"""AI01/02. Injection is distinct from actual owned Win32 resources."""
import ctypes
from ctypes import wintypes as W
from datetime import datetime,timedelta,timezone
from pathlib import Path
import subprocess
import sys
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from observador.cleanup import CleanupStatus,RESOURCES
from observador.owned_identity import OwnedProcessIdentity,creation_ticks
from observador.native_session import NativeSession
from observador.lab_controller import LaboratoryWindow
from observador.acceptance_session import AcceptanceLaboratory
from observador.acceptance_metrics import OwnedSampler
from observador.acceptance_report import empty_session


class FakeProcess:
    def __init__(self,fault=None):self.done=False;self.calls=[];self.fault=fault
    def poll(self):return 0 if self.done else None
    def terminate(self):
        self.calls.append('terminate')
        if self.fault=='terminate':raise RuntimeError('SYNTHETIC_PRIVATE_SENTINEL')
        self.done=True
    def kill(self):self.calls.append('kill');self.done=True
    def wait(self,**kw):
        self.calls.append('wait')
        if self.fault=='wait':self.fault=None;raise TypeError('SYNTHETIC_PRIVATE_SENTINEL')
        return 0


class FakeAPI:
    def __init__(self,mismatch=False,closed=True):
        self.closes=[];self.duplicates=[]
        self.GetCurrentProcess=lambda:-1;self.GetProcessId=lambda h:7
        self.WaitForSingleObject=lambda *a:258
        def times(h,created,*args):
            ctypes.cast(created,ctypes.POINTER(W.FILETIME))[0].dwLowDateTime=20 if mismatch and h==9 else 10
            return True
        def duplicate(current,source,target,out,rights,inherit,options):
            self.duplicates.append((source,rights,inherit));ctypes.cast(out,ctypes.POINTER(W.HANDLE))[0]=9;return True
        def close(h):self.closes.append(h);return closed
        self.GetProcessTimes=times;self.DuplicateHandle=duplicate;self.CloseHandle=close


