"""Stop callers, not direct cleanup: injected errors cannot strand owned resources."""
from datetime import datetime,timedelta,timezone
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from observador.acceptance_session import AcceptanceLaboratory
from observador.acceptance_report import empty_session
from observador.acceptance_metrics import OwnedSampler
from observador.native_session import NativeSession
from observador.cleanup import CleanupStatus
from observador.lab_queue import AsyncLabQueue


class Process:
    def __init__(self,name,calls):self.name=name;self.calls=calls;self.done=False
    def poll(self):return 0 if self.done else None
    def terminate(self):self.calls.append(self.name);self.done=True
    def kill(self):self.calls.append(self.name+'_kill');self.done=True
    def wait(self,**kw):return 0


def fake_lab(fault=None):
    lab=AcceptanceLaboratory.__new__(AcceptanceLaboratory);calls=[]
    lab.cleanup_status=CleanupStatus();lab.finished=False;lab.cleanup=None;lab.failed_binding=None
    lab.tk=SimpleNamespace(DISABLED='disabled');lab.sampling_lock=threading.RLock();lab.sampling_closed=False
    now=datetime.now(timezone.utc)
    def action(name):
        def run(*args,**kw):
            calls.append(name)
            if name==fault:raise OSError('SYNTHETIC_PRIVATE_SENTINEL')
        return run
    stream=SimpleNamespace(stop=action('stream'),clock=lambda:now,expires_at=now+timedelta(minutes=15),
                           monotonic=lambda:0,deadline=900,stopped=False)
    lab.fixture=Process('fixture',calls);lab.secondary=Process('secondary',calls);provider=Process('provider',calls)
    lab.session=SimpleNamespace(close=action('session'),process=provider,cleanup_confirmed=True,stream=stream)
    lab.sink=SimpleNamespace(close=action('sink'),worker=SimpleNamespace(is_alive=lambda:False),written=0,discarded=0,purged=0)
    lab.sampler=SimpleNamespace(close=action('sampler'),cleanup_confirmed=True)
    lab.recorder=SimpleNamespace(data=empty_session(),observe=action('observation'))
    for name in ('launch_btn','start_btn','pause_btn','stop_btn','persist_box','secondary_btn'):
        setattr(lab,name,SimpleNamespace(config=action(name)))
    lab.status_var=SimpleNamespace(set=action('status'))
    return lab,calls


def assert_cleaned(test,lab,calls,confirmed=False):
    if lab.cleanup and lab.cleanup.ident is not None:lab.cleanup.join(timeout=20)
    test.assertTrue(lab.cleanup_status.finished)
    for name in ('session','sink','provider','fixture','secondary','sampler'):test.assertEqual(calls.count(name),1,name)
    test.assertTrue(lab.fixture.done);test.assertTrue(lab.secondary.done);test.assertTrue(lab.session.process.done)
    test.assertTrue(lab.sampling_closed);test.assertIs(lab.recorder.data['children_stopped'],confirmed)
    test.assertEqual(lab.cleanup_status.confirmed,confirmed)
    test.assertNotIn('SENTINEL',str(lab.cleanup_snapshot()))
    before=list(calls);lab.stop();test.assertEqual(calls,before)


class StopPreworkerInjectionTest(unittest.TestCase):
    def test_stream_and_each_tk_or_observation_error_still_start_cleanup(self):
        for fault in ('stream','launch_btn','start_btn','pause_btn','stop_btn','persist_box','secondary_btn','status','observation'):
            with self.subTest(fault=fault):
                lab,calls=fake_lab(fault);lab.stop();assert_cleaned(self,lab,calls)
                self.assertGreater(sum(lab.cleanup_snapshot()['errors'].values()),0)

    def test_thread_constructor_failure_runs_synchronous_cleanup(self):
        lab,calls=fake_lab()
        with patch('observador.lab_controller.threading.Thread',side_effect=RuntimeError('SYNTHETIC_PRIVATE_SENTINEL')):lab.stop()
        self.assertIsNone(lab.cleanup);assert_cleaned(self,lab,calls)
        self.assertGreater(lab.cleanup_snapshot()['errors']['cleanup_worker'],0)

    def test_thread_start_failure_runs_synchronous_cleanup(self):
        lab,calls=fake_lab()
        with patch.object(threading.Thread,'start',side_effect=RuntimeError('SYNTHETIC_PRIVATE_SENTINEL')):lab.stop()
        self.assertIsNone(lab.cleanup.ident);assert_cleaned(self,lab,calls)
        self.assertGreater(lab.cleanup_snapshot()['errors']['cleanup_worker'],0)

    def test_start_raises_after_launch_does_not_double_cleanup_or_publish_success(self):
        lab,calls=fake_lab();start=threading.Thread.start
        def launched_then_failed(thread):start(thread);raise RuntimeError('SYNTHETIC_PRIVATE_SENTINEL')
        with patch.object(threading.Thread,'start',launched_then_failed):lab.stop()
        assert_cleaned(self,lab,calls)
        self.assertGreater(lab.cleanup_snapshot()['errors']['cleanup_worker'],0)

    def test_unstarted_worker_join_failure_does_not_escape_run_finally(self):
        lab,calls=fake_lab();lab.root=SimpleNamespace(mainloop=lambda:None)
        with patch.object(threading.Thread,'start',side_effect=RuntimeError('SYNTHETIC_PRIVATE_SENTINEL')):lab.run()
        assert_cleaned(self,lab,calls)

    def test_positive_stop_can_confirm_after_all_resources(self):
        lab,calls=fake_lab();lab.stop();assert_cleaned(self,lab,calls,confirmed=True)


