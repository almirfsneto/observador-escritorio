"""Local synthetic-event queue: explicit opt-in, retention and bounded SQLite file.

The cap covers the main DB. Rollback journals and the filesystem require free-space
headroom; this is not a whole-disk quota or encryption facility.
"""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import queue
import re
import sqlite3
import threading

from .collector import utc
from .store import EventStore


class LabEventQueue(EventStore):
    def __init__(self, path, *, max_db_bytes=4 * 1024 * 1024, max_events=10000,
                 retention=timedelta(hours=1), clock=lambda: datetime.now(timezone.utc)):
        if max_db_bytes < 65536 or max_events < 1 or not timedelta(0) < retention <= timedelta(days=1):
            raise ValueError('invalid laboratory retention or quota')
        self.clock, self.retention, self.max_events = clock, retention, max_events
        self.rejected = self.purged = 0
        self.health = 'ready'
        path = Path(path)
        if path.is_symlink() or path.parent.is_symlink() or (path.exists() and path.stat().st_size > max_db_bytes):
            raise ValueError('existing queue exceeds quota or is a symlink')
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        super().__init__(path)
        try:
            path.chmod(0o600)
            self.conn.execute('PRAGMA busy_timeout=50')
            # Do not retain deleted values in SQLite free pages. Does not promise SSD erasure.
            self.conn.execute('PRAGMA secure_delete=ON')
            self.conn.execute('PRAGMA journal_mode=DELETE')
            page_size = self.conn.execute('PRAGMA page_size').fetchone()[0]
            pages = max_db_bytes // page_size
            actual = self.conn.execute(f'PRAGMA max_page_count={pages}').fetchone()[0]
            if actual > pages:
                raise ValueError('existing queue exceeds page quota')
            self.purge()
        except Exception:
            self.close()
            raise

    def purge(self):
        cutoff = (utc(self.clock()) - self.retention).isoformat()
        with self.conn:
            cursor = self.conn.execute('DELETE FROM events WHERE julianday(timestamp_utc) < julianday(?)', (cutoff,))
            self.purged += cursor.rowcount
            extra = max(0, self.conn.execute('SELECT COUNT(*) FROM events').fetchone()[0] - self.max_events)
            if extra:
                cursor = self.conn.execute('DELETE FROM events WHERE event_id IN '
                                           '(SELECT event_id FROM events ORDER BY timestamp_utc, event_id LIMIT ?)', (extra,))
                self.purged += cursor.rowcount
        return self.purged

    def append_batch(self, events):
        # Validate before opening a transaction. Never persist raw UIA dictionaries.
        now = utc(self.clock())
        rows = []
        for event in events:
            event.validate()
            when = datetime.fromisoformat(event.timestamp_utc.replace('Z', '+00:00'))
            if (event.app != 'synthetic-app' or event.metadata.get('category') != 'laboratory'
                    or event.device_id != 'laboratorio-sintetico' or event.duration_ms != 0
                    or not {'category', 'control_role'} <= set(event.metadata) <= {'category', 'control_role', 'source_sequence'}
                    or event.event_type not in {'window_focus', 'ui_action'}
                    or event.action not in {'focus', 'invoke', 'toggle'}
                    or (event.event_type == 'window_focus') != (event.action == 'focus')
                    or event.screenshot_ref is not None
                    or not now - self.retention <= when <= now + timedelta(milliseconds=100)):
                raise ValueError('queue accepts only current projected laboratory events')
            # The persistent projection must not accept arbitrary synthetic-looking content.
            if not re.fullmatch(r'(button|checkbox|combobox|edit|listitem|menuitem|tab|window|control)-[a-f0-9]{16}', event.target):
                raise ValueError('invalid synthetic control identity')
            rows.append((event.event_id, event.timestamp_utc, event.device_id, event.session_id,
                         event.event_type, json.dumps(event.to_dict(), sort_keys=True)))
        try:
            self.purge()
            before = self.conn.total_changes
            with self.conn:
                self.conn.executemany('INSERT OR IGNORE INTO events VALUES (?, ?, ?, ?, ?, ?)', rows)
                count = self.conn.execute('SELECT COUNT(*) FROM events').fetchone()[0]
                extra = max(0, count - self.max_events)
                if extra:
                    self.conn.execute('DELETE FROM events WHERE event_id IN '
                                      '(SELECT event_id FROM events ORDER BY timestamp_utc,event_id LIMIT ?)', (extra,))
            self.purged += extra
            self.health = 'ready'
            return self.conn.total_changes - before - extra
        except sqlite3.OperationalError as error:
            # SQLite may return BUSY or FULL; do not copy exception text into health logs.
            self.rejected += len(rows)
            code = getattr(error, 'sqlite_errorcode', None)
            self.health = 'quota_full' if code == sqlite3.SQLITE_FULL else 'storage_unavailable'
            return 0

    def insert(self, event):
        return self.append_batch([event]) == 1


class AsyncLabQueue:
    """Single SQLite owner thread. The UI only enqueues validated Event batches."""
    def __init__(self, path, *, capacity=16, **options):
        self.path, self.options = path, options
        self.pending = queue.Queue(maxsize=capacity)
        self.shutdown = threading.Event()
        self.discarded = 0
        self.written = 0
        self.purged = 0
        self.health = 'starting'
        self.lock = threading.RLock()
        self.worker = threading.Thread(target=self._run, daemon=True)
        self.worker.start()

    def submit(self, events):
        with self.lock:
            if not events or self.shutdown.is_set():
                return
            if len(events) > 100:
                self.discarded += len(events)
                return
            try:
                self.pending.put_nowait(tuple(events))
            except queue.Full:
                self.discarded += len(events)

    def _run(self):
        store = None
        batch = ()
        try:
            store = LabEventQueue(self.path, **self.options)
            self.health = 'ready'
            while not self.shutdown.is_set() or not self.pending.empty():
                try:
                    batch = self.pending.get(timeout=1)
                except queue.Empty:
                    store.purge()
                    self.purged = store.purged
                    continue
                self.written += store.append_batch(batch)
                with self.lock:
                    self.discarded += store.rejected
                store.rejected = 0
                self.purged, self.health = store.purged, store.health
                batch = ()
        except (OSError, ValueError, sqlite3.Error):
            self.health = 'storage_unavailable'
            with self.lock:
                self.shutdown.set()
                self.discarded += len(batch)
                while True:
                    try:
                        self.discarded += len(self.pending.get_nowait())
                    except queue.Empty:
                        break
            # No exception text or user payload is retained.
        finally:
            if store:
                store.close()

    def close(self):
        with self.lock:
            self.shutdown.set()
        self.worker.join(timeout=3)
        if self.worker.is_alive():
            self.health = 'shutdown_timeout'