class LegacyInjectionTest(unittest.TestCase):
    def test_initial_identity_substitution_and_close_failure_prevent_provider_launch(self):
        for mismatch,closed,code in ((True,True,'owned_identity_unavailable'),(False,False,'cleanup_unconfirmed')):
            calls=[]
            class Owned:
                pid=7;_handle=8
                def __init__(self,*args,**kw):
                    calls.append(args)
                    if args:raise AssertionError('provider_must_not_launch')
                def poll(self):return None
            process=Owned();api=FakeAPI(mismatch,closed)
            with patch('observador.owned_identity.sys.platform','win32'),patch('observador.owned_identity.subprocess.Popen',Owned),patch('observador.owned_identity.ctypes.WinDLL',return_value=api,create=True):
                with self.assertRaisesRegex(OSError,'^'+code+'$') as error:
                    NativeSession(process,'synthetic',datetime.now(timezone.utc)+timedelta(seconds=10))
            self.assertEqual(len(calls),1);self.assertEqual(api.closes,[9])
            self.assertEqual(api.duplicates,[(8,0x1000|0x100000,False)])
            if not closed:
                owner=error.exception.resource;self.assertEqual(owner.handle,9)
                with self.assertRaises(OSError):owner.close()
                self.assertEqual(api.closes,[9])

    def test_bare_pid_is_rejected_without_kernel_lookup(self):
        with patch('observador.owned_identity.sys.platform','win32'),patch('observador.owned_identity.ctypes.WinDLL',create=True) as dll:
            with self.assertRaisesRegex(OSError,'^owned_identity_unavailable$'):creation_ticks(7)
            dll.assert_not_called()

    def test_sink_and_session_errors_cannot_prevent_fixture_kill(self):
        window=LaboratoryWindow.__new__(LaboratoryWindow);window.cleanup_status=CleanupStatus()
        provider=FakeProcess();fixture=FakeProcess('terminate');calls=[]
        def failed(name):
            def action():calls.append(name);raise TypeError('SYNTHETIC_PRIVATE_SENTINEL')
            return action
        window.session=SimpleNamespace(close=failed('session'),process=provider,cleanup_confirmed=False)
        window.sink=SimpleNamespace(close=failed('sink'),worker=SimpleNamespace(is_alive=lambda:False))
        window.fixture=fixture;window._cleanup()
        self.assertEqual(calls,['session','sink']);self.assertIn('kill',fixture.calls)
        self.assertTrue(provider.done);self.assertTrue(fixture.done)
        snapshot=window.cleanup_snapshot();self.assertEqual(snapshot['status'],'cleanup_unconfirmed')
        self.assertEqual(set(snapshot['errors']),set(RESOURCES));self.assertNotIn('SENTINEL',str(snapshot))
        before=list(fixture.calls);window._cleanup();self.assertEqual(fixture.calls,before)

    def test_secondary_or_sampler_error_does_not_skip_other_cleanup_or_report(self):
        for fault in ('terminate','wait','sampler'):
            lab=AcceptanceLaboratory.__new__(AcceptanceLaboratory);lab.cleanup_status=CleanupStatus()
            lab.session=None;lab.fixture=FakeProcess();lab.secondary=FakeProcess(None if fault=='sampler' else fault)
            lab.sink=None;lab.sampling_lock=threading.RLock();lab.sampling_closed=False;calls=[]
            def close():
                calls.append('sampler')
                if fault=='sampler':raise ValueError('SYNTHETIC_PRIVATE_SENTINEL')
            lab.sampler=SimpleNamespace(close=close,cleanup_confirmed=fault!='sampler')
            lab.recorder=SimpleNamespace(data=empty_session())
            lab._cleanup()
            self.assertEqual(calls,['sampler']);self.assertTrue(lab.sampling_closed)
            self.assertTrue(lab.fixture.done);self.assertTrue(lab.secondary.done)
            self.assertIs(lab.recorder.data['children_stopped'],False)
            self.assertEqual(lab.cleanup_snapshot()['status'],'cleanup_unconfirmed')
            lab._cleanup();self.assertEqual(calls,['sampler'])

    def test_native_close_continues_after_process_thread_and_pipe_exceptions(self):
        session=NativeSession.__new__(NativeSession);session.cleanup_status=CleanupStatus()
        session.lock=threading.RLock();session.closed=False;session.stream=SimpleNamespace(stop=lambda:None)
        session._enqueue=lambda _:None;process=FakeProcess('wait');session.process=process;calls=[]
        def fail(name):
            def action(**kw):calls.append(name);raise RuntimeError('SYNTHETIC_PRIVATE_SENTINEL')
            return action
        process.stdin=SimpleNamespace(close=fail('stdin'));process.stdout=SimpleNamespace(close=fail('stdout'))
        session.reader=SimpleNamespace(join=fail('reader'),is_alive=lambda:False)
        session.writer=SimpleNamespace(join=lambda **kw:calls.append('writer'),is_alive=lambda:False)
        session.close();self.assertIn('kill',process.calls)
        self.assertEqual(calls,['reader','stdout','writer','stdin']);self.assertFalse(session.cleanup_confirmed)
        self.assertNotIn('SENTINEL',str(session.cleanup_status.snapshot()))
        before=list(calls);session.close();self.assertEqual(calls,before)

    def test_live_reader_does_not_close_locked_stdout_or_skip_writer(self):
        session=NativeSession.__new__(NativeSession);session.cleanup_status=CleanupStatus()
        session.lock=threading.RLock();session.closed=False;session.stream=SimpleNamespace(stop=lambda:None)
        session._enqueue=lambda _:None;session.process=FakeProcess();session.process.done=True;closed=[]
        session.process.stdin=SimpleNamespace(close=lambda:closed.append('stdin'))
        session.process.stdout=SimpleNamespace(close=lambda:closed.append('stdout'))
        session.reader=SimpleNamespace(join=lambda **kw:None,is_alive=lambda:True)
        session.writer=SimpleNamespace(join=lambda **kw:None,is_alive=lambda:False)
        session.close();self.assertEqual(closed,['stdin']);self.assertFalse(session.cleanup_confirmed)

    def test_native_thread_start_error_attempts_provider_and_both_pipes(self):
        process=FakeProcess('wait');closed=[]
        process.stdin=SimpleNamespace(close=lambda:closed.append('stdin'))
        process.stdout=SimpleNamespace(close=lambda:closed.append('stdout'))
        def failed(**kw):raise RuntimeError('SYNTHETIC_PRIVATE_SENTINEL')
        thread=SimpleNamespace(start=failed,join=failed,is_alive=lambda:False)
        with patch('observador.native_session.creation_ticks',return_value=504911232000000010),patch('observador.native_session.subprocess.Popen',return_value=process),patch('observador.native_session.threading.Thread',return_value=thread):
            with self.assertRaisesRegex(OSError,'^native_start_unconfirmed$') as error:
                NativeSession(SimpleNamespace(pid=7),'synthetic',datetime.now(timezone.utc)+timedelta(seconds=5))
        self.assertTrue(process.done);self.assertIn('kill',process.calls)
        self.assertEqual(closed,['stdout','stdin']);self.assertFalse(error.exception.resource.cleanup_confirmed)

    def test_successful_cleanup_can_confirm_only_after_every_resource(self):
        lab=AcceptanceLaboratory.__new__(AcceptanceLaboratory);lab.cleanup_status=CleanupStatus()
        lab.session=None;lab.sink=None;lab.fixture=FakeProcess();lab.secondary=FakeProcess()
        lab.sampling_lock=threading.RLock();lab.sampling_closed=False
        lab.sampler=SimpleNamespace(close=lambda:None,cleanup_confirmed=True)
        lab.recorder=SimpleNamespace(data=empty_session())
        self.assertFalse(lab.cleanup_status.confirmed);lab._cleanup()
        self.assertIs(lab.recorder.data['children_stopped'],True)


