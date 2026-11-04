from copy import deepcopy
from dataclasses import replace
from datetime import datetime,timedelta,timezone
from pathlib import Path
import json
import tempfile
import unittest
from uuid import uuid4

from observador.offline_bridge import OfflineBridge,BridgeError,make_batch,read_batch,canonical,validate_batch
from test_storage_hardening import event


def source(kind='web',slot=1):
    return dict(kind=kind,version=1,instance=str(uuid4()),origin='http://127.0.0.1:8765' if kind=='web' else 'owned_synthetic_process',
                tab_slot=slot if kind=='web' else None)


def events_for(provenance,sequences=(1,2)):
    result=[]
    for sequence in sequences:
        base=event()
        if provenance['kind']=='web':base=replace(base,app='synthetic-web',event_type='browser_action',action='save',metadata={'category':'synthetic','control_role':'button'})
        result.append(replace(base,session_id=provenance['instance'],metadata={**base.metadata,'source_sequence':sequence}))
    return result


class OfflineBridgeTest(unittest.TestCase):
    def test_disabled_binding_ack_idempotence_and_reopen_are_durable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'inbox/bridge.sqlite3'
            bridge=OfflineBridge(path)
            provenance=source()
            try:
                self.assertEqual(bridge.state,'disabled')
                bridge.authorize(provenance)
                with self.assertRaises(BridgeError):bridge.ticket(provenance['instance'])
                bridge.control('start')
                batch=make_batch(bridge.ticket(provenance['instance']),events_for(provenance))
                ack=bridge.ingest(batch)
                self.assertEqual(bridge.ingest(batch),ack)
                self.assertEqual(ack['written_count'],2)
                bridge.control('pause')
                self.assertEqual(bridge.ingest(batch),ack)  # Historical ACK, not new admission.
            finally:bridge.close()
            bridge=OfflineBridge(path)
            try:
                self.assertEqual(bridge.state,'disabled')
                bridge.authorize(provenance)
                self.assertEqual(bridge.ingest(batch),ack)
                self.assertEqual(len(bridge.source_events()[0]['events']),2)
                self.assertEqual(bridge.conn.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            finally:bridge.close()

    def test_pauses_generations_expiry_and_sequence_gaps_are_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            now=[datetime.now(timezone.utc)];elapsed=[0.0]
            bridge=OfflineBridge(Path(tmp)/'inbox/db.sqlite3',clock=lambda:now[0],monotonic=lambda:elapsed[0])
            p=source()
            try:
                bridge.authorize(p);bridge.control('start')
                old=make_batch(bridge.ticket(p['instance']),events_for(p,(1,)))
                bridge.control('pause')
                with self.assertRaises(BridgeError):bridge.ingest(old)
                ack=bridge.control('resume')
                self.assertEqual(ack['scope'],'bridge_admission_only_producers_not_confirmed')
                with self.assertRaises(BridgeError):bridge.ingest(old)
                fresh=make_batch(bridge.ticket(p['instance']),events_for(p,(3,5)))
                self.assertEqual(bridge.ingest(fresh)['source_gap_count'],3)
                elapsed[0]=901;now[0]-=timedelta(seconds=5)
                with self.assertRaises(BridgeError):bridge.ticket(p['instance'])
                self.assertEqual(bridge.state,'expired')
            finally:bridge.close()

    def test_denied_sources_tab_origin_replay_conflict_and_extra_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            bridge=OfflineBridge(Path(tmp)/'inbox/db.sqlite3');p=source()
            try:
                bridge.authorize(p);bridge.control('start')
                batch=make_batch(bridge.ticket(p['instance']),events_for(p,(1,)))
                for key,value in [('origin','https://example.com'),('tab_slot',2),('instance',str(uuid4()))]:
                    bad=deepcopy(batch);bad['source'][key]=value
                    with self.assertRaises(BridgeError):bridge.ingest(bad)
                bad=deepcopy(batch);bad['events'][0]['password']='SECRET'
                with self.assertRaisesRegex(BridgeError,'^bridge_batch_rejected$'):bridge.ingest(bad)
                bad=deepcopy(batch);bad['batch_sequence']=2
                with self.assertRaises(BridgeError):bridge.ingest(bad)
                bridge.ingest(batch)
                bad=deepcopy(batch);bad['events'][0]['action']='review'
                with self.assertRaises(BridgeError):bridge.ingest(bad)
                replay=make_batch(bridge.ticket(p['instance']),events_for(p,(1,)))
                with self.assertRaises(BridgeError):bridge.ingest(replay)
                self.assertEqual(len(bridge.source_events()[0]['events']),1)
            finally:bridge.close()

    def test_two_sources_keep_separate_orders_and_no_global_causality(self):
        with tempfile.TemporaryDirectory() as tmp:
            bridge=OfflineBridge(Path(tmp)/'inbox/db.sqlite3')
            web,windows=source(),source('windows')
            try:
                bridge.authorize(web);bridge.authorize(windows);bridge.control('start')
                for p in (windows,web):
                    records=events_for(p)
                    records[0]=replace(records[0],timestamp_utc=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat())
                    bridge.ingest(make_batch(bridge.ticket(p['instance']),records))
                sources=bridge.source_events()
                self.assertEqual(len(sources),2)
                for item in sources:
                    self.assertEqual([e.metadata['source_sequence'] for e in item['events']],[1,2])
                    self.assertIn('no_global_order',item['gaps'])
            finally:bridge.close()

    def test_transaction_failure_never_acknowledges_partial_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'inbox/db.sqlite3'
            bridge=OfflineBridge(path);p=source()
            bridge.authorize(p);bridge.control('start')
            batch=make_batch(bridge.ticket(p['instance']),events_for(p))
            bridge.conn.execute('CREATE TRIGGER synthetic_fail BEFORE INSERT ON receipts BEGIN SELECT RAISE(ABORT,"synthetic"); END')
            with self.assertRaises(BridgeError):bridge.ingest(batch)
            self.assertEqual(bridge.state,'failed')
            self.assertEqual(bridge.conn.execute('SELECT COUNT(*) FROM events').fetchone()[0],0)
            self.assertEqual(bridge.conn.execute('SELECT COUNT(*) FROM receipts').fetchone()[0],0)
            bridge.conn.execute('DROP TRIGGER synthetic_fail');bridge.close()
            bridge=OfflineBridge(path)
            try:
                bridge.authorize(p);bridge.control('start')
                self.assertEqual(bridge.ingest(make_batch(bridge.ticket(p['instance']),events_for(p)))['written_count'],2)
            finally:bridge.close()

    def test_reader_rejects_duplicate_keys_and_non_bridge_databases(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'bad.json'
            path.write_text('{"a":1,"a":2}')
            with self.assertRaises(BridgeError):read_batch(path)
            path.write_text(' '*300000)
            with self.assertRaises(BridgeError):read_batch(path)
            from observador.lab_queue import LabEventQueue
            database=Path(tmp)/'legacy/db.sqlite3'
            store=LabEventQueue(database);store.close()
            with self.assertRaises(BridgeError):OfflineBridge(database)

    def test_new_owner_revokes_old_uncommitted_tickets(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'inbox/db.sqlite3';p=source()
            old=OfflineBridge(path);old.authorize(p);old.control('start')
            batch=make_batch(old.ticket(p['instance']),events_for(p))
            new=OfflineBridge(path)
            try:
                new.authorize(p);new.control('start')
                with self.assertRaises(BridgeError):old.ingest(batch)
                with self.assertRaises(BridgeError):old.ticket(p['instance'])
                self.assertEqual(new.ingest(make_batch(new.ticket(p['instance']),events_for(p)))['written_count'],2)
            finally:old.close();new.close()
