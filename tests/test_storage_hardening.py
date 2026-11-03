from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from observador.events import Event
from observador.lab_queue import LabEventQueue, AsyncLabQueue
from observador.private_directory import WindowsSecurity
from observador.dpapi_archive import protect, unprotect, write_archive, read_archive


def event():
    return Event(1, str(uuid4()), datetime.now(timezone.utc).isoformat(), 'laboratorio-sintetico', str(uuid4()),
                 'synthetic-app', 'ui_action', 'invoke', 'button-0123456789abcdef',
                 metadata={'control_role': 'button', 'category': 'laboratory'})


class StorageHardeningTest(unittest.TestCase):
    def test_auxiliary_budget_rejects_before_mutation_and_recovers(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'queue/events.sqlite3'
            store = LabEventQueue(path, max_db_bytes=65536, max_total_bytes=300000)
            try:
                extra = path.parent/'auxiliary.bin'
                extra.write_bytes(b'x'*100000)
                self.assertFalse(store.insert(event()))
                self.assertEqual(store.rejected, 1)
                self.assertEqual(store.health, 'storage_unavailable')
                self.assertEqual(store.list_events(), [])
                extra.unlink()
                self.assertTrue(store.insert(event()))
                self.assertLessEqual(store.budget.usage(), store.budget.limit)
            finally:
                store.close()

    def test_disk_full_readonly_and_shutdown_loss_are_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'queue/events.sqlite3'
            store = LabEventQueue(path)
            try:
                with patch('observador.storage_budget.shutil.disk_usage', return_value=type('Space', (), {'free': 0})()):
                    self.assertFalse(store.insert(event()))
                self.assertEqual(store.rejected, 1)
                store.conn.execute('PRAGMA query_only=ON')
                self.assertFalse(store.insert(event()))
                self.assertEqual(store.rejected, 2)
                self.assertEqual(store.conn.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            finally:
                store.close()
            sink = AsyncLabQueue(path)
            sink.close()
            sink.submit([event(), event()])
            self.assertEqual(sink.discarded, 2)

    def test_corruption_is_preserved_and_error_is_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'queue/events.sqlite3'
            path.parent.mkdir()
            payload = b'not a database - synthetic corruption'
            path.write_bytes(payload)
            sink = AsyncLabQueue(path)
            sink.submit([event()])
            sink.close()
            self.assertEqual(sink.discarded, 1)
            self.assertEqual(sink.health, 'storage_unavailable')
            self.assertEqual(path.read_bytes(), payload)

    def test_unexpected_exit_rolls_back_and_committed_data_survives(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'queue/events.sqlite3'
            store = LabEventQueue(path)
            original = event()
            store.insert(original)
            store.close()
            script = "import sqlite3,sys,os;c=sqlite3.connect(sys.argv[1]);c.execute('BEGIN IMMEDIATE');c.execute(\"DELETE FROM events\");os._exit(19)"
            process = subprocess.run([sys.executable, '-c', script, str(path)], timeout=10, capture_output=True)
            self.assertEqual(process.returncode, 19)
            store = LabEventQueue(path)
            try:
                self.assertEqual(store.list_events(), [original])
                self.assertEqual(store.conn.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
                self.assertTrue(store.insert(event()))
                self.assertFalse(path.with_name(path.name+'-journal').exists())
            finally:
                store.close()

    def test_links_are_rejected_without_modifying_destination(self):
        if sys.platform == 'win32':
            self.skipTest('Symlink creation requires optional Windows privilege; hardlink test covers Windows separately')
        with tempfile.TemporaryDirectory() as tmp:
            outside = Path(tmp)/'outside'
            outside.mkdir()
            alias = Path(tmp)/'alias'
            alias.symlink_to(outside, target_is_directory=True)
            with self.assertRaises((OSError, ValueError)):
                LabEventQueue(alias/'db.sqlite3')
            self.assertEqual(list(outside.iterdir()), [])

    def test_hardlinks_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'queue/events.sqlite3'
            path.parent.mkdir()
            original = Path(tmp)/'original'
            original.write_bytes(b'synthetic')
            os.link(original, path)
            with self.assertRaises(OSError):
                LabEventQueue(path)
            self.assertEqual(original.read_bytes(), b'synthetic')

    @unittest.skipUnless(sys.platform == 'win32', 'Windows native DACL/DPAPI requires Windows')
    def test_windows_acl_and_current_user_dpapi_real_roundtrip_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'queue/events.sqlite3'
            store = LabEventQueue(path)
            try:
                source = event()
                store.insert(source)
                api = WindowsSecurity()
                for target in (path.parent, path):
                    dacl = api.dacl(target)
                    self.assertTrue(dacl.startswith('D:P'))
                    trustees = api.trustees(target)
                    self.assertEqual({entry[0] for entry in trustees}, {api.user_sid(), 'S-1-5-18'})
                    self.assertTrue(all(entry[2] == 0x1f01ff for entry in trustees))
                    self.assertIn(';;;SY)', dacl)
                    self.assertEqual(dacl.count('(A;'), 2)
                    self.assertNotIn(';;;BU)', dacl)
                    self.assertNotIn(';;;WD)', dacl)
                archive = Path(tmp)/'archive/synthetic.dpapi'
                self.assertEqual(write_archive(store, archive), 1)
                self.assertEqual(read_archive(archive), [source])
                self.assertNotIn(b'button-0123456789abcdef', archive.read_bytes())
                envelope = protect(b'synthetic payload')
                self.assertEqual(unprotect(envelope), b'synthetic payload')
                damaged = bytearray(envelope)
                damaged[-10] ^= 0xff
                with self.assertRaises(OSError):
                    unprotect(bytes(damaged))
                with self.assertRaises(FileExistsError):
                    write_archive(store, archive)
            finally:
                store.close()
