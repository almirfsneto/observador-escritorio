"""Portable fault injection: no OS ownership or native failure claimed."""
import ctypes
from ctypes import wintypes as W
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from isolated_job_creation import CreationProbe, StartupEx, ProcessInfo, JOB_LIST, CREATION_FLAGS, PHASES
from observador.win32_handles import close_handle_once


class FakeApi:
    def __init__(self, fault=None):
        self.fault = fault
        self.calls = []
        self.last_error = 122
        self.probe = None

    def action(self, name):
        self.calls.append(name)
        if self.fault == name + '_exception':
            raise OSError('SYNTHETIC_SECRET')
        return self.fault != name

    def GetHandleInformation(self, handle, out):
        ctypes.cast(out, ctypes.POINTER(W.DWORD))[0] = 0
        return self.action('job_setup')

    def GetCurrentProcess(self):
        return -1

    def IsProcessInJob(self, process, job, out):
        ctypes.cast(out, ctypes.POINTER(W.BOOL))[0] = bool(job)
        return self.action('ambient' if job is None else 'membership')

    def InitializeProcThreadAttributeList(self, buffer, count, flags, size):
        name = 'attribute_size' if buffer is None else 'attribute_init'
        ok = self.action(name)
        ctypes.cast(size, ctypes.POINTER(ctypes.c_size_t))[0] = 128 if ok else 0
        return False if buffer is None else ok

    def UpdateProcThreadAttribute(self, buffer, flags, key, value, size, previous, returned):
        assert key == JOB_LIST and flags == 0 and size == ctypes.sizeof(W.HANDLE)
        assert value is self.probe.job_values
        return self.action('attribute_update')

    def CreateProcessW(self, image, command, process_security, thread_security, inherit, flags,
                       environment, directory, startup, info):
        assert inherit is False and flags == CREATION_FLAGS
        assert not flags & 0x1000000  # No BREAKAWAY.
        assert self.probe.attribute_state == 'initialized'
        assert self.probe.job_values is not None
        value = ctypes.cast(startup, ctypes.POINTER(StartupEx)).contents
        assert value.startup.cb == ctypes.sizeof(StartupEx)
        assert value.attributes == ctypes.addressof(self.probe.attribute_buffer)
        if not self.action('create'):
            return False
        target = ctypes.cast(info, ctypes.POINTER(ProcessInfo)).contents
        target.process, target.thread = 11, 12
        return True

    def DeleteProcThreadAttributeList(self, buffer):
        assert self.probe.job_values is not None  # lpValue still alive through deletion.
        self.action('attribute_delete')  # VOID: a fake False is NOT native failure.

    def ResumeThread(self, handle):
        return 1 if self.action('resume') else 0xffffffff

    def WaitForSingleObject(self, handle, milliseconds):
        self.calls.append('process_wait')
        return 0xffffffff if self.fault == 'process_wait' else 0

    def CloseHandle(self, handle):
        self.calls.append('close_' + str(handle))
        return self.fault != 'close_' + str(handle)


class FakeJob:
    def __init__(self, api):
        self.api = api
        self.handle = 13
        self.close_state = 'open'
        self.cleanup_confirmed = self.processes_confirmed = False

    def close(self):
        if self.close_state == 'closed':
            return
        ok = self.api.action('job_cleanup')
        try:
            close_handle_once(self, self.api)
        finally:
            self.cleanup_confirmed = self.processes_confirmed = ok and self.close_state == 'closed'
        if not ok:
            raise OSError('SYNTHETIC_SECRET')


