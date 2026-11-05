"""Portable injected supervision negatives: never claimed as Win32 evidence."""
import ctypes
from ctypes import wintypes as W
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch
from types import SimpleNamespace
import unittest

from isolated_process_supervision import Ledger, Supervisor, NativeWorker, NONCE, decode_record, job_members, PHASES
from test_job_at_creation_contract import FakeApi, FakeJob


class Clock:
    def __init__(self):
        self.value = 0
    def __call__(self):
        return self.value
    def tick(self):
        self.value += .01


class Backend:
    def __init__(self, *, states=('blocked_after_join', 'pong_blocked'), fault=None):
        self.ledger = Ledger('injected')
        self.states = iter(states)
        self.fault = fault
        self.commands = []
        self.stopped = False
        self.expired_at_stop = False
    def start(self):
        if self.fault in ('job_creation', 'attribute_size', 'attribute_init', 'attribute_update', 'membership'):
            self.ledger.fail('membership' if self.fault == 'membership' else 'creation')
            raise OSError('SYNTHETIC_SECRET')
    def read(self):
        if self.fault == 'communication':
            raise OSError('SYNTHETIC_SECRET')
        return next(self.states, None)
    def write(self, command):
        if self.fault == 'send':
            raise OSError('SYNTHETIC_SECRET')
        self.commands.append(command)
    def alive(self):
        return self.fault != 'normal'
    def close(self):
        self.expired_at_stop = self.ledger.expired
        self.stopped = True
        l = self.ledger
        l.worker_exit = self.fault not in ('wait', 'process_wait')
        l.job_zero = self.fault != 'job_zero'
        l.handles_closed = self.fault not in ('job_close', 'thread_close', 'process_close')
        l.attributes_deleted = self.fault != 'attribute_delete'
        if self.fault in ('job_terminate', 'process_wait', 'job_zero', 'job_close', 'thread_close', 'process_close'):
            l.fail(self.fault)
        if self.fault == 'attribute_delete':
            l.fail('attributes')
        if self.fault == 'unknown_members':
            l.unknown_members = l.bulk_refused = True
            l.fail('ownership')
        l.finished = True


