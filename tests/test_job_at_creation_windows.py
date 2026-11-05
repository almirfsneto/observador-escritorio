"""Real Windows Job-at-creation evidence; every process is a synthetic own fixture."""
import ctypes
from ctypes import wintypes as W
import json
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from isolated_job_creation import CreationProbe, minimal_environment
from observador.cleanup import CleanupStatus
from observador.owned_channel_win32 import Kernel
from observador.win32_handles import close_handle_once


def wait_marker(marker):
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        if marker.exists():
            data = marker.read_bytes()
            if data:
                if len(data) <= 20 and data.isdigit():
                    return int(data)
                raise OSError('creation_fixture_rejected')
        time.sleep(.01)
    raise OSError('creation_fixture_not_ready')


def duplicate_process(kernel, source, slot):
    """Private slot from our own retained launcher/child; never OpenProcess(pid)."""
    if not isinstance(slot, int) or not 0 < slot < 2 ** 64:
        raise OSError('creation_capability_rejected')
    out = W.HANDLE()
    if not kernel.api.DuplicateHandle(source, slot, kernel.current(), ctypes.byref(out),
                                       1 | 0x40 | 0x1000 | 0x100000, False, 0):
        raise OSError('creation_capability_unavailable')
    owner = SimpleNamespace(handle=out.value, close_state='open')
    try:
        kernel.identity(owner.handle)  # Retained object, live Python image/times/session.
        if kernel.flags(owner.handle) != 0:
            raise OSError('creation_capability_rejected')
    except Exception:
        close_handle_once(owner, kernel.api)
        raise OSError('creation_capability_rejected') from None
    return owner