class JobCreationContractTest(unittest.TestCase):
    def context(self, fault=None):
        api = FakeApi(fault)
        # Setup must be tested before the probe exists too.
        with patch('isolated_job_creation.ctypes.get_last_error', lambda: api.last_error, create=True):
            probe = CreationProbe(Path(tempfile.gettempdir()) / 'synthetic.started', api=api,
                                  job_factory=lambda: FakeJob(api))
        api.probe = probe
        return probe, api

    def create(self, p, api):
        with patch.dict(os.environ, {'SystemRoot': 'SYNTHETIC_ROOT'}), patch(
                'isolated_job_creation.ctypes.get_last_error', lambda: api.last_error, create=True):
            p.create()

    def test_flags_storage_and_order_no_assign_no_resume_before_verification(self):
        p, api = self.context()
        self.create(p, api)
        with self.assertRaisesRegex(OSError, '^creation_resume_refused$'):
            p.resume()
        self.assertNotIn('membership', api.calls)
        p.verify()
        p.resume()
        with self.assertRaises(OSError):
            p.resume()
        p.close()
        self.assertLess(api.calls.index('membership'), api.calls.index('resume'))
        self.assertLess(api.calls.index('attribute_delete'), api.calls.index('close_13'))
        self.assertTrue(p.status.confirmed)
        self.assertIsNone(p.attribute_buffer)
        self.assertIsNone(p.job_values)
        self.assertEqual(p.attribute_state, 'deleted')

    def test_all_creation_failures_cleanup_without_fallback(self):
        for fault in ('attribute_size', 'attribute_size_exception', 'attribute_init',
                      'attribute_init_exception', 'attribute_update', 'attribute_update_exception',
                      'create', 'create_exception'):
            with self.subTest(fault=fault):
                p, api = self.context(fault)
                with self.assertRaisesRegex(OSError, '^job_at_creation_unavailable$') as result:
                    self.create(p, api)
                self.assertIs(result.exception.resource, p)
                self.assertTrue(p.status.confirmed)
                self.assertFalse(p.created)
                self.assertIsNone(p.attribute_buffer)
                self.assertNotIn('resume', api.calls)
                self.assertNotIn('SYNTHETIC_SECRET', json.dumps(p.snapshot()))
                if fault.startswith('attribute_update') or fault.startswith('create'):
                    self.assertEqual(api.calls.count('attribute_delete'), 1)
                else:
                    self.assertNotIn('attribute_delete', api.calls)

    def test_setup_failure_retains_diagnostic_and_closes_job(self):
        for fault in ('job_setup', 'job_setup_exception', 'ambient_exception'):
            with self.assertRaises(OSError) as result:
                self.context(fault)
            p = result.exception.resource
            self.assertTrue(p.status.confirmed)
            self.assertEqual(p.first_failure, 'job_setup')
            self.assertEqual(p.job.close_state, 'closed')

    def test_membership_and_resume_failure_prevent_success_but_cleanup_continues(self):
        for fault in ('membership', 'membership_exception', 'resume', 'resume_exception'):
            p, api = self.context()
            self.create(p, api)
            api.fault = fault
            with self.assertRaises(OSError):
                p.verify()
                p.resume()
            self.assertFalse(p.resumed)
            p.close()
            self.assertTrue(p.status.confirmed)

    def test_delete_exception_is_sticky_preserves_storage_and_all_other_cleanup(self):
        p, api = self.context()
        self.create(p, api)
        api.fault = 'attribute_delete_exception'
        with self.assertRaises(OSError):
            p.close()
        self.assertEqual(p.attribute_state, 'failed')
        self.assertIsNotNone(p.attribute_buffer)
        self.assertIsNotNone(p.job_values)
        self.assertFalse(p.status.confirmed)
        self.assertEqual(p.process.close_state, 'closed')
        self.assertEqual(p.thread.close_state, 'closed')
        before = list(api.calls)
        with self.assertRaises(OSError):
            p.close()
        self.assertEqual(api.calls, before)

    def test_job_wait_and_both_handle_errors_stay_unconfirmed_without_retry(self):
        for fault in ('job_cleanup', 'job_cleanup_exception', 'process_wait', 'close_11', 'close_12', 'close_13'):
            with self.subTest(fault=fault):
                p, api = self.context()
                self.create(p, api)
                api.fault = fault
                with self.assertRaises(OSError):
                    p.close()
                self.assertFalse(p.status.confirmed)
                self.assertEqual(p.attribute_state, 'deleted')
                self.assertIn('close_11', api.calls)
                self.assertIn('close_12', api.calls)
                before = list(api.calls)
                with self.assertRaises(OSError):
                    p.close()
                self.assertEqual(api.calls, before)

    def test_diagnostics_are_closed_and_single_use(self):
        p, api = self.context()
        self.create(p, api)
        p.close()
        value = p.snapshot()
        self.assertEqual(set(value['phases']), set(PHASES))
        self.assertNotIn('SYNTHETIC_ROOT', json.dumps(value))
        self.assertNotIn('synthetic.started', json.dumps(value))
        self.assertNotIn('11', json.dumps(value))
        self.assertNotIn('13', json.dumps(value))
        with self.assertRaises(ValueError):
            p.note('SYNTHETIC_SECRET', False)
        with self.assertRaises(OSError):
            p.create()
