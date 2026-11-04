"""Issue20: injected failures are separate from actual synthetic Win32 failures."""
import ctypes
from ctypes import wintypes as W
from concurrent.futures import Future
from pathlib import Path
import queue
import subprocess
import sys
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from observador.acceptance_metrics import OwnedJob, OwnedSampler, ProcessProbe
from observador.acceptance_prepare import CommandRunner, PreparationError
from observador.acceptance_report import empty_session
from observador.owned_channel import OwnedSyntheticChannel
from observador.owned_channel_protocol import ChannelError
from observador.private_directory import WindowsSecurity


class FakeKernel:
    """Only an injected API. Its BOOLs/errors are NOT a real Windows failure."""
    def __init__(self, *, close=True, terminate=True, query=True, mismatch=False):
        self.closes=[];self.memory_reads=0;self.duplicates=[]
        def close_handle(h):self.closes.append(h);return close
        def duplicate(current,source,target,out,access,inherit,options):
            self.duplicates.append((source,inherit));ctypes.cast(out,ctypes.POINTER(W.HANDLE))[0]=99;return True
        def times(h,created,*rest):
            ctypes.cast(created,ctypes.POINTER(W.FILETIME))[0].dwLowDateTime=20 if mismatch and h==99 else 10
            return True
        def memory(*args):self.memory_reads+=1;return True
        # ctypes function attributes can also be assigned to these test callables.
        self.CloseHandle=close_handle;self.GetCurrentProcess=lambda:-1;self.DuplicateHandle=duplicate
        self.WaitForSingleObject=lambda *a:258;self.GetProcessTimes=times;self.K32GetProcessMemoryInfo=memory
        self.TerminateJobObject=lambda *a:terminate;self.QueryInformationJobObject=lambda *a:query


def injected_job(api):
    job=OwnedJob.__new__(OwnedJob);job.api=api;job.handle=77;job.close_state='open'
    job.cleanup_confirmed=False;job.processes_confirmed=False;job._teardown_failed=False
    return job