class SupervisionContractTest(unittest.TestCase):
    def run_backend(self, backend, **kwargs):
        clock = Clock()
        return Supervisor(backend, clock=clock, idle=clock.tick).run(**kwargs)

    def test_expiry_is_monotone_and_recorded_before_stop_even_after_late_exit(self):
        b = Backend()
        d = self.run_backend(b)
        self.assertTrue(b.expired_at_stop)
        self.assertTrue(d['deadline_expired'])
        self.assertTrue(d['expiry_before_stop'])
        self.assertEqual(d['worker_state'], 'deadline_expired')
        self.assertTrue(d['process_exit_confirmed'])
        self.assertEqual(d['cleanup_state'], 'confirmed')
        self.assertTrue(d['root_responsive'])
        self.assertEqual(d['ui_state'], 'unknown')

    def test_normal_exit_requires_independent_cleanup_proofs(self):
        b = Backend(states=('normal_done',), fault='normal')
        d = self.run_backend(b)
        self.assertFalse(d['deadline_expired'])
        self.assertEqual(d['worker_state'], 'exited')
        self.assertEqual(d['cleanup_state'], 'confirmed')

    def test_creation_and_membership_failures_still_attempt_cleanup(self):
        for fault in ('job_creation', 'attribute_size', 'attribute_init', 'attribute_update', 'membership'):
            b = Backend(fault=fault)
            d = self.run_backend(b)
            self.assertTrue(b.stopped)
            self.assertEqual(d['cleanup_state'], 'cleanup_unconfirmed')
            self.assertNotIn('SYNTHETIC_SECRET', json.dumps(d))

    def test_api_wait_job_close_failures_never_become_confirmation(self):
        for fault in ('wait', 'job_zero', 'job_terminate', 'process_wait', 'job_close',
                      'thread_close', 'process_close', 'attribute_delete'):
            b = Backend(fault=fault)
            d = self.run_backend(b)
            self.assertEqual(d['cleanup_state'], 'cleanup_unconfirmed')
            self.assertTrue(d['deadline_expired'])

    def test_cancel_without_ack_remains_unconfirmed_after_physical_exit(self):
        b = Backend()
        event = SimpleNamespace(is_set=lambda: b.ledger.started)
        d = self.run_backend(b, cancel_event=event)
        self.assertIn('cancel', b.commands)
        self.assertTrue(d['cancel_requested'])
        self.assertFalse(d['cancel_acknowledged'])
        self.assertTrue(d['physical_cleanup_confirmed'])
        self.assertEqual(d['cleanup_state'], 'cleanup_unconfirmed')

    def test_ack_without_request_is_rejected_and_does_not_prove_exit(self):
        b = Backend(states=('cancel_ack',))
        d = self.run_backend(b)
        self.assertFalse(d['cancel_acknowledged'])
        self.assertGreater(d['errors']['communication'], 0)
        self.assertEqual(d['cleanup_state'], 'cleanup_unconfirmed')

    def test_communication_error_send_failure_and_missing_start_fail_closed(self):
        for b in (Backend(fault='communication'), Backend(fault='send'), Backend(states=())):
            d = self.run_backend(b, startup_budget=.05)
            self.assertTrue(b.stopped)
            self.assertEqual(d['cleanup_state'], 'cleanup_unconfirmed')

    def test_unknown_members_refuse_bulk_termination_without_invented_ownership(self):
        b = Backend(fault='unknown_members')
        d = self.run_backend(b)
        self.assertTrue(d['bulk_termination_refused'])
        self.assertTrue(d['unknown_members'])
        self.assertEqual(d['cleanup_state'], 'cleanup_unconfirmed')

    def test_protocol_rejects_payload_types_nonce_replay_shape_and_duplicates(self):
        valid = dict(v=1, nonce=NONCE, seq=0, state='blocked_after_join')
        self.assertEqual(decode_record(json.dumps(valid).encode()), valid)
        for value in (dict(valid, seq=True), dict(valid, seq=65), dict(valid, v=True),
                      dict(valid, nonce='wrong'), dict(valid, state='arbitrary'), dict(valid, extra=1)):
            with self.assertRaisesRegex(OSError, '^supervision_communication_rejected$'):
                decode_record(json.dumps(value).encode())
        for raw in (b'X'*257, b'{"v":1,"v":1}', b'[]', b'null', b'bad'):
            with self.assertRaises(OSError):
                decode_record(raw)

    def test_job_query_is_bounded_and_unknown_ids_never_opened(self):
        def query(handle, kind, buffer, size, returned):
            # Write a synthetic Job process list; no native OS call.
            ctypes.cast(buffer, ctypes.POINTER(W.DWORD))[0] = 2
            ctypes.cast(buffer, ctypes.POINTER(W.DWORD))[1] = 2
            # DWORD alignment on Linux differs; use the structure's field offset.
            start = ctypes.addressof(buffer._obj) + type(buffer._obj).ids.offset
            ids = (ctypes.c_size_t*16).from_address(start)
            ids[0], ids[1] = 11, 22
            return True
        api = SimpleNamespace(QueryInformationJobObject=query, GetProcessId=lambda h: 11)
        self.assertEqual(job_members(api, SimpleNamespace(handle=1), [1]), (2, True))
        api.QueryInformationJobObject = lambda *a: False
        with self.assertRaises(OSError):
            job_members(api, SimpleNamespace(handle=1), [1])

    def test_diagnostic_has_fixed_phases_and_sticky_errors(self):
        l = Ledger('injected')
        l.fail('process_close')
        l.worker_exit = l.job_zero = l.handles_closed = l.attributes_deleted = l.finished = True
        l.expire()
        d = l.snapshot()
        self.assertEqual(set(d['errors']), set(PHASES))
        self.assertEqual(d['cleanup_state'], 'cleanup_unconfirmed')
        self.assertTrue(d['physical_cleanup_confirmed'])
        with self.assertRaises(ValueError):
            l.fail('SYNTHETIC_SECRET')
        with self.assertRaises(ValueError):
            Ledger('forged')


