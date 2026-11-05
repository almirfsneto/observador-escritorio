"""Issue33 real Win32 observations, separately labeled injected API failures."""
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

from isolated_process_supervision import NativeWorker, Supervisor, job_members, disarm_job
from isolated_suspended_spawn import minimal_environment
from test_job_at_creation_windows import duplicate_process
from observador.cleanup import CleanupStatus
from observador.acceptance_metrics import OwnedJob
from observador.owned_channel_win32 import Kernel
from observador.win32_handles import close_handle_once


@unittest.skipUnless(sys.platform == 'win32', 'Requires real Windows kernel process/handle execution')
class WindowsProcessSupervisionTest(unittest.TestCase):
    def emit(self, snapshot):
        print('PROCESS_SUPERVISION_DIAGNOSTIC ' + json.dumps(snapshot, sort_keys=True), flush=True)

    def assert_physical_and_classification(self, snapshot):
        # An observed ownership refusal stays a refusal; do NOT erase it to obtain green.
        self.assertTrue(snapshot['physical_cleanup_confirmed'])
        self.assertTrue(all(v == 0 for k,v in snapshot['errors'].items() if k != 'ownership'))
        if snapshot['unknown_members']:
            self.assertTrue(snapshot['bulk_termination_refused'])
            self.assertTrue(snapshot['job_disarmed_verified'])
            self.assertGreater(snapshot['errors']['ownership'], 0)
            self.assertEqual(snapshot['cleanup_state'], 'cleanup_unconfirmed')
        else:
            self.assertEqual(snapshot['cleanup_state'], 'confirmed')

    def test_real_normal_worker_exit_and_verified_resources(self):
        with tempfile.TemporaryDirectory() as tmp:
            worker = NativeWorker(Path(tmp)/'status', mode='normal')
            snapshot = Supervisor(worker).run(duration=2)
            self.emit(snapshot)
            self.assertTrue(snapshot['worker_started'])
            self.assert_physical_and_classification(snapshot)
            self.assertTrue(snapshot['process_exit_confirmed'])
            self.assertTrue(snapshot['job_zero_confirmed'])
            self.assertFalse(snapshot['deadline_expired'])
            self.assertEqual(snapshot['ui_state'], 'unknown')

    def test_real_blocked_lock_root_responsive_deadline_then_confirmed_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            worker = NativeWorker(Path(tmp)/'status')
            observed = []
            with patch.object(worker.job.api, 'TerminateJobObject', wraps=worker.job.api.TerminateJobObject) as bulk:
                snapshot = Supervisor(worker).run(on_tick=lambda s: observed.append(time.monotonic()))
                if snapshot['unknown_members']:
                    bulk.assert_not_called()
                else:
                    bulk.assert_called_once()
            self.emit(snapshot)
            self.assertTrue(snapshot['join_insufficient'])
            self.assertTrue(snapshot['root_responsive'])
            self.assertGreaterEqual(snapshot['root_pongs'], 1)
            self.assertTrue(snapshot['deadline_expired'])
            self.assertTrue(snapshot['expiry_before_stop'])
            self.assertTrue(snapshot['process_exit_confirmed'])
            self.assertTrue(snapshot['job_zero_confirmed'])
            self.assert_physical_and_classification(snapshot)
            self.assertGreaterEqual(len(observed), 3)
            self.assertTrue(snapshot['creation_membership_verified'])
            self.assertEqual(list(Path(tmp).iterdir()), [])
        print('REAL_SUPERVISION_BLOCKED_LOCK root_responsive deadline_sticky physical_exit_zero_close ownership_separate')

    def test_real_cancel_request_without_ack_stays_unconfirmed_after_owned_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            worker = NativeWorker(Path(tmp)/'status')
            event = threading.Event()
            def cancel(s):
                if s.ledger.started and s.ledger.pongs:
                    event.set()
            snapshot = Supervisor(worker).run(cancel_event=event, on_tick=cancel)
            self.emit(snapshot)
            self.assertTrue(snapshot['cancel_requested'])
            self.assertFalse(snapshot['cancel_acknowledged'])
            self.assertTrue(snapshot['physical_cleanup_confirmed'])
            self.assertEqual(snapshot['cleanup_state'], 'cleanup_unconfirmed')

    def test_real_late_exit_does_not_erase_expiration(self):
        class LateWorker(NativeWorker):
            def close(self):
                if self.created and not self.ledger.finished and self.ledger.expired:
                    self.write('release')
                    if self.api.WaitForSingleObject(self.process.handle, 2000) != 0:
                        self.ledger.fail('process_wait')
                super().close()
        with tempfile.TemporaryDirectory() as tmp:
            worker = LateWorker(Path(tmp)/'status')
            snapshot = Supervisor(worker).run()
            self.emit(snapshot)
            self.assertTrue(snapshot['deadline_expired'])
            self.assertEqual(snapshot['worker_state'], 'deadline_expired')
            self.assert_physical_and_classification(snapshot)

    def test_injected_unknown_member_refuses_bulk_stop_disarms_job_and_closes_only_known_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            worker = NativeWorker(Path(tmp)/'status')
            worker.ledger.origin = 'injected'
            worker.start()
            with patch('isolated_process_supervision.job_members', return_value=(2, True)), patch.object(
                    worker.job.api, 'TerminateJobObject', side_effect=AssertionError('bulk_stop_forbidden')) as bulk:
                with self.assertRaisesRegex(OSError, '^supervision_cleanup_unconfirmed$'):
                    worker.close()
                bulk.assert_not_called()
            snapshot = worker.ledger.snapshot()
            self.emit(snapshot)
            self.assertTrue(snapshot['unknown_members'])
            self.assertTrue(snapshot['bulk_termination_refused'])
            self.assertFalse(snapshot['job_quarantined'])
            self.assertTrue(snapshot['physical_cleanup_confirmed'])
            self.assertEqual(snapshot['cleanup_state'], 'cleanup_unconfirmed')
        print('INJECTED_UNKNOWN_JOB_MEMBER no_bulk_stop disarm_verified known_handle_exit_only')

    def test_injected_api_failures_preserve_error_and_attempt_other_resources(self):
        for fault in ('membership', 'job_terminate', 'job_query', 'wait', 'communication', 'attribute_delete'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as tmp:
                worker = NativeWorker(Path(tmp)/'status')
                worker.ledger.origin = 'injected'
                if fault == 'membership':
                    with patch.object(worker.api, 'IsProcessInJob', return_value=False):
                        snapshot = Supervisor(worker).run()
                elif fault == 'communication':
                    with patch.object(worker, 'read', side_effect=OSError('SYNTHETIC_SECRET')):
                        snapshot = Supervisor(worker).run()
                elif fault == 'attribute_delete':
                    # Start normally; inject deletion exception only at cleanup, keep storage alive.
                    worker.start()
                    worker.attribute_state = 'initialized'
                    worker.attribute_buffer = ctypes.create_string_buffer(128)
                    worker.job_values = (W.HANDLE*1)(worker.job.handle)
                    with patch.object(worker.api, 'DeleteProcThreadAttributeList', side_effect=OSError('SYNTHETIC_SECRET')):
                        with self.assertRaises(OSError):
                            worker.close()
                    snapshot = worker.ledger.snapshot()
                    self.assertIsNotNone(worker.attribute_buffer)
                else:
                    worker.start()
                    kernel = Kernel()
                    retained = duplicate_process(kernel, worker.api.GetCurrentProcess(), int(worker.process.handle))
                    try:
                        if fault == 'job_terminate':
                            context = patch.object(worker.job.api, 'TerminateJobObject', return_value=False)
                        elif fault == 'job_query':
                            query = worker.job.api.QueryInformationJobObject
                            context = patch.object(worker.job.api, 'QueryInformationJobObject',
                                                   side_effect=lambda h,c,*a: False if c == 3 else query(h,c,*a))
                        else:
                            context = patch.object(worker.api, 'WaitForSingleObject', return_value=258)
                        with context:
                            with self.assertRaises(OSError):
                                worker.close()
                        snapshot = worker.ledger.snapshot()
                        self.assertEqual(kernel.api.WaitForSingleObject(retained.handle, 5000), 0)
                    finally:
                        close_handle_once(retained, kernel.api)
                self.emit(snapshot)
                self.assertEqual(snapshot['cleanup_state'], 'cleanup_unconfirmed')
                self.assertTrue(worker.thread.close_state == worker.process.close_state == 'closed')
                self.assertNotIn('SYNTHETIC_SECRET', json.dumps(snapshot))

    def test_real_protected_handle_refuses_close_without_retry_and_other_resources_finish(self):
        with tempfile.TemporaryDirectory() as tmp:
            worker = NativeWorker(Path(tmp)/'status')
            worker.start()
            raw = worker.process.handle
            api = worker.api
            api.SetHandleInformation.argtypes = [W.HANDLE, W.DWORD, W.DWORD]
            api.SetHandleInformation.restype = W.BOOL
            self.assertTrue(api.SetHandleInformation(raw, 2, 2))
            try:
                with self.assertRaises(OSError):
                    worker.close()
                self.emit(worker.ledger.snapshot())
                self.assertTrue(worker.ledger.worker_exit)
                self.assertTrue(worker.ledger.job_zero)
                self.assertEqual(worker.process.close_state, 'failed')
                self.assertEqual(worker.thread.close_state, 'closed')
                self.assertEqual(worker.job.close_state, 'closed')
                self.assertEqual(worker.attribute_state, 'deleted')
                with self.assertRaises(OSError):
                    worker.close()
            finally:
                self.assertTrue(api.SetHandleInformation(raw, 2, 0))
                self.assertTrue(api.CloseHandle(raw))
        print('REAL_SUPERVISION_PROTECTED_CLOSE refused cleanup_unconfirmed no_retry')

    def crash_case(self, stage):
        kernel = Kernel()
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp)/'status'
            script = Path(__file__).with_name('isolated_process_supervision.py')
            launcher = subprocess.Popen([sys.executable,'-I','-S','-B',str(script),stage,str(marker)],
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                        text=True, close_fds=True, env=minimal_environment(tmp),
                                        creationflags=subprocess.CREATE_NO_WINDOW)
            child = outer = None
            lines = queue.Queue(maxsize=2)
            def receive():
                for _ in range(2 if stage == 'nested_after_start' else 1):
                    lines.put(launcher.stdout.readline(512))
            reader = threading.Thread(target=receive, daemon=True)
            reader.start()
            try:
                if stage == 'nested_after_start':
                    self.assertEqual(lines.get(timeout=10).strip(), 'prepare')
                    outer = OwnedJob()
                    outer.assign(launcher)
                    launcher.stdin.write('create\n');launcher.stdin.flush()
                value = json.loads(lines.get(timeout=10))
                self.assertTrue(set(value) == {'slot','stage','blocked','ownership_checked','unknown_members','job_disarmed'}, 'supervision_control_rejected')
                self.assertTrue(value['stage'] == stage and value['ownership_checked'], 'supervision_stage_rejected')
                self.assertIs(value['blocked'], stage != 'before_start')
                child = duplicate_process(kernel, int(launcher._handle), value['slot'])
                self.assertTrue(kernel.identity(child.handle)['start_ticks'] > kernel.identity(int(launcher._handle))['start_ticks'])
                self.assertIs(type(value['unknown_members']), bool)
                self.assertIs(type(value['job_disarmed']), bool)
                self.assertEqual(value['unknown_members'], value['job_disarmed'])
                outer_unknown = False
                if outer:
                    api = SimpleNamespace(QueryInformationJobObject=outer.api.QueryInformationJobObject,
                                          GetProcessId=kernel.api.GetProcessId)
                    count, unknown = job_members(api, outer, [int(launcher._handle), child.handle])
                    outer_unknown = unknown
                    if unknown:
                        disarm_job(outer)  # Keep outer open, but never armed with uncertain members.
                    elif count != 2:
                        raise OSError('supervision_outer_members_unconfirmed')
                launcher.kill();launcher.wait(timeout=5)
                termination_mode = 'kill_on_last_close'
                if value['job_disarmed']:
                    termination_mode = 'root_retained_process_handle'
                    from isolated_job_creation import extended_api
                    if kernel.api.WaitForSingleObject(child.handle, 0) != 0:
                        self.assertTrue(extended_api().TerminateProcess(child.handle, 1))
                self.assertEqual(kernel.api.WaitForSingleObject(child.handle, 5000), 0)
                if outer:
                    outer._confirm_empty()
                    self.assertTrue(outer.processes_confirmed)
                proof = dict(origin='win32', stage=stage, target_job_handles_in_root=0,
                             child_exit_confirmed=True, outer_zero_confirmed=bool(outer and outer.processes_confirmed),
                             unknown_target_members=value['unknown_members'],
                             target_job_disarmed=value['job_disarmed'], outer_unknown_members=outer_unknown,
                             termination_mode=termination_mode,
                             ownership_state='unconfirmed' if value['unknown_members'] or outer_unknown else 'known')
            finally:
                cleanup = CleanupStatus()
                # Guard the outer Job before any failure cleanup. Never issue a bulk termination.
                outer_releasable = True
                if outer:
                    try:
                        known = [int(launcher._handle)] + ([child.handle] if child else [])
                        api = SimpleNamespace(QueryInformationJobObject=outer.api.QueryInformationJobObject,
                                              GetProcessId=kernel.api.GetProcessId)
                        _, unknown = job_members(api, outer, known)
                        if unknown:
                            disarm_job(outer)
                    except Exception:
                        outer_releasable = False
                        cleanup.fail('session')
                def stop_launcher():
                    if launcher.poll() is None:
                        try:
                            launcher.stdin.write('cleanup\n');launcher.stdin.flush();launcher.wait(timeout=5)
                        except (OSError, subprocess.TimeoutExpired):
                            launcher.kill();launcher.wait(timeout=5)
                cleanup.attempt('provider', stop_launcher)
                if child:
                    def stop_child():
                        try:
                            if kernel.api.WaitForSingleObject(child.handle, 0) != 0:
                                from isolated_job_creation import extended_api
                                if not extended_api().TerminateProcess(child.handle, 1):
                                    raise OSError('supervision_emergency_stop_unconfirmed')
                            if kernel.api.WaitForSingleObject(child.handle, 5000) != 0:
                                raise OSError('supervision_emergency_exit_unconfirmed')
                        finally:
                            close_handle_once(child, kernel.api)
                    cleanup.attempt('provider', stop_child)
                if outer and outer_releasable:
                    def close_outer():
                        try:
                            outer._confirm_empty()
                        except Exception:
                            # No close at all if disarm fails. OS teardown remains a declared risk.
                            disarm_job(outer)
                            close_handle_once(outer, outer.api)
                            raise OSError('supervision_outer_zero_unconfirmed') from None
                        close_handle_once(outer, outer.api)
                    cleanup.attempt('session', close_outer)
                reader.join(timeout=2)
                if reader.is_alive():
                    cleanup.fail('reader')
                cleanup.attempt('stdin', launcher.stdin.close)
                cleanup.attempt('stdout', launcher.stdout.close)
                owner = SimpleNamespace(handle=launcher._handle.Detach(), close_state='open')
                cleanup.attempt('provider', lambda: close_handle_once(owner, kernel.api))
                cleanup.finish()
                self.assertTrue(cleanup.confirmed, 'supervision_root_cleanup_unconfirmed')
            proof['root_resources_closed'] = True
            print('REAL_SUPERVISION_LAUNCHER_CRASH ' + json.dumps(proof, sort_keys=True))

    def test_real_launcher_crash_before_worker_start_has_no_orphan(self):
        self.crash_case('before_start')

    def test_real_launcher_crash_after_blocked_worker_start_has_no_orphan(self):
        self.crash_case('after_start')

    def test_real_nested_launcher_crash_zero_while_outer_stays_open(self):
        self.crash_case('nested_after_start')
