from dataclasses import replace
from datetime import datetime,timedelta,timezone
from pathlib import Path
import json
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from observador.lab_queue import LabEventQueue,AsyncLabQueue
from observador.lab_faults import LabFaultPlan
from observador.diagnostics import DiagnosticRecorder
from test_storage_hardening import event


class QueueFaultTest(unittest.TestCase):
    def test_before_commit_faults_rollback_journal_and_after_commit_is_not_lost(self):
        for stage in ('before_transaction','after_insert','before_commit','after_commit'):
            for failure in ('busy','full','io'):
                with self.subTest(stage=stage,failure=failure),tempfile.TemporaryDirectory() as tmp:
                    path=Path(tmp)/'queue/db.sqlite3'
                    store=LabEventQueue(path,fault_plan=LabFaultPlan({stage:[failure]}))
                    source=event()
                    try:
                        count=store.append_batch([source])
                        committed=stage=='after_commit'
                        self.assertEqual(count,int(committed))
                        self.assertEqual(store.last_outcome['written'],int(committed))
                        self.assertEqual(store.last_outcome['rejected'],int(not committed))
                        self.assertEqual(store.conn.execute('PRAGMA integrity_check').fetchone()[0],'ok')
                        self.assertEqual(len(store.list_events()),int(committed))
                        if committed:
                            self.assertEqual(store.last_error,'post_commit')
                            self.assertFalse(store.insert(source))
                            self.assertEqual(store.last_outcome['duplicates'],1)
                    finally:store.close()
                    reopened=LabEventQueue(path)
                    try:self.assertEqual(len(reopened.list_events()),int(committed))
                    finally:reopened.close()

    def test_rollback_failure_is_uncertain_and_reopening_checks_integrity(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'queue/db.sqlite3'
            store=LabEventQueue(path,fault_plan=LabFaultPlan({'after_insert':['io'],'before_rollback':['io']}))
            self.assertFalse(store.insert(event()))
            self.assertEqual(store.last_outcome['uncertain'],1)
            self.assertFalse(store.usable)
            store.close()
            reopened=LabEventQueue(path)
            try:
                self.assertEqual(reopened.list_events(),[])
                self.assertEqual(reopened.conn.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            finally:reopened.close()

    def test_purge_commit_phases_and_preexisting_rows_have_separate_windows(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'queue/db.sqlite3'
            now=datetime.now(timezone.utc)
            store=LabEventQueue(path,clock=lambda:now)
            try:store.insert(replace(event(),timestamp_utc=now.isoformat()))
            finally:store.close()
            now+=timedelta(hours=2)
            sink=AsyncLabQueue(path,clock=lambda:now)
            sink.close()
            sample=DiagnosticRecorder().sample(writer=sink)['writer']
            self.assertEqual(sample['ledger']['written'],0)
            self.assertEqual(sample['storage']['rows_at_open'],1)
            self.assertEqual(sample['storage']['purged'],1)
            self.assertEqual(sample['row_balance'],'balanced')

    def test_conflicting_uuid_is_rejected_not_silently_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=LabEventQueue(Path(tmp)/'queue/db.sqlite3')
            source=event()
            try:
                self.assertTrue(store.insert(source))
                self.assertFalse(store.insert(replace(source,action='toggle')))
                self.assertEqual(store.last_error,'projection')
                self.assertEqual(store.list_events(),[source])
            finally:store.close()

    def test_async_failure_settles_inflight_and_rejects_pending_without_deadlock(self):
        gate=threading.Event()
        real=LabEventQueue
        def delayed(*args,**kwargs):
            gate.wait(2)
            return real(*args,**kwargs)
        with tempfile.TemporaryDirectory() as tmp,patch('observador.lab_queue.LabEventQueue',side_effect=delayed):
            sink=AsyncLabQueue(Path(tmp)/'queue/db.sqlite3',capacity=2,fault_plan=LabFaultPlan({'after_commit':['io']}))
            sink.submit([event()]);sink.submit([event()]);sink.submit([event()])
            sample=DiagnosticRecorder().sample(writer=sink)
            self.assertEqual(sample['writer']['ledger']['ingress_rejected'],1)
            gate.set();sink.close()
            sample=DiagnosticRecorder().sample(writer=sink)
            self.assertEqual(sample['writer']['ledger']['written'],1)
            self.assertEqual(sample['writer']['ledger']['write_rejected'],1)
            self.assertTrue(sample['writer']['shutdown'])
            self.assertFalse(sample['writer']['worker_alive'])

    def test_budget_observes_live_journal_and_purge_fault_rolls_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'queue/db.sqlite3'
            now=datetime.now(timezone.utc)
            store=LabEventQueue(path,clock=lambda:now)
            try:
                store.insert(replace(event(),timestamp_utc=now.isoformat()))
                self.assertGreater(store.budget.peak_observed,path.stat().st_size)
                self.assertLessEqual(store.budget.peak_observed,store.budget.limit)
                now+=timedelta(hours=2)
                store.fault_plan=LabFaultPlan({'purge_before_commit':['io']})
                with self.assertRaises(sqlite3.Error):store.purge()
                self.assertEqual(store.purged,0)
                self.assertEqual(len(store.list_events()),1)
                store.purge()
                self.assertEqual(store.purged,1)
                self.assertEqual(store.conn.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            finally:store.close()

    def test_snapshot_and_submission_do_not_wait_on_sqlite_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'queue/db.sqlite3'
            store=LabEventQueue(path);store.close()
            sink=AsyncLabQueue(path)
            deadline=time.monotonic()+2
            while sink.health=='starting' and time.monotonic()<deadline:time.sleep(.005)
            other=sqlite3.connect(path)
            other.execute('BEGIN EXCLUSIVE')
            started=time.monotonic()
            sink.submit([event()])
            for _ in range(20):DiagnosticRecorder().sample(writer=sink)
            self.assertLess(time.monotonic()-started,.5)
            sink.close();other.rollback();other.close()
            self.assertFalse(sink.worker.is_alive())
            self.assertEqual(sink.diagnostics_snapshot()['ledger']['write_rejected'],1)

    def test_shutdown_timeout_is_a_gap_and_does_not_deadlock_snapshots(self):
        release=threading.Event()
        real=LabEventQueue
        def stalled(*args,**kwargs):
            release.wait(5)
            return real(*args,**kwargs)
        with tempfile.TemporaryDirectory() as tmp,patch('observador.lab_queue.LabEventQueue',side_effect=stalled):
            sink=AsyncLabQueue(Path(tmp)/'queue/db.sqlite3')
            try:
                sink.submit([event()])
                sink.close()
                sample=DiagnosticRecorder().sample(writer=sink)
                self.assertEqual(sample['writer']['health'],'shutdown_timeout')
                self.assertIn('writer_shutdown_incomplete',sample['gaps'])
                self.assertTrue(sample['writer']['worker_alive'])
            finally:
                release.set();sink.worker.join(timeout=2)
            self.assertFalse(sink.worker.is_alive())
            self.assertEqual(DiagnosticRecorder().sample(writer=sink)['writer']['ledger']['written'],1)

    def test_abrupt_exit_after_and_before_commit_recovers_without_false_persistent_counters(self):
        for commit in (False,True):
            with tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'queue/db.sqlite3'
                script=('import sys,os;from observador.lab_queue import LabEventQueue;'
                        'from observador.sample import generate_sample;from datetime import datetime,timezone;'
                        'from dataclasses import replace;'
                        's=LabEventQueue(sys.argv[1]);e=replace(generate_sample(1)[0],timestamp_utc=datetime.now(timezone.utc).isoformat(),'
                        'device_id="laboratorio-sintetico",app="synthetic-app",event_type="ui_action",action="invoke",'
                        'target="button-0123456789abcdef",duration_ms=0,metadata={"category":"laboratory","control_role":"button"});'
                        + ('s.insert(e);' if commit else
                           'import json;s.conn.execute("BEGIN IMMEDIATE");s.conn.execute("INSERT INTO events VALUES (?,?,?,?,?,?)",'
                           '(e.event_id,e.timestamp_utc,e.device_id,e.session_id,e.event_type,json.dumps(e.to_dict(),sort_keys=True)));')
                        + 'os._exit(19)')
                result=subprocess.run([sys.executable,'-c',script,str(path)],capture_output=True,timeout=10)
                self.assertEqual(result.returncode,19)
                sink=AsyncLabQueue(path);sink.close()
                sample=DiagnosticRecorder().sample(writer=sink)
                self.assertEqual(sample['writer']['ledger']['written'],0)
                self.assertEqual(sample['writer']['storage']['rows_at_open'],int(commit))
                self.assertEqual(sample['writer']['storage']['rows_current'],int(commit))