class NativeBackendInjectionTest(unittest.TestCase):
    def backend(self, marker, fault=None):
        class Api(FakeApi):
            def GetProcessId(self, handle):
                return 11
            def QueryInformationJobObject(self, handle, kind, buffer, size, returned):
                if kind == 3:
                    obj = buffer._obj
                    active = bool(self.probe and self.probe.created)
                    obj.assigned = obj.listed = int(active)
                    if active:
                        obj.ids[0] = 11
                return True
            def SetInformationJobObject(self, *args):
                return self.action('disarm')
            def TerminateJobObject(self, *args):
                return self.action('job_terminate')
            def TerminateProcess(self, *args):
                return self.action('process_terminate')
        class Job(FakeJob):
            def _confirm_empty(self):
                if not self.api.action('job_zero'):
                    raise OSError('SYNTHETIC_SECRET')
                self.processes_confirmed = True
        api = Api(fault)
        with patch('isolated_job_creation.ctypes.get_last_error', lambda: 122, create=True):
            worker = NativeWorker(marker, api=api, job_factory=lambda: Job(api))
        api.probe = worker
        return worker, api

    def test_actual_creation_paths_injected_failures_cannot_bypass_teardown(self):
        with tempfile.TemporaryDirectory() as tmp:
            def refused_job():raise OSError('SYNTHETIC_SECRET')
            with self.assertRaises(OSError) as error:
                NativeWorker(Path(tmp)/'status', api=FakeApi(), job_factory=refused_job)
            owner = error.exception.resource
            self.assertTrue(owner.ledger.finished)
            self.assertEqual(owner.ledger.snapshot()['cleanup_state'],'cleanup_unconfirmed')
        for fault in ('attribute_size', 'attribute_init', 'attribute_update', 'create', 'membership'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as tmp:
                worker, api = self.backend(Path(tmp)/'status', fault)
                with patch.dict(os.environ, {'SystemRoot':'SYNTHETIC_ROOT'}), patch(
                        'isolated_job_creation.ctypes.get_last_error', lambda: 122, create=True):
                    with self.assertRaises(OSError):
                        worker.start()
                    try:
                        worker.close()
                    except OSError:
                        pass
                snapshot = worker.ledger.snapshot()
                self.assertTrue(worker.ledger.finished)
                self.assertEqual(snapshot['cleanup_state'], 'cleanup_unconfirmed')
                self.assertEqual(worker.process.close_state, 'closed')
                self.assertEqual(worker.thread.close_state, 'closed')
                self.assertNotIn('SYNTHETIC_SECRET', json.dumps(snapshot))

    def test_disarm_denied_quarantines_job_and_never_bulk_kills_or_closes_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            worker, api = self.backend(Path(tmp)/'status')
            with patch.dict(os.environ, {'SystemRoot':'SYNTHETIC_ROOT'}), patch(
                    'isolated_job_creation.ctypes.get_last_error', lambda: 122, create=True):
                worker.create()
            api.fault = 'disarm'
            api.WaitForSingleObject = lambda h,ms: 258 if ms == 0 else 0
            with patch('isolated_process_supervision.job_members', return_value=(2,True)):
                with self.assertRaises(OSError):
                    worker.close()
            d = worker.ledger.snapshot()
            self.assertTrue(d['job_quarantined'])
            self.assertTrue(d['bulk_termination_refused'])
            self.assertNotIn('job_terminate', api.calls)
            self.assertNotIn('close_13', api.calls)
            self.assertIn('process_terminate', api.calls)
            self.assertEqual(d['cleanup_state'], 'cleanup_unconfirmed')
            self.assertFalse(d['physical_cleanup_confirmed'])
            before = list(api.calls)
            with self.assertRaises(OSError):
                worker.close()
            self.assertEqual(api.calls, before)

    def test_actual_teardown_failures_keep_resource_errors_and_attempt_both_handle_closes(self):
        for fault in ('job_terminate','job_zero','close_11','close_12','close_13','process_wait'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as tmp:
                worker, api = self.backend(Path(tmp)/'status')
                with patch.dict(os.environ, {'SystemRoot':'SYNTHETIC_ROOT'}), patch(
                        'isolated_job_creation.ctypes.get_last_error', lambda:122, create=True):
                    worker.create()
                api.fault = fault
                with self.assertRaises(OSError):
                    worker.close()
                d = worker.ledger.snapshot()
                self.assertEqual(d['cleanup_state'],'cleanup_unconfirmed')
                if fault == 'process_wait':
                    self.assertNotIn('close_11',api.calls)
                    self.assertTrue(d['process_capability_retained_after_shutdown'])
                    self.assertEqual(worker.process.close_state,'open')
                else:
                    self.assertIn('close_11',api.calls)
                self.assertIn('close_12',api.calls)
                self.assertTrue(d['attributes_deleted'])
                before = list(api.calls)
                with self.assertRaises(OSError):worker.close()
                self.assertEqual(api.calls,before)
