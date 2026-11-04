"""Synthetic retention model, crash recovery and anti-replay; no external data."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime,timedelta,timezone
import json
import os
from pathlib import Path
import random
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from observador.lab_faults import LabFaultPlan
from observador.offline_bridge import OfflineBridge,BridgeError,make_batch,canonical,EVENT_TTL_MS,RECEIPT_TTL_MS
from test_offline_bridge import source,events_for


class RetentionTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'inbox/db.sqlite3'
        self.now=datetime(2026,11,4,tzinfo=timezone.utc);self.mono=0
        self.p=source()

    def open(self):
        b=OfflineBridge(self.path,clock=lambda:self.now,monotonic=lambda:self.mono)
        self.addCleanup(b.close);return b

    def active(self,b):
        b.authorize(self.p);b.control('start');return b

    def batch(self,b,seq=1):return make_batch(b.ticket(self.p['instance']),events_for(self.p,(seq,)))

    def advance(self,seconds):self.now+=timedelta(seconds=seconds);self.mono+=seconds

    def test_exact_boundaries_payload_receipt_and_markers_separate(self):
        b=self.active(self.open());batch=self.batch(b);ack=b.ingest(batch)
        b.control('pause');self.advance(EVENT_TTL_MS/1000-.001)
        self.assertEqual(b.purge()['events'],0)
        self.advance(.001);self.assertEqual(b.purge(),dict(events=1,receipts=0))
        self.assertEqual(b.ingest(batch),ack)
        self.assertEqual(b.retention_snapshot()['counts']['event_markers'],1)
        self.advance((RECEIPT_TTL_MS-EVENT_TTL_MS)/1000)
        self.assertEqual(b.purge(),dict(events=0,receipts=1))
        with self.assertRaisesRegex(BridgeError,'^receipt_expired_or_unknown$'):b.ingest(batch)
        self.assertEqual(b.retention_snapshot()['counts']['batch_markers'],1)
        self.assertEqual(b.retention_snapshot()['counters']['receipt_unavailable'],1)

    def test_no_reuse_after_purge_even_with_fresh_epoch_and_sequences(self):
        b=self.active(self.open());old=self.batch(b);b.ingest(old)
        self.advance(86401);b.purge();b.close()
        b=self.active(self.open());fresh=self.batch(b,2)
        for change in ('batch_id','event_id','source_sequence','batch_sequence'):
            candidate=deepcopy(fresh)
            if change=='batch_id':candidate['batch_id']=old['batch_id']
            elif change=='event_id':candidate['events'][0]['event_id']=old['events'][0]['event_id']
            elif change=='source_sequence':candidate['events'][0]['metadata']['source_sequence']=1
            else:candidate['batch_sequence']=1
            with self.subTest(change=change),self.assertRaises(BridgeError):b.ingest(candidate)
            self.assertEqual(b.conn.execute('SELECT COUNT(*) FROM events').fetchone()[0],0)
        self.assertEqual(b.ingest(fresh)['written_count'],1)

    def test_backward_clock_freezes_retention_and_rejects_admission_across_restart(self):
        b=self.active(self.open());batch=self.batch(b);ack=b.ingest(batch)
        self.advance(1800);b.purge();self.advance(-3600)
        self.assertEqual(b.purge()['events'],0);self.assertEqual(b.state,'expired')
        self.assertEqual(b.ingest(batch),ack)
        b.close();b=self.open()
        self.assertEqual(b.state,'expired')
        b.authorize(self.p);self.assertEqual(b.ingest(batch),ack)
        with self.assertRaises(BridgeError):b.control('start')
        self.assertEqual(b.retention_snapshot()['counts']['events'],1)

    def test_monotonic_expiry_does_not_imply_payload_purge(self):
        b=self.active(self.open());batch=self.batch(b);ack=b.ingest(batch)
        self.mono=901
        with self.assertRaises(BridgeError):b.ticket(self.p['instance'])
        self.assertEqual(b.ingest(batch),ack)
        self.assertEqual(b.purge()['events'],0)

    def test_capacity_never_evicts_markers_and_retry_survives_budget_full(self):
        b=self.active(self.open());batch=self.batch(b);ack=b.ingest(batch)
        with patch('observador.offline_bridge.MAX_EVENT_MARKERS',1):
            with self.assertRaisesRegex(BridgeError,'capacity'):b.ingest(self.batch(b,2))
        self.assertEqual(b.retention_snapshot()['counts']['event_markers'],1)
        # Read-only ACK recovery needs neither new storage nor a purge transaction.
        with patch.object(b.budget,'check',side_effect=OSError('synthetic')):
            self.assertEqual(b.ingest(batch),ack)
            with self.assertRaises(BridgeError):b.ingest(self.batch(b,2))
        self.assertEqual(b.state,'failed')
        self.assertEqual(b.retention_snapshot()['counts']['batch_markers'],1)

    def test_purge_faults_commit_boundary_and_recovery(self):
        for stage in ('purge_before_commit','purge_after_commit'):
            with self.subTest(stage=stage):
                path=Path(self.tmp.name)/stage/'db.sqlite3'
                b=OfflineBridge(path,clock=lambda:self.now);b.authorize(self.p);b.control('start')
                batch=self.batch(b);b.ingest(batch);self.advance(3601)
                b.fault_plan=LabFaultPlan({stage:['io']})
                with self.assertRaises(BridgeError):b.purge()
                self.assertEqual(b.state,'failed')
                self.assertEqual(b.conn.execute('SELECT COUNT(*) FROM events').fetchone()[0],int(stage=='purge_before_commit'))
                self.assertEqual(b.conn.execute('SELECT COUNT(*) FROM event_markers').fetchone()[0],1)
                b.close();b=OfflineBridge(path,clock=lambda:self.now)
                try:
                    b.authorize(self.p);self.assertEqual(b.ingest(batch)['written_count'],1)
                    self.assertEqual(b.conn.execute('PRAGMA integrity_check').fetchone()[0],'ok')
                finally:b.close()

    def test_post_commit_error_recovers_same_ack_without_reinsertion(self):
        b=self.active(self.open());batch=self.batch(b)
        b.fault_plan=LabFaultPlan({'after_commit':['io']})
        with self.assertRaises(BridgeError):b.ingest(batch)
        self.assertEqual(b.state,'failed')
        stored=json.loads(b.conn.execute('SELECT ack_json FROM receipts').fetchone()[0])
        self.assertEqual(b.ingest(batch),stored)
        self.assertEqual(b.retention_snapshot()['counts']['events'],1)
        self.assertEqual(b.retention_snapshot()['counts']['event_markers'],1)

    def test_busy_full_io_precommit_are_atomic(self):
        b=self.active(self.open())
        for stage in ('before_transaction','after_insert','before_commit'):
            for fault in ('busy','full','io'):
                b.state='active';b.fault_plan=LabFaultPlan({stage:[fault]})
                with self.subTest(stage=stage,fault=fault),self.assertRaises(BridgeError):b.ingest(self.batch(b))
                self.assertEqual(b.retention_snapshot()['counts']['events'],0)
                self.assertEqual(b.retention_snapshot()['counts']['batch_markers'],0)
                self.assertEqual(b.conn.execute('SELECT last_batch,last_sequence FROM sources').fetchone(),(0,0))

    def test_new_owner_fences_old_maintenance_and_history(self):
        old=self.active(self.open());batch=self.batch(old);old.ingest(batch)
        new=self.open();new.authorize(self.p)
        with self.assertRaises(BridgeError):old.purge()
        with self.assertRaises(BridgeError):old.ingest(batch)
        self.assertEqual(new.ingest(batch)['written_count'],1)

    def test_real_sqlite_lock_blocks_purge_without_deleting_protection(self):
        b=self.active(self.open());b.ingest(self.batch(b))
        other=sqlite3.connect(self.path,timeout=.05)
        try:
            other.execute('BEGIN EXCLUSIVE')
            with self.assertRaises(BridgeError):b.purge()
        finally:other.rollback();other.close()
        self.assertEqual(b.retention_snapshot()['counts']['event_markers'],1)

    def test_seeded_model_replay_conflict_and_purge_invariants(self):
        b=self.active(self.open());rng=random.Random(1401);committed=[]
        # 100 different random operations, not a claim of exhaustive property proof.
        for _ in range(100):
            op=rng.choice(('new','retry','conflict','purge','out_of_order'))
            if op=='new' or not committed:
                seq=len(committed)+1;batch=self.batch(b,seq);ack=b.ingest(batch);committed.append((batch,ack))
            elif op in ('retry','conflict'):
                batch,ack=rng.choice(committed);batch=deepcopy(batch)
                if op=='conflict':
                    batch['events'][0]['action']='review'
                    with self.assertRaises(BridgeError):b.ingest(batch)
                else:self.assertEqual(b.ingest(batch),ack)
            elif op=='out_of_order':
                batch=self.batch(b,len(committed)+1);batch['batch_sequence']+=1
                with self.assertRaises(BridgeError):b.ingest(batch)
            else:b.purge()
            snap=b.retention_snapshot()['counts']
            self.assertEqual(snap['events'],len(committed));self.assertEqual(snap['event_markers'],len(committed))
            self.assertEqual(snap['batch_markers'],len(committed))
        self.advance(86401);b.purge()
        for batch,_ in committed:
            with self.assertRaisesRegex(BridgeError,'receipt_expired_or_unknown'):b.ingest(batch)
        self.assertEqual(b.retention_snapshot()['counts']['events'],0)
        self.assertEqual(b.retention_snapshot()['counts']['event_markers'],len(committed))

    def test_v1_migration_grants_window_and_preserves_ack(self):
        b=self.active(self.open());batch=self.batch(b);ack=b.ingest(batch)
        # Reconstruct exact legacy schema in place for an isolated, synthetic fixture.
        with b.conn:
            b.conn.execute('ALTER TABLE events DROP COLUMN committed_ms')
            b.conn.execute('ALTER TABLE receipts DROP COLUMN committed_ms')
            b.conn.execute('DROP TABLE batch_markers');b.conn.execute('DROP TABLE event_markers')
            b.conn.execute('DELETE FROM meta WHERE key="retention_ms"');b.conn.execute('PRAGMA user_version=1')
        b.close();self.advance(86401)
        b=self.open();b.authorize(self.p)
        self.assertEqual(b.ingest(batch),ack)
        self.assertEqual(b.conn.execute('PRAGMA user_version').fetchone()[0],2)
        self.assertEqual(b.retention_snapshot()['counts']['events'],1)

    def test_actual_page_limit_rollback_preserves_receipts(self):
        b=self.active(self.open());batch=self.batch(b);ack=b.ingest(batch)
        # Exhaust SQLite's page budget inside this disposable DB, never the filesystem.
        pages=b.conn.execute('PRAGMA page_count').fetchone()[0]
        b.conn.execute('PRAGMA max_page_count='+str(pages))
        with self.assertRaises(sqlite3.Error):
            with b.conn:b.conn.execute('CREATE TABLE synthetic_fill AS SELECT zeroblob(1000000) AS value')
        self.assertEqual(b.ingest(batch),ack)
        self.assertEqual(b.conn.execute('PRAGMA integrity_check').fetchone()[0],'ok')

    def test_real_process_kill_before_after_ingest_and_purge_commit(self):
        script='''
import json,os,sys
from pathlib import Path
from datetime import datetime,timezone
from observador.offline_bridge import OfflineBridge,make_batch
from test_offline_bridge import source,events_for
root=Path(sys.argv[1]);stage=sys.argv[2];now=datetime(2026,11,4,tzinfo=timezone.utc)
b=OfflineBridge(root/'inbox/db.sqlite3',clock=lambda:now)
p=source();b.authorize(p);b.control('start');batch=make_batch(b.ticket(p['instance']),events_for(p))
(root/'batch.json').write_text(json.dumps(batch))
def hit(s):
    if s==stage:os._exit(73)
if stage.startswith('purge'):
    b.ingest(batch)
    from datetime import timedelta
    b.clock=lambda:now+timedelta(seconds=3601)
    b._hit=hit;b.purge()
else:
    b._hit=hit;b.ingest(batch)
raise RuntimeError('crash_not_reached')
'''
        for stage in ('before_commit','after_commit','purge_before_commit','purge_after_commit'):
            root=Path(self.tmp.name)/stage;root.mkdir()
            env=dict(os.environ);env['PYTHONPATH']=os.pathsep.join(str(Path(p).resolve()) for p in ('src','tests'))
            result=subprocess.run([sys.executable,'-c',script,str(root),stage],env=env,capture_output=True,timeout=15)
            self.assertEqual(result.returncode,73,result.stderr.decode(errors='replace'))
            batch=json.loads((root/'batch.json').read_text())
            # Inspect recovered SQLite BEFORE constructor retention changes observable rows.
            raw=sqlite3.connect(root/'inbox/db.sqlite3')
            try:
                self.assertEqual(raw.execute('PRAGMA integrity_check').fetchone()[0],'ok')
                expected_events=0 if stage in ('before_commit','purge_after_commit') else 2
                self.assertEqual(raw.execute('SELECT COUNT(*) FROM events').fetchone()[0],expected_events)
                self.assertEqual(raw.execute('SELECT COUNT(*) FROM receipts').fetchone()[0],int(stage!='before_commit'))
            finally:raw.close()
            b=OfflineBridge(root/'inbox/db.sqlite3',clock=lambda:self.now+timedelta(seconds=3601))
            try:
                b.authorize(batch['source'])
                self.assertEqual(b.conn.execute('PRAGMA integrity_check').fetchone()[0],'ok')
                self.assertEqual(b.retention_snapshot()['counts']['batch_markers'],int(stage!='before_commit'))
                if stage!='before_commit':self.assertEqual(b.ingest(batch)['written_count'],2)
                else:
                    with self.assertRaises(BridgeError):b.ingest(batch)  # Old epoch, no fabricated ACK.
            finally:b.close()

    def test_v1_global_id_collision_rolls_back_migration_without_erasing_history(self):
        b=self.active(self.open());batch=self.batch(b);b.ingest(batch)
        with b.conn:
            b.conn.execute('ALTER TABLE events DROP COLUMN committed_ms')
            b.conn.execute('ALTER TABLE receipts DROP COLUMN committed_ms')
            b.conn.execute('DROP TABLE batch_markers');b.conn.execute('DROP TABLE event_markers')
            b.conn.execute('DELETE FROM meta WHERE key="retention_ms"');b.conn.execute('PRAGMA user_version=1')
            b.conn.execute('INSERT INTO events SELECT ?,event_id,source_sequence,payload_json FROM events',('synthetic_other_source',))
        b.close()
        with self.assertRaises(BridgeError):self.open()
        conn=sqlite3.connect(self.path)
        try:
            self.assertEqual(conn.execute('PRAGMA user_version').fetchone()[0],1)
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM events').fetchone()[0],2)
            self.assertNotIn('committed_ms',{r[1] for r in conn.execute('PRAGMA table_info(events)')})
            self.assertEqual(conn.execute('PRAGMA integrity_check').fetchone()[0],'ok')
        finally:conn.close()

    def test_failed_rollback_cannot_return_uncommitted_receipt(self):
        for stage in ('before_rollback','after_rollback'):
            path=Path(self.tmp.name)/stage/'db.sqlite3'
            b=OfflineBridge(path,clock=lambda:self.now);b.authorize(self.p);b.control('start')
            batch=self.batch(b)
            b.fault_plan=LabFaultPlan({'before_commit':['io'],stage:['io']})
            with self.assertRaises(BridgeError):b.ingest(batch)
            self.assertFalse(b.usable)
            self.assertTrue(b.retention_snapshot()['reopen_required'])
            self.assertIsNone(b.retention_snapshot()['counts']['receipts'])
            with self.assertRaisesRegex(BridgeError,'^bridge_reopen_required$'):b.ingest(batch)
            b.close();b=OfflineBridge(path,clock=lambda:self.now)
            try:
                b.authorize(self.p)
                self.assertEqual(b.retention_snapshot()['counts']['receipts'],0)
                self.assertEqual(b.conn.execute('PRAGMA integrity_check').fetchone()[0],'ok')
                with self.assertRaises(BridgeError):b.ingest(batch)
            finally:b.close()

    def test_commit_return_uncertain_requires_reopen_even_when_transaction_closed(self):
        b=self.active(self.open());batch=self.batch(b)
        class AmbiguousCommit:
            def __init__(self,conn):self.conn=conn
            def __getattr__(self,key):return getattr(self.conn,key)
            def commit(self):
                self.conn.commit()
                raise OSError('synthetic_commit_return_lost')
        def hit(stage):
            if stage=='before_commit':b.conn=AmbiguousCommit(b.conn)
        b._hit=hit
        with self.assertRaises(BridgeError):b.ingest(batch)
        self.assertFalse(b.usable)
        with self.assertRaisesRegex(BridgeError,'^bridge_reopen_required$'):b.ingest(batch)
        b.close();b=self.open();b.authorize(self.p)
        self.assertEqual(b.ingest(batch)['written_count'],1)
        self.assertEqual(b.retention_snapshot()['counts']['events'],1)
        self.assertEqual(b.conn.execute('PRAGMA integrity_check').fetchone()[0],'ok')

    def test_truncated_file_eof_never_admits_partial_batch(self):
        from observador.offline_bridge import read_batch
        b=self.active(self.open());payload=canonical(self.batch(b)).encode()
        path=Path(self.tmp.name)/'partial.json'
        for end in (0,1,len(payload)//2,len(payload)-1):
            path.write_bytes(payload[:end])
            with self.assertRaisesRegex(BridgeError,'^bridge_batch_rejected$'):read_batch(path)
        self.assertEqual(b.retention_snapshot()['counts']['batch_markers'],0)
