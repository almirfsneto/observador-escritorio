"""Actual configured lifetime caps; no patched thresholds, DB reset or real-time TTL claim."""
from datetime import datetime,timedelta,timezone
from pathlib import Path
import tempfile
import unittest

from observador.offline_bridge import OfflineBridge,BridgeError,make_batch
from test_offline_bridge import source,events_for


class LifetimeCapacityTest(unittest.TestCase):
    def saturate(self,count,events_per_batch,expected_table,expected_count):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'inbox/db.sqlite3';now=[datetime(2026,11,4,tzinfo=timezone.utc)];p=source('windows')
            first=None
            b=None
            try:
                for index in range(count):
                    if b is None:
                        b=OfflineBridge(path,clock=lambda:now[0]);b.authorize(p);b.control('start')
                    records=events_for(p,range(index*events_per_batch+1,(index+1)*events_per_batch+1))
                    batch=make_batch(b.ticket(p['instance']),records);b.ingest(batch)
                    if first is None:first=batch
                    # Normal configured receipt cap allows128 batches per session.
                    # Reopen at that boundary; event-size stress purges each100-event batch.
                    session_batches=128 if events_per_batch==1 else 1
                    if (index+1)%session_batches==0:
                        b.close();b=None;now[0]+=timedelta(seconds=86401)
            finally:
                if b is not None:b.close()
            b=OfflineBridge(path,clock=lambda:now[0])
            try:
                b.authorize(p);b.control('start');snapshot=b.retention_snapshot()
                self.assertEqual(snapshot['counts'][expected_table],expected_count)
                self.assertEqual(snapshot['counts']['events'],0);self.assertEqual(snapshot['counts']['receipts'],0)
                with self.assertRaisesRegex(BridgeError,'receipt_expired_or_unknown'):b.ingest(first)
                fresh=make_batch(b.ticket(p['instance']),events_for(p,(count*events_per_batch+1,)))
                with self.assertRaisesRegex(BridgeError,'capacity_reached_markers_preserved'):b.ingest(fresh)
                self.assertEqual(b.retention_snapshot()['counters']['capacity_rejected'],1)
                b.purge();self.assertEqual(b.retention_snapshot()['counts'][expected_table],expected_count)
                self.assertEqual(b.conn.execute('PRAGMA integrity_check').fetchone()[0],'ok')
                print('SYNTHETIC_LIFETIME_CAP_VERIFIED',dict(table=expected_table,limit=expected_count,
                      expired_payloads=0,expired_receipts=0,markers_preserved=True,clock_injected=True,physical_quota=False))
            finally:b.close()
            b=OfflineBridge(path,clock=lambda:now[0])
            try:
                b.authorize(p);b.control('start')
                self.assertEqual(b.retention_snapshot()['counts'][expected_table],expected_count)
                with self.assertRaises(BridgeError):b.ingest(make_batch(b.ticket(p['instance']),events_for(p,(count*events_per_batch+1,))))
            finally:b.close()

    def test_actual_1024_batch_markers_remain_saturated_after_ttl_and_restart(self):
        self.saturate(1024,1,'batch_markers',1024)

    def test_actual_10000_event_markers_remain_saturated_after_ttl_and_restart(self):
        self.saturate(100,100,'event_markers',10000)

    def test_actual_32_sources_are_not_freed_by_purge_or_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'inbox/db.sqlite3';known=[]
            for _ in range(32):
                b=OfflineBridge(path)
                try:
                    p=source('windows');b.authorize(p);known.append(p)
                finally:b.close()
            for _ in range(2):
                b=OfflineBridge(path)
                try:
                    b.purge()
                    with self.assertRaisesRegex(BridgeError,'bridge_source_limit'):b.authorize(source('windows'))
                    self.assertEqual(b.retention_snapshot()['counts']['sources'],32)
                    b.authorize(known[0]) # Historical recovery is not a newly admitted source.
                    self.assertEqual(b.conn.execute('PRAGMA integrity_check').fetchone()[0],'ok')
                finally:b.close()