@unittest.skipUnless(sys.platform=='win32','Requires real Windows kernel process/handle execution')
class WindowsStopPreworkerTest(unittest.TestCase):
    def child(self,pipes=False):
        process=subprocess.Popen([sys.executable,'-I','-S','-c','import time;time.sleep(40)'],
                                 stdin=subprocess.PIPE if pipes else None,stdout=subprocess.PIPE if pipes else None)
        def close():
            if process.poll() is None:process.kill()
            process.wait(timeout=5)
            for pipe in (process.stdin,process.stdout):
                if pipe:pipe.close()
        self.addCleanup(close);return process

    def test_destroyed_tk_controls_cannot_strand_real_children_queue_and_sampler(self):
        import tkinter as tk
        fixture=self.child();secondary=self.child();provider=self.child(pipes=True)
        native=NativeSession.__new__(NativeSession);native.fixture=fixture;native.process=provider
        native.cleanup_status=CleanupStatus();native.lock=threading.RLock();native.closed=False
        native._enqueue=lambda _:None
        now=datetime.now(timezone.utc)
        native.stream=SimpleNamespace(stop=lambda:None,clock=lambda:now,expires_at=now+timedelta(minutes=15),
                                      monotonic=lambda:0,deadline=900,stopped=False)
        native.reader=threading.Thread(target=provider.stdout.read,daemon=True)
        native.writer=threading.Thread(target=lambda:None,daemon=True);native.reader.start();native.writer.start()
        root=tk.Tk();root.title('Synthetic stop cleanup regression');button=tk.Button(root)
        status=tk.StringVar(master=root);root.destroy()
        with self.assertRaises(tk.TclError):button.config(state=tk.DISABLED)
        with tempfile.TemporaryDirectory() as tmp:
            sink=AsyncLabQueue(Path(tmp)/'synthetic.sqlite3');self.addCleanup(sink.close)
            data=empty_session();sampler=OwnedSampler(data);self.addCleanup(sampler.close)
            sampler.register('controller',current_controller=True);sampler.register('fixture',fixture)
            sampler.register('fixture_secondary',secondary);sampler.register('provider',provider)
            lab=AcceptanceLaboratory.__new__(AcceptanceLaboratory);lab.cleanup_status=CleanupStatus()
            lab.finished=False;lab.cleanup=None;lab.failed_binding=None;lab.tk=tk;lab.status_var=status
            lab.fixture=fixture;lab.secondary=secondary;lab.session=native;lab.sink=sink;lab.sampler=sampler
            lab.sampling_lock=threading.RLock();lab.sampling_closed=False
            lab.recorder=SimpleNamespace(data=data,observe=lambda _:None)
            for name in ('launch_btn','start_btn','pause_btn','stop_btn','persist_box','secondary_btn'):setattr(lab,name,button)
            lab.stop();lab.cleanup.join(timeout=20)
            self.assertFalse(lab.cleanup.is_alive());self.assertTrue(all(p.poll() is not None for p in (fixture,secondary,provider)))
            self.assertFalse(sink.worker.is_alive());self.assertTrue(sampler.cleanup_confirmed)
            self.assertFalse(native.reader.is_alive());self.assertFalse(native.writer.is_alive())
            self.assertIs(data['children_stopped'],False)
            self.assertGreater(lab.cleanup_snapshot()['errors']['controls'],0)
            print('REAL_DESTROYED_TK_STOP_CLEANED owned_children queue sampler confirmed_unavailable')
