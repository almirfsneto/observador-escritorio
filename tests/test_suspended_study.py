"""AI03 isolated Win32 study. Production launchers are deliberately unchanged."""
import ctypes
import json
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from observador.owned_channel_win32 import Kernel
from observador.win32_handles import close_handle_once
from isolated_suspended_spawn import SuspendedProbe,kernel_api,duplicate_owned_launcher_child,minimal_environment


@unittest.skipUnless(sys.platform=='win32','Requires real Windows kernel process/handle execution')
class WindowsSuspendedStudyTest(unittest.TestCase):
    def test_real_primary_cannot_execute_until_membership_and_resume_no_inherited_decoy(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker=Path(tmp)/'synthetic.started';kernel=Kernel();read,write=kernel.pipe()
            try:
                kernel.inherit(read,True)
                probe=SuspendedProbe(marker)
                try:
                    self.assertEqual(probe.api.WaitForSingleObject(probe.process.handle,0),258)
                    self.assertFalse(marker.exists())
                    self.assertTrue(kernel.no_inherited_objects(probe.process.handle,[read,write]))
                    with self.assertRaisesRegex(OSError,'^isolated_resume_refused$'):probe.resume()
                    probe.assign();self.assertFalse(marker.exists());probe.resume()
                    until=time.monotonic()+8
                    while not marker.exists() and time.monotonic()<until:time.sleep(.01)
                    self.assertEqual(marker.read_bytes(),b'1')
                    accounting=ctypes.create_string_buffer(48)
                    self.assertTrue(probe.job.api.QueryInformationJobObject(probe.job.handle,1,accounting,48,None))
                    from ctypes import wintypes as W
                    self.assertGreaterEqual(W.DWORD.from_buffer(accounting,40).value,2)
                finally:probe.close()
                self.assertTrue(probe.job.processes_confirmed);self.assertTrue(probe.status.confirmed)
                self.assertTrue(probe.diagnostic.process_exit_confirmed)
                print('ISOLATED_CLEANUP_CONFIRMED '+json.dumps(probe.diagnostic.snapshot(probe),sort_keys=True))
            finally:
                kernel.inherit(read,False);kernel.close(read);kernel.close(write)
        print('REAL_SUSPENDED_MEMBERSHIP_BEFORE_RESUME no_inherited_decoy descendants_zero isolated_only')

    def test_injected_pre_resume_errors_cleanup_real_suspended_children(self):
        for fault in ('before_assign','after_assign','assign','membership','resume'):
            with tempfile.TemporaryDirectory() as tmp:
                marker=Path(tmp)/'synthetic.started';probe=SuspendedProbe(marker)
                try:
                    if fault=='assign':
                        with patch.object(probe.job.api,'AssignProcessToJobObject',return_value=False):
                            with self.assertRaisesRegex(OSError,'^owned_job_unavailable$'):probe.start()
                    elif fault=='membership':
                        with patch.object(probe.api,'IsProcessInJob',return_value=False):
                            with self.assertRaisesRegex(OSError,'^isolated_job_membership_unconfirmed$'):probe.start()
                    elif fault=='resume':
                        with patch.object(probe.api,'ResumeThread',return_value=0xffffffff):
                            with self.assertRaisesRegex(OSError,'^isolated_resume_failed$'):probe.start()
                    else:
                        with self.assertRaisesRegex(OSError,'^injected_pre_resume_failure$'):probe.start(fault)
                    self.assertFalse(marker.exists())
                finally:probe.close()
                self.assertTrue(probe.status.confirmed);self.assertFalse(marker.exists())
        print('REAL_SUSPENDED_CHILDREN_CLEANED_AFTER_INJECTED_FAILURES no_resume no_production_integration')

    def test_real_protected_process_handle_stays_unconfirmed_and_other_handles_close(self):
        from ctypes import wintypes as W
        with tempfile.TemporaryDirectory() as tmp:
            probe=SuspendedProbe(Path(tmp)/'synthetic.started');api=probe.api;raw=probe.process.handle
            api.SetHandleInformation.argtypes=[W.HANDLE,W.DWORD,W.DWORD];api.SetHandleInformation.restype=W.BOOL
            self.assertTrue(api.SetHandleInformation(raw,2,2))
            try:
                with self.assertRaisesRegex(OSError,'^isolated_cleanup_unconfirmed$'):probe.close()
                snapshot=probe.diagnostic.snapshot(probe)
                self.assertEqual(snapshot['first_failure'],'process_handle_close')
                self.assertEqual(snapshot['handles'],{'process':'failed','thread':'closed'})
                self.assertTrue(snapshot['process_exit_confirmed']);self.assertFalse(probe.status.confirmed)
                self.assertEqual(api.WaitForSingleObject(raw,0),0)
                with self.assertRaises(OSError):probe.close() # No numeric slot retry.
            finally:
                # Test-only recovery of our still-live, deliberately protected handle.
                self.assertTrue(api.SetHandleInformation(raw,2,0));self.assertTrue(api.CloseHandle(raw))
        print('REAL_PROTECTED_SUSPENDED_HANDLE_REJECTED process_exited cleanup_unconfirmed no_retry')

    def test_real_exit_race_requires_signaled_process_with_injected_initial_wait(self):
        with tempfile.TemporaryDirectory() as tmp:
            probe=SuspendedProbe(Path(tmp)/'synthetic.started')
            try:
                probe.assign();probe.job.close()
                self.assertEqual(probe.api.WaitForSingleObject(probe.process.handle,2000),0)
                probe.diagnostic_origin='win32_with_injected_wait'
                wait=probe.api.WaitForSingleObject;calls=[]
                def initial_timeout(handle,milliseconds):
                    calls.append(milliseconds)
                    return 258 if len(calls)==1 else wait(handle,milliseconds)
                with patch.object(probe.api,'WaitForSingleObject',side_effect=initial_timeout):probe.close()
                snapshot=probe.diagnostic.snapshot(probe)
                self.assertTrue(snapshot['exit_race_confirmed']);self.assertTrue(snapshot['process_exit_confirmed'])
                self.assertEqual(snapshot['native_errors']['process_fallback'],'access_denied')
                self.assertTrue(probe.status.confirmed)
            finally:probe.close()
        print('REAL_TERMINATE_EXITED_PROCESS_REJECTED initial_wait_injected final_exit_and_job_confirmed')

    def crash_case(self,phase):
        api=kernel_api()
        with tempfile.TemporaryDirectory() as tmp:
            marker=Path(tmp)/'synthetic.started';script=Path(__file__).with_name('isolated_suspended_spawn.py')
            launcher=subprocess.Popen([sys.executable,'-I','-S','-B',str(script),'--crash-fixture',phase,str(marker)],
                                      stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,
                                      env=minimal_environment(tmp),creationflags=subprocess.CREATE_NO_WINDOW)
            child=None;reader=None
            try:
                lines=queue.Queue(maxsize=1);reader=threading.Thread(target=lambda:lines.put(launcher.stdout.readline()),daemon=True)
                reader.start();line=lines.get(timeout=10).strip().split(' ')
                self.assertEqual(line[0],'ready');self.assertEqual(len(line),2);self.assertLessEqual(len(line[1]),20)
                child=duplicate_owned_launcher_child(api,launcher,int(line[1]));self.assertGreater(api.GetProcessId(child.handle),0)
                self.assertEqual(api.WaitForSingleObject(child.handle,0),258);self.assertFalse(marker.exists())
                launcher.kill();launcher.wait(timeout=5) # Actual crash: no finally in the launcher.
                if phase=='after_assign':self.assertEqual(api.WaitForSingleObject(child.handle,5000),0)
                else:self.assertEqual(api.WaitForSingleObject(child.handle,200),258)
                self.assertFalse(marker.exists())
            finally:
                if launcher.poll() is None:
                    try:launcher.stdin.write('cleanup\n');launcher.stdin.flush();launcher.wait(timeout=5)
                    except (OSError,subprocess.TimeoutExpired):launcher.kill();launcher.wait(timeout=5)
                if child is not None:
                    if api.WaitForSingleObject(child.handle,0)!=0:self.assertTrue(api.TerminateProcess(child.handle,1))
                    self.assertEqual(api.WaitForSingleObject(child.handle,5000),0);close_handle_once(child,api)
                if reader:reader.join(timeout=2);self.assertFalse(reader.is_alive())
                launcher.stdin.close();launcher.stdout.close()

    def test_real_parent_crash_after_assignment_kills_suspended_child(self):
        self.crash_case('after_assign')
        print('REAL_POST_ASSIGN_PARENT_CRASH child_exited_before_resume isolated_only')

    def test_real_parent_crash_before_assignment_demonstrates_remaining_gap_then_root_cleans(self):
        self.crash_case('before_assign')
        print('REAL_PRE_ASSIGN_PARENT_CRASH_GAP suspended_child_survived root_owned_capability_cleanup_verified')