class LifetimeInjectionTest(unittest.TestCase):
    def test_job_close_false_retains_reference_never_retries_and_terminates_all_callers(self):
        api=FakeKernel(close=False);job=injected_job(api)
        with self.assertRaisesRegex(OSError,'^cleanup_unconfirmed$'):job.close()
        self.assertEqual(job.handle,77);self.assertEqual(job.close_state,'failed')
        self.assertTrue(job.processes_confirmed);self.assertFalse(job.cleanup_confirmed)
        with self.assertRaises(OSError):job.close()
        self.assertEqual(api.closes,[77])
        pending=Future();channel=OwnedSyntheticChannel();channel._job=job
        channel._queue.put_nowait(('sample',None,pending));channel._cleanup()
        self.assertFalse(channel.snapshot()['shutdown_confirmed'])
        self.assertEqual(channel.snapshot()['last_error'],'cleanup_unconfirmed')
        with self.assertRaises(ChannelError):pending.result(timeout=.1)
        self.assertEqual(api.closes,[77])

    def test_job_termination_or_query_failure_still_closes_but_never_confirms(self):
        for option in ('terminate','query'):
            api=FakeKernel(**{option:False});job=injected_job(api)
            with self.subTest(option=option),self.assertRaisesRegex(OSError,'^cleanup_unconfirmed$'):job.close()
            self.assertEqual(api.closes,[77]);self.assertEqual(job.close_state,'closed')
            self.assertFalse(job.cleanup_confirmed)
            with self.assertRaises(OSError):job.close()
            self.assertEqual(api.closes,[77])

    def test_job_active_process_timeout_still_attempts_close(self):
        api=FakeKernel()
        def query(handle,kind,out,*rest):
            # Accounting's last four fields are DWORD; active is the penultimate.
            offset=4*ctypes.sizeof(ctypes.c_int64)+2*ctypes.sizeof(W.DWORD)
            W.DWORD.from_address(ctypes.addressof(out._obj)+offset).value=1
            return True
        api.QueryInformationJobObject=query;job=injected_job(api)
        with patch('observador.acceptance_metrics.time.monotonic',side_effect=[0,3]):
            with self.assertRaisesRegex(OSError,'^cleanup_unconfirmed$'):job.close()
        self.assertEqual(api.closes,[77]);self.assertFalse(job.processes_confirmed)

    def test_command_runner_joins_reader_closes_stdout_and_blocks_retry_after_job_error(self):
        api=FakeKernel(close=False);job=injected_job(api);job.assign=lambda process:None
        threads=[];original=threading.Thread
        def thread(**kw):
            result=original(**kw);threads.append(result);return result
        runner=CommandRunner()
        with patch('observador.acceptance_prepare.OwnedJob',return_value=job),patch('observador.acceptance_prepare.threading.Thread',side_effect=thread):
            with self.assertRaisesRegex(PreparationError,'^cleanup_unconfirmed$'):
                runner.run([sys.executable,'-c','print("SYNTHETIC")'],cwd=Path.cwd(),timeout=10)
        self.assertTrue(threads);self.assertFalse(any(t.is_alive() for t in threads))
        self.assertIsNotNone(runner.current.poll());self.assertTrue(runner.current.stdout.closed)
        self.assertFalse(runner.cleanup_confirmed);self.assertEqual(runner.last_error,'cleanup_unconfirmed')
        with self.assertRaisesRegex(PreparationError,'^cleanup_unconfirmed$'):
            runner.run([sys.executable,'-c','pass'],cwd=Path.cwd())
        runner.cancel();self.assertEqual(api.closes,[77])
        # Assignment itself can fail after spawn; even a clean job cannot prove
        # containment of that command's descendants. Never claim clean shutdown.
        good_api=FakeKernel();unassigned=injected_job(good_api)
        def denied(_):raise OSError('SYNTHETIC_ASSIGN_FAULT')
        unassigned.assign=denied;other=CommandRunner()
        with patch('observador.acceptance_prepare.OwnedJob',return_value=unassigned):
            with self.assertRaisesRegex(PreparationError,'^cleanup_unconfirmed$'):
                other.run([sys.executable,'-c','pass'],cwd=Path.cwd(),timeout=10)
        self.assertFalse(other.cleanup_confirmed);self.assertTrue(other.current.stdout.closed)
        self.assertIsNotNone(other.current.poll());self.assertTrue(unassigned.cleanup_confirmed)

    def test_failed_job_constructor_retains_owner_without_launching_command(self):
        api=FakeKernel(close=False)
        api.CreateJobObjectW=lambda *a:77
        api.SetInformationJobObject=lambda *a:False
        api.AssignProcessToJobObject=lambda *a:True
        runner=CommandRunner()
        with patch('observador.acceptance_metrics.sys.platform','win32'),patch('observador.acceptance_metrics.ctypes.WinDLL',return_value=api,create=True):
            with patch('observador.acceptance_prepare.subprocess.Popen') as launch:
                with self.assertRaisesRegex(PreparationError,'^cleanup_unconfirmed$'):
                    runner.run(['synthetic'],cwd=Path.cwd())
                launch.assert_not_called()
        self.assertEqual(runner.job.handle,77);self.assertFalse(runner.cleanup_confirmed)
        runner.cancel();self.assertEqual(api.closes,[77])

    def test_sampler_attempts_every_probe_keeps_failed_reference_and_no_invented_samples(self):
        closed=[]
        class Probe:
            def __init__(self,process):self.source=process
            def read(self):return 10,.1,100,200
            def close(self):
                closed.append(self.source)
                if self.source.bad:raise OSError('SYNTHETIC_SECRET_DO_NOT_EXPORT')
        a=SimpleNamespace(bad=True,poll=lambda:None);b=SimpleNamespace(bad=False,poll=lambda:None)
        data=empty_session();sampler=OwnedSampler(data,probe_factory=Probe)
        sampler.register('fixture',a);sampler.register('provider',b);sampler.close()
        self.assertEqual(closed,[a,b]);self.assertFalse(sampler.cleanup_confirmed)
        self.assertIs(sampler.failed_probes['fixture'].source,a);self.assertTrue(sampler.closed)
        self.assertEqual(data['metrics']['processes']['fixture']['availability'],'unavailable')
        self.assertNotIn('SYNTHETIC_SECRET',str(data));sampler.close();self.assertEqual(closed,[a,b])

    def test_probe_rejects_initial_identity_substitution_before_memory_read(self):
        api=FakeKernel(mismatch=True)
        with patch('observador.acceptance_metrics.sys.platform','win32'),patch('observador.acceptance_metrics.ctypes.WinDLL',return_value=api,create=True):
            probe=ProcessProbe()  # Source is our own current-process handle.
        with self.assertRaisesRegex(OSError,'^metrics_unavailable$'):probe.read()
        probe.close();self.assertEqual(api.memory_reads,0);self.assertEqual(api.closes,[99])
        self.assertEqual(api.duplicates,[(-1,False)])
        self.assertIs(api.CloseHandle.restype,W.BOOL)

    def test_failed_probe_close_is_sticky_and_sampler_registration_has_no_samples(self):
        api=FakeKernel(close=False,mismatch=True)
        def factory(_):
            with patch('observador.acceptance_metrics.sys.platform','win32'),patch('observador.acceptance_metrics.ctypes.WinDLL',return_value=api,create=True):
                return ProcessProbe()
        data=empty_session();sampler=OwnedSampler(data,probe_factory=factory)
        sampler.register('controller',current_controller=True);sampler.close()
        self.assertFalse(sampler.cleanup_confirmed);self.assertEqual(api.closes,[99])
        p=sampler.failed_probes['controller'];self.assertEqual(p.handle,99)
        with self.assertRaisesRegex(OSError,'^cleanup_unconfirmed$'):p.close()
        self.assertEqual(api.closes,[99]);self.assertEqual(data['metrics']['processes']['controller']['samples'],0)
        self.assertIsNone(data['metrics']['processes']['controller']['ram_working_set_sample_peak_bytes'])

    def test_token_close_failure_fails_closed_without_returning_sid_or_retrying(self):
        security=WindowsSecurity.__new__(WindowsSecurity);security.kernel=FakeKernel(close=False)
        opens=[]
        def open_token(process,access,out):
            opens.append(True);ctypes.cast(out,ctypes.POINTER(W.HANDLE))[0]=55;return True
        def denied(token,kind,data,size,out):
            ctypes.cast(out,ctypes.POINTER(W.DWORD))[0]=16;return False
        security.api=SimpleNamespace(OpenProcessToken=open_token,GetTokenInformation=denied)
        with self.assertRaisesRegex(OSError,'^cleanup_unconfirmed$'):security.user_sid()
        with self.assertRaisesRegex(OSError,'^cleanup_unconfirmed$'):security.user_sid()
        self.assertEqual(opens,[True]);self.assertEqual(security.kernel.closes,[55])
        self.assertEqual(security._failed_token.handle,55)