@unittest.skipUnless(sys.platform == 'win32', 'Requires real Windows kernel process/handle execution')
class WindowsJobAtCreationTest(unittest.TestCase):
    def emit(self, probe):
        print('JOB_AT_CREATION_DIAGNOSTIC ' + json.dumps(probe.snapshot(), sort_keys=True), flush=True)

    def test_real_membership_at_creation_suspended_no_inheritance_descendants_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / 'synthetic.started'
            kernel = Kernel()
            read, write = kernel.pipe()
            probe = None
            try:
                kernel.inherit(read, True)
                probe = CreationProbe(marker)
                # Runtime assign must never be invoked by the experiment.
                with patch.object(probe.job, 'assign', side_effect=AssertionError('creation_assign_forbidden')):
                    probe.create()
                    self.assertEqual(probe.api.WaitForSingleObject(probe.process.handle, 100), 258)
                    self.assertFalse(marker.exists())
                    self.assertFalse(probe.assigned)
                    self.assertTrue(kernel.no_inherited_objects(probe.process.handle, [read, write, probe.job.handle]))
                    with self.assertRaisesRegex(OSError, '^creation_resume_refused$'):
                        probe.resume()
                    probe.verify()
                    self.assertFalse(marker.exists())
                    probe.delete_attributes()
                    self.assertIsNone(probe.job_values)
                    probe.resume()
                    slot = wait_marker(marker)
                    descendant = duplicate_process(kernel, probe.process.handle, slot)
                    try:
                        self.assertTrue(kernel.no_inherited_objects(descendant.handle, [read, write, probe.job.handle]))
                        member = W.BOOL()
                        self.assertTrue(probe.api.IsProcessInJob(descendant.handle, probe.job.handle, ctypes.byref(member)))
                        self.assertTrue(member.value)
                        accounting = ctypes.create_string_buffer(48)
                        self.assertTrue(probe.job.api.QueryInformationJobObject(probe.job.handle, 1, accounting, 48, None))
                        self.assertEqual(W.DWORD.from_buffer(accounting, 40).value, 2)
                        probe.close()
                        self.assertEqual(kernel.api.WaitForSingleObject(descendant.handle, 2000), 0)
                    finally:
                        close_handle_once(descendant, kernel.api)
                self.assertTrue(probe.status.confirmed)
                self.assertTrue(probe.job.processes_confirmed)
                self.assertEqual(probe.attribute_state, 'deleted')
                self.emit(probe)
            finally:
                status = CleanupStatus()
                if probe is not None:
                    status.attempt('provider', probe.close)
                status.attempt('provider', lambda: kernel.inherit(read, False))
                status.attempt('provider', lambda: kernel.close(read))
                status.attempt('provider', lambda: kernel.close(write))
                status.finish()
                self.assertTrue(status.confirmed, 'creation_test_cleanup_unconfirmed')
        print('REAL_JOB_AT_CREATION membership_before_resume no_inherited_job_or_decoy descendants_zero')

    def crash_case(self, stage, *, nested=False):
        kernel = Kernel()
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / 'synthetic.started'
            script = Path(__file__).with_name('isolated_job_creation.py')
            launcher = subprocess.Popen([sys.executable, '-I', '-S', '-B', str(script), 'nested_before_verify' if nested else stage, str(marker)],
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                        text=True, close_fds=True, env=minimal_environment(tmp),
                                        creationflags=subprocess.CREATE_NO_WINDOW)
            child = descendant = reader = outer = None
            try:
                messages = queue.Queue(maxsize=2)
                def receive():
                    for _ in range(2 if nested else 1):
                        messages.put(launcher.stdout.readline(1024))
                reader = threading.Thread(target=receive, daemon=True)
                reader.start()
                if nested:
                    from observador.acceptance_metrics import OwnedJob
                    self.assertEqual(messages.get(timeout=10).strip(), 'prepare')
                    outer = OwnedJob()
                    outer.assign(launcher)
                    launcher.stdin.write('create\n')
                    launcher.stdin.flush()
                message = json.loads(messages.get(timeout=10))
                self.assertTrue(set(message) == {'slot', 'stage', 'verified', 'resumed', 'job_noninheritable', 'ambient_job'},
                                'creation_private_control_rejected')
                self.assertTrue(message['stage'] == stage and message['job_noninheritable'],
                                'creation_private_stage_rejected')
                self.assertIs(message['verified'], stage != 'before_verify')
                self.assertIs(message['resumed'], stage == 'after_resume')
                if nested:
                    self.assertEqual(message['ambient_job'], 'present')
                child = duplicate_process(kernel, int(launcher._handle), message['slot'])
                self.assertTrue(kernel.identity(child.handle)['start_ticks'] >
                                kernel.identity(int(launcher._handle))['start_ticks'],
                                'creation_child_identity_unconfirmed')
                if nested:
                    member = W.BOOL()
                    # Use the typed declaration from the experiment, for our retained child only.
                    from isolated_job_creation import extended_api
                    self.assertTrue(extended_api().IsProcessInJob(child.handle, outer.handle, ctypes.byref(member)))
                    self.assertTrue(member.value)
                if stage == 'after_resume':
                    descendant = duplicate_process(kernel, child.handle, wait_marker(marker))
                else:
                    self.assertFalse(marker.exists())
                # Root holds no TARGET Job; the controlled outer Job, if any, stays open.
                self.assertEqual(kernel.api.WaitForSingleObject(child.handle, 0), 258)
                launcher.kill()
                launcher.wait(timeout=5)  # True abrupt death, no launcher finally.
                self.assertEqual(kernel.api.WaitForSingleObject(child.handle, 5000), 0,
                                 'creation_orphan_child')
                if descendant is not None:
                    self.assertEqual(kernel.api.WaitForSingleObject(descendant.handle, 5000), 0,
                                     'creation_orphan_descendant')
                else:
                    self.assertFalse(marker.exists())
                if outer is not None:
                    outer._confirm_empty()  # Outer remains open throughout inner kill-on-close proof.
                    self.assertTrue(outer.processes_confirmed)
                evidence = dict(
                    stage=stage, origin='win32', root_target_job_handles=0,
                    controlled_outer_job=nested, outer_zero_confirmed=bool(outer and outer.processes_confirmed),
                    child_exit_confirmed=True, known_descendants=1 if descendant else 0,
                    known_descendants_exit_confirmed=True, launcher_finally_executed=False)
            finally:
                status = CleanupStatus()
                def stop_launcher():
                    if launcher.poll() is None:
                        try:
                            launcher.stdin.write('cleanup\n')
                            launcher.stdin.flush()
                            launcher.wait(timeout=5)
                        except (OSError, subprocess.TimeoutExpired):
                            launcher.kill()
                            launcher.wait(timeout=5)
                status.attempt('provider', stop_launcher)
                for owner in (descendant, child):
                    if owner is not None:
                        def stop_owned(o=owner):
                            try:
                                if kernel.api.WaitForSingleObject(o.handle, 0) != 0:
                                    if not kernel.api.TerminateProcess(o.handle, 1):
                                        raise OSError('creation_emergency_stop_failed')
                                if kernel.api.WaitForSingleObject(o.handle, 5000) != 0:
                                    raise OSError('creation_emergency_exit_unconfirmed')
                            finally:
                                close_handle_once(o, kernel.api)
                        # Declare TerminateProcess only for known retained owned handles.
                        kernel.api.TerminateProcess.argtypes = [W.HANDLE, W.UINT]
                        kernel.api.TerminateProcess.restype = W.BOOL
                        status.attempt('provider', stop_owned)
                if reader:
                    reader.join(timeout=2)
                    if reader.is_alive():
                        status.fail('provider')
                if outer is not None:
                    status.attempt('provider', outer.close)
                status.attempt('provider', launcher.stdin.close)
                status.attempt('provider', launcher.stdout.close)
                # Transfer the Popen handle once; prevent its finalizer closing an uncertain slot.
                launcher_owner = SimpleNamespace(handle=launcher._handle.Detach(), close_state='open')
                status.attempt('provider', lambda: close_handle_once(launcher_owner, kernel.api))
                status.finish()
                self.assertTrue(status.confirmed, 'creation_crash_test_cleanup_unconfirmed')
            evidence['root_resource_cleanup_confirmed'] = True
            print('REAL_JOB_CREATION_LAUNCHER_CRASH ' + json.dumps(evidence, sort_keys=True))

    def test_real_launcher_death_before_membership_verification(self):
        self.crash_case('before_verify')

    def test_real_launcher_death_after_membership_before_resume(self):
        self.crash_case('after_verify')

    def test_real_launcher_death_after_resume_kills_known_descendant(self):
        self.crash_case('after_resume')

    def test_real_nested_job_launcher_death_before_verification_with_outer_still_open(self):
        self.crash_case('before_verify', nested=True)

    def test_real_invalid_attribute_job_and_image_fail_closed(self):
        for negative, phase in (('invalid_attribute_size', 'attribute_update'),
                                ('invalid_job', 'create'), ('missing_image', 'create')):
            with self.subTest(negative=negative), tempfile.TemporaryDirectory() as tmp:
                probe = CreationProbe(Path(tmp) / 'synthetic.started')
                with self.assertRaisesRegex(OSError, '^job_at_creation_unavailable$'):
                    probe.create(negative=negative)
                self.assertFalse(probe.created)
                self.assertFalse(probe.marker.exists())
                self.assertEqual(probe.first_failure, phase)
                self.assertTrue(probe.status.confirmed)
                self.assertEqual(probe.attribute_state, 'deleted')
                self.emit(probe)
        print('REAL_JOB_CREATION_INVALID_ARGUMENTS rejected_without_fallback resources_closed')

    def test_injected_membership_resume_failures_close_real_owned_resources(self):
        for fault in ('membership_false', 'membership_error', 'resume'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as tmp:
                probe = CreationProbe(Path(tmp) / 'synthetic.started')
                probe.diagnostic_origin = 'injected'
                try:
                    probe.create()
                    if fault.startswith('membership'):
                        with patch.object(probe.api, 'IsProcessInJob', return_value=fault == 'membership_false'):
                            with self.assertRaises(OSError):
                                probe.verify()
                        self.assertFalse(probe.assigned)
                        with self.assertRaises(OSError):
                            probe.resume()
                    else:
                        probe.verify()
                        with patch.object(probe.api, 'ResumeThread', return_value=0xffffffff):
                            with self.assertRaises(OSError):
                                probe.resume()
                    self.assertFalse(probe.marker.exists())
                finally:
                    probe.close()
                self.assertTrue(probe.status.confirmed)
                self.emit(probe)
        print('INJECTED_JOB_CREATION_GUARDS real_children_closed no_resume')

    def test_real_console_flag_comparison_accounts_for_additional_job_members(self):
        # Controlled A/B: only the descendant console creation flag differs.
        observations = {}
        for console in (True, False):
            with tempfile.TemporaryDirectory() as tmp:
                probe = CreationProbe(Path(tmp) / 'synthetic.started', descendant_console=console)
                try:
                    probe.create()
                    before = ctypes.create_string_buffer(48)
                    self.assertTrue(probe.job.api.QueryInformationJobObject(probe.job.handle, 1, before, 48, None))
                    self.assertEqual(W.DWORD.from_buffer(before, 40).value, 1)
                    probe.verify()
                    probe.resume()
                    wait_marker(probe.marker)
                    value = ctypes.create_string_buffer(48)
                    self.assertTrue(probe.job.api.QueryInformationJobObject(probe.job.handle, 1, value, 48, None))
                    active = W.DWORD.from_buffer(value, 40).value
                    observations['allocate_console' if console else 'no_window'] = active
                    if not console:
                        self.assertEqual(active, 2)
                    else:
                        self.assertGreaterEqual(active, 2)  # Observe helper count, never assume helper identity.
                finally:
                    probe.close()
                self.assertTrue(probe.status.confirmed)
                self.assertTrue(probe.job.processes_confirmed)
        print('REAL_JOB_CREATION_CONSOLE_COMPARISON ' + json.dumps(dict(
            origin='win32', active_members=observations, all_jobs_zero_after_cleanup=True), sort_keys=True))

    def test_real_protected_close_keeps_cleanup_unconfirmed_and_closes_attributes(self):
        with tempfile.TemporaryDirectory() as tmp:
            probe = CreationProbe(Path(tmp) / 'synthetic.started')
            probe.create()
            raw = probe.process.handle
            api = probe.api
            api.SetHandleInformation.argtypes = [W.HANDLE, W.DWORD, W.DWORD]
            api.SetHandleInformation.restype = W.BOOL
            self.assertTrue(api.SetHandleInformation(raw, 2, 2))
            try:
                with self.assertRaisesRegex(OSError, '^isolated_cleanup_unconfirmed$'):
                    probe.close()
                self.assertFalse(probe.status.confirmed)
                self.assertTrue(probe.diagnostic.process_exit_confirmed)
                self.assertEqual(probe.thread.close_state, 'closed')
                self.assertEqual(probe.process.close_state, 'failed')
                self.assertEqual(probe.attribute_state, 'deleted')
                self.assertIsNone(probe.job_values)
                with self.assertRaises(OSError):
                    probe.close()
                self.emit(probe)
            finally:
                self.assertTrue(api.SetHandleInformation(raw, 2, 0))
                self.assertTrue(api.CloseHandle(raw))  # Known, deliberately protected owner; test-only recovery.
        print('REAL_JOB_CREATION_CLOSE_REFUSED cleanup_unconfirmed no_retry attributes_deleted')
