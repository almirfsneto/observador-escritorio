from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import sqlite3
import threading
import unittest
from unittest.mock import patch
from uuid import uuid4

from observador.events import Event
from observador.lab_queue import AsyncLabQueue, LabEventQueue


class LabQueueTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name) / 'lab/events.sqlite3'
        self.now = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)
        self.session = str(uuid4())

    def tearDown(self):
        self.temporary.cleanup()

    def event(self):
        return Event(1, str(uuid4()), self.now.isoformat(), 'laboratorio-sintetico', self.session,
                     'synthetic-app', 'ui_action', 'invoke', 'button-0123456789abcdef',
                     metadata={'control_role': 'button', 'category': 'laboratory'})

    def open(self, **options):
        return LabEventQueue(self.path, clock=lambda: self.now, **options)

    def test_idempotence_restart_and_retention(self):
        event = self.event()
        store = self.open()
        try:
            self.assertTrue(store.insert(event))
            self.assertFalse(store.insert(event))
        finally:
            store.close()
        self.now += timedelta(hours=2)
        store = self.open()
        try:
            self.assertEqual(store.list_events(), [])
            self.assertEqual(store.purged, 1)
            self.assertTrue(store.insert(self.event()))
        finally:
            store.close()

    def test_row_limit_is_deterministic(self):
        store = self.open(max_events=3)
        try:
            for _ in range(7):
                self.now += timedelta(milliseconds=1)
                store.insert(self.event())
            self.assertEqual(len(store.list_events()), 3)
            self.assertEqual(store.purged, 4)
        finally:
            store.close()

    def test_database_quota_rolls_back_cleanly_and_can_recover_after_purge(self):
        store = self.open(max_db_bytes=65536, max_events=100000)
        try:
            for _ in range(50):
                store.append_batch([self.event() for _ in range(25)])
                if store.health == 'quota_full':
                    break
            self.assertEqual(store.health, 'quota_full')
            self.assertLessEqual(self.path.stat().st_size, 65536)
            self.assertEqual(store.conn.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            self.now += timedelta(hours=2)
            self.assertTrue(store.insert(self.event()))
            self.assertEqual(store.health, 'ready')
        finally:
            store.close()

    def test_rejects_raw_or_expired_events_before_writing(self):
        store = self.open()
        try:
            for event in [replace(self.event(), target='client-name'),
                          replace(self.event(), device_id='real-person'),
                          replace(self.event(), app='Chrome'),
                          replace(self.event(), timestamp_utc=(self.now - timedelta(hours=2)).isoformat())]:
                with self.assertRaises(ValueError):
                    store.insert(event)
            self.assertEqual(store.list_events(), [])
        finally:
            store.close()

    def test_async_flush_and_close_are_bounded_and_durable(self):
        sink = AsyncLabQueue(self.path, clock=lambda: self.now)
        sink.submit([self.event() for _ in range(30)])
        sink.close()
        sink.close()
        self.assertFalse(sink.worker.is_alive())
        self.assertEqual(sink.written, 30)
        store = self.open()
        try:
            self.assertEqual(len(store.list_events()), 30)
        finally:
            store.close()

    def test_async_rejects_unbounded_batches(self):
        sink = AsyncLabQueue(self.path, clock=lambda: self.now)
        sink.submit([self.event() for _ in range(101)])
        sink.close()
        self.assertEqual(sink.discarded, 101)
        self.assertEqual(sink.written, 0)

    def test_existing_oversized_database_is_not_silently_modified(self):
        self.path.parent.mkdir()
        self.path.write_bytes(b'x' * 65537)
        with self.assertRaises(ValueError):
            self.open(max_db_bytes=65536)
        self.assertEqual(self.path.stat().st_size, 65537)

    def test_locked_database_rejects_without_raw_error_and_recovers(self):
        store = self.open()
        other = sqlite3.connect(self.path)
        try:
            other.execute('BEGIN EXCLUSIVE')
            self.assertFalse(store.insert(self.event()))
            self.assertEqual(store.health, 'storage_unavailable')
            self.assertEqual(store.rejected, 1)
            other.rollback()
            self.assertTrue(store.insert(self.event()))
        finally:
            other.close()
            store.close()

    def test_async_buffer_backpressure_is_counted(self):
        release = threading.Event()
        real_store = LabEventQueue
        def delayed(*args, **options):
            release.wait(timeout=2)
            return real_store(*args, **options)
        with patch('observador.lab_queue.LabEventQueue', side_effect=delayed):
            sink = AsyncLabQueue(self.path, capacity=1, clock=lambda: self.now)
            sink.submit([self.event()])
            sink.submit([self.event()])
            self.assertEqual(sink.discarded, 1)
            release.set()
            sink.close()
        self.assertEqual(sink.written, 1)

    def test_async_invalid_projection_discards_pending_batches_and_closes(self):
        release = threading.Event()
        real_store = LabEventQueue
        def delayed(*args, **options):
            release.wait(timeout=2)
            return real_store(*args, **options)
        with patch('observador.lab_queue.LabEventQueue', side_effect=delayed):
            sink = AsyncLabQueue(self.path, clock=lambda: self.now)
            sink.submit([replace(self.event(), device_id='unapproved-device')])
            sink.submit([self.event()])
            release.set()
            sink.close()
        self.assertEqual(sink.health, 'storage_unavailable')
        self.assertEqual(sink.discarded, 2)
        self.assertFalse(sink.worker.is_alive())
        self.assertTrue(sink.pending.empty())
        store = self.open()
        try:
            self.assertEqual(store.list_events(), [])
        finally:
            store.close()