@unittest.skipUnless(sys.platform=='win32','Requires real Windows kernel process/handle execution')
class WindowsLifetimeTest(unittest.TestCase):
    def release_protected_test_handle(self,api,handle):
        # Test-only recovery: this handle was deliberately protected and is still
        # live/owned. Never a production retry of an uncertain recycled slot.
        self.assertTrue(api.SetHandleInformation(handle,2,0))
        self.assertTrue(api.CloseHandle(handle))

    def protect(self,api,handle):
        api.SetHandleInformation.argtypes=[W.HANDLE,W.DWORD,W.DWORD]
        api.SetHandleInformation.restype=W.BOOL
        self.assertTrue(api.SetHandleInformation(handle,2,2))

    def owned_child(self):
        child=subprocess.Popen([sys.executable,'-I','-S','-c','import time;time.sleep(60)'])
        def stop():
            if child.poll() is None:child.kill()
            child.wait(timeout=5)
        self.addCleanup(stop)
        return child

    def descendant_job(self):
        job=OwnedJob()
        script='import subprocess,sys,time;sys.stdin.readline();subprocess.Popen([sys.executable,"-I","-S","-c","import time;time.sleep(60)"]);print("DESCENDANT_READY",flush=True);time.sleep(60)'
        process=subprocess.Popen([sys.executable,'-I','-S','-u','-c',script],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
        def cleanup():
            try:job.close()
            except OSError:pass
            if process.poll() is None:process.kill()
            process.wait(timeout=5);process.stdin.close();process.stdout.close()
        self.addCleanup(cleanup)
        job.assign(process);process.stdin.write('start\n');process.stdin.flush()
        lines=queue.Queue();reader=threading.Thread(target=lambda:lines.put(process.stdout.readline()),daemon=True);reader.start()
        self.assertEqual(lines.get(timeout=10).strip(),'DESCENDANT_READY');reader.join(timeout=2)
        self.assertFalse(reader.is_alive())
        accounting=ctypes.create_string_buffer(48)  # JOBOBJECT_BASIC_ACCOUNTING_INFORMATION on Win32/64.
        self.assertTrue(job.api.QueryInformationJobObject(job.handle,1,accounting,48,None))
        self.assertGreaterEqual(W.DWORD.from_buffer(accounting,40).value,2)
        return job,process

    def test_real_protected_job_close_fails_and_descendants_are_confirmed_terminated(self):
        job,process=self.descendant_job();raw=job.handle;self.protect(job.api,raw)
        self.addCleanup(self.release_protected_test_handle,job.api,raw)
        with self.assertRaisesRegex(OSError,'^cleanup_unconfirmed$'):job.close()
        self.assertNotEqual(ctypes.get_last_error(),0)
        self.assertEqual(job.handle,raw);self.assertEqual(job.close_state,'failed')
        self.assertFalse(job.cleanup_confirmed);self.assertTrue(job.processes_confirmed)
        process.wait(timeout=5)
        with self.assertRaises(OSError):job.close()
        print('REAL_PROTECTED_JOB_CLOSE_REJECTED cleanup_unconfirmed descendants_zero adapter_off')

    def test_real_job_termination_confirms_descendant_exit_and_close_is_idempotent(self):
        job,process=self.descendant_job();job.close();process.wait(timeout=5)
        self.assertTrue(job.cleanup_confirmed);self.assertTrue(job.processes_confirmed)
        self.assertEqual(job.close_state,'closed');self.assertIsNone(job.handle);job.close()
        print('REAL_JOB_DESCENDANTS_ZERO_CONFIRMED checked_close adapter_off')

    def test_real_probe_protected_close_is_not_silently_discarded(self):
        child=self.owned_child();probe=ProcessProbe(child);raw=probe.handle
        self.protect(probe.kernel,raw);self.addCleanup(self.release_protected_test_handle,probe.kernel,raw)
        with self.assertRaisesRegex(OSError,'^cleanup_unconfirmed$'):probe.close()
        self.assertNotEqual(ctypes.get_last_error(),0);self.assertEqual(probe.handle,raw)
        with self.assertRaises(OSError):probe.close()
        self.assertIsNone(child.poll())
        print('REAL_PROTECTED_PROBE_CLOSE_REJECTED retained_reference no_retry')

    def test_real_probe_duplicates_retained_identity_noninherited_and_refuses_exited_child(self):
        child=self.owned_child();probe=ProcessProbe(child);self.addCleanup(probe.close)
        compare=ctypes.WinDLL('kernelbase',use_last_error=True).CompareObjectHandles
        compare.argtypes=[W.HANDLE,W.HANDLE];compare.restype=W.BOOL
        self.assertTrue(compare(int(child._handle),probe.handle))
        self.assertEqual(probe.creation,probe._creation(int(child._handle)))
        flags=W.DWORD();probe.kernel.GetHandleInformation.argtypes=[W.HANDLE,ctypes.POINTER(W.DWORD)]
        self.assertTrue(probe.kernel.GetHandleInformation(probe.handle,ctypes.byref(flags)));self.assertEqual(flags.value&1,0)
        sample=probe.read();self.assertEqual(sample[0],probe.creation)
        child.kill();child.wait(timeout=5)
        with self.assertRaisesRegex(OSError,'^metrics_unavailable$'):probe.read()
        with self.assertRaisesRegex(OSError,'^metrics_unavailable$'):ProcessProbe(child)
        print('REAL_OWNED_METRIC_IDENTITY_VERIFIED duplicate_same_object noninherited exited_refused no_pid_reuse_claim')