@unittest.skipUnless(sys.platform=='win32','Requires real Windows kernel process/handle execution')
class WindowsLegacyCleanupTest(unittest.TestCase):
    def child(self,pipes=False):
        process=subprocess.Popen([sys.executable,'-I','-S','-c','import time;time.sleep(40)'],
                                 stdin=subprocess.PIPE if pipes else None,stdout=subprocess.PIPE if pipes else None)
        def cleanup():
            if process.poll() is None:process.kill()
            process.wait(timeout=5)
            for stream in (process.stdin,process.stdout):
                if stream:stream.close()
        self.addCleanup(cleanup);return process

    def test_real_legacy_binding_matches_retained_object_and_refuses_exit(self):
        child=self.child();owner=OwnedProcessIdentity(child);self.addCleanup(owner.close)
        compare=ctypes.WinDLL('kernelbase',use_last_error=True).CompareObjectHandles
        compare.argtypes=[W.HANDLE,W.HANDLE];compare.restype=W.BOOL
        self.assertTrue(compare(int(child._handle),owner.handle));self.assertEqual(creation_ticks(child),owner.ticks())
        flags=W.DWORD();owner.api.GetHandleInformation.argtypes=[W.HANDLE,ctypes.POINTER(W.DWORD)]
        self.assertTrue(owner.api.GetHandleInformation(owner.handle,ctypes.byref(flags)));self.assertEqual(flags.value&1,0)
        child.kill();child.wait(timeout=5)
        with self.assertRaises(OSError):owner.ticks()
        with self.assertRaises(OSError):creation_ticks(child)
        print('REAL_LEGACY_RETAINED_BINDING_VERIFIED same_object noninherited exited_refused no_pid_reuse_claim')

    def test_real_protected_binding_close_refuses_provider_launch(self):
        child=self.child();owner=OwnedProcessIdentity(child);api=owner.api;raw=owner.handle
        api.SetHandleInformation.argtypes=[W.HANDLE,W.DWORD,W.DWORD];api.SetHandleInformation.restype=W.BOOL
        self.assertTrue(api.SetHandleInformation(raw,2,2))
        def release():
            self.assertTrue(api.SetHandleInformation(raw,2,0));self.assertTrue(api.CloseHandle(raw))
        self.addCleanup(release)
        with patch('observador.owned_identity.OwnedProcessIdentity',return_value=owner),patch('observador.native_session.subprocess.Popen') as launch:
            with self.assertRaisesRegex(OSError,'^cleanup_unconfirmed$') as error:
                NativeSession(child,'synthetic',datetime.now(timezone.utc)+timedelta(seconds=5))
            launch.assert_not_called()
        self.assertIs(error.exception.resource,owner);self.assertEqual(owner.handle,raw)
        self.assertIsNone(child.poll());print('REAL_LEGACY_PROTECTED_CLOSE_REJECTED provider_not_launched')

    def test_real_owned_children_and_io_cleanup_survive_injected_sink_failure(self):
        fixture=self.child();secondary=self.child();provider=self.child(pipes=True)
        session=NativeSession.__new__(NativeSession);session.fixture=fixture;session.process=provider
        session.lock=threading.RLock();session.closed=False;session.cleanup_status=CleanupStatus()
        session.stream=SimpleNamespace(stop=lambda:None);session._enqueue=lambda _:None
        session.reader=threading.Thread(target=provider.stdout.read,daemon=True)
        session.writer=threading.Thread(target=lambda:None,daemon=True);session.reader.start();session.writer.start()
        data=empty_session();sampler=OwnedSampler(data);sampler.register('controller',current_controller=True)
        sampler.register('fixture',fixture);sampler.register('fixture_secondary',secondary);sampler.register('provider',provider)
        lab=AcceptanceLaboratory.__new__(AcceptanceLaboratory);lab.cleanup_status=CleanupStatus()
        lab.fixture=fixture;lab.secondary=secondary;lab.session=session;lab.sampler=sampler
        lab.sampling_lock=threading.RLock();lab.sampling_closed=False
        lab.recorder=SimpleNamespace(data=data,observe=lambda _:None)
        def fail():raise ValueError('SYNTHETIC_PRIVATE_SENTINEL')
        lab.sink=SimpleNamespace(close=fail,worker=SimpleNamespace(is_alive=lambda:False),written=0,discarded=0,purged=0)
        lab._cleanup()
        self.assertTrue(all(p.poll() is not None for p in (fixture,secondary,provider)))
        self.assertFalse(session.reader.is_alive());self.assertFalse(session.writer.is_alive())
        self.assertTrue(provider.stdin.closed);self.assertTrue(provider.stdout.closed)
        self.assertTrue(sampler.cleanup_confirmed);self.assertIs(data['children_stopped'],False)
        self.assertGreater(lab.cleanup_snapshot()['errors']['sink'],0)
        print('REAL_OWNED_CLEANUP_WITH_INJECTED_SINK_ERROR all_children_exited metrics_closed acceptance_false')
