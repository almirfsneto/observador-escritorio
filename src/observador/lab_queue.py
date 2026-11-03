"""Synthetic queue with bounded main DB, auxiliary budget and explicit losses."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import queue
import re
import sqlite3
import threading

from .collector import utc
from .store import EventStore
from .store import DDL
from .private_directory import reject_links, secure_directory, secure_file
from .storage_budget import StorageBudget


class LabEventQueue(EventStore):
    def __init__(self, path, *, max_db_bytes=4 * 1024 * 1024, max_events=10000,
                 retention=timedelta(hours=1), clock=lambda: datetime.now(timezone.utc),
                 max_total_bytes=None, min_free_bytes=1024*1024):
        if max_db_bytes < 65536 or max_events < 1 or not timedelta(0) < retention <= timedelta(days=1):
            raise ValueError('invalid laboratory retention or quota')
        self.clock, self.retention, self.max_events = clock, retention, max_events
        self.rejected = self.purged = 0
        self.health = 'ready'
        path = Path(path).absolute()
        if path.is_symlink() or path.parent.is_symlink() or (path.exists() and path.stat().st_size > max_db_bytes):
            raise ValueError('existing queue exceeds quota or is a symlink')
        reject_links(path)
        secure_directory(path.parent)
        self.path = path
        self.budget = StorageBudget(path, max_db_bytes, max_total_bytes, min_free_bytes)
        self.budget.check()
        # Repair permissions on pre-existing journals before SQLite crash recovery.
        for entry in path.parent.iterdir():
            secure_file(entry)
        self.conn = sqlite3.connect(path, timeout=.05)
        try:
            secure_file(path)
            self.conn.execute('PRAGMA busy_timeout=50')
            # Do not retain deleted values in SQLite free pages. Does not promise SSD erasure.
            self.conn.execute('PRAGMA secure_delete=ON')
            mode = self.conn.execute('PRAGMA journal_mode=DELETE').fetchone()[0]
            if mode != 'delete':
                raise ValueError('unsupported_queue_journal')
            self.conn.execute('PRAGMA synchronous=FULL')
            self.conn.execute('PRAGMA temp_store=MEMORY')
            self.conn.execute('PRAGMA cache_spill=OFF')
            self.conn.execute('PRAGMA cache_size=-2048')
            if self.conn.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                raise ValueError('queue_corrupt')
            page_size = self.conn.execute('PRAGMA page_size').fetchone()[0]
            pages = max_db_bytes // page_size
            actual = self.conn.execute(f'PRAGMA max_page_count={pages}').fetchone()[0]
            if actual > pages:
                raise ValueError('existing queue exceeds page quota')
            self.conn.executescript(DDL)
            self.purge()
        except Exception:
            self.close()
            raise

    def purge(self):
        self.budget.check()
        cutoff = (utc(self.clock()) - self.retention).isoformat()
        with self.conn:
            cursor = self.conn.execute('DELETE FROM events WHERE julianday(timestamp_utc) < julianday(?)', (cutoff,))
            deleted = cursor.rowcount
            extra = max(0, self.conn.execute('SELECT COUNT(*) FROM events').fetchone()[0] - self.max_events)
            if extra:
                cursor = self.conn.execute('DELETE FROM events WHERE event_id IN '
                                           '(SELECT event_id FROM events ORDER BY timestamp_utc, event_id LIMIT ?)', (extra,))
                deleted += cursor.rowcount
            self.budget.check(reserve=False)
        self.purged += deleted
        self.budget.check(reserve=False)
        return self.purged

    def append_batch(self, events):
        # Validate before opening a transaction. Never persist raw UIA dictionaries.
        now = utc(self.clock())
        rows = []
        for event in events:
            if len(rows) >= 100:
                raise ValueError('queue_batch_limit')
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
                self.budget.check(reserve=False)
            self.purged += extra
            inserted = self.conn.total_changes - before - extra
            self.health = 'ready'
            try:
                self.budget.check(reserve=False)
            except OSError:
                self.health = 'storage_unavailable'  # Already committed: never count these as lost.
            return inserted
        except (sqlite3.Error, OSError) as error:
            # SQLite may return BUSY or FULL; do not copy exception text into health logs.
            self.rejected += len(rows)
            code = getattr(error, 'sqlite_errorcode', 0) or 0
            code &= 0xff
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
            if not events:
                return
            if self.shutdown.is_set():
                self.discarded += len(events)
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
                try:
                    store.close()
                except sqlite3.Error:
                    self.health = 'storage_unavailable'

    def close(self):
        with self.lock:
            self.shutdown.set()
        self.worker.join(timeout=3)
        if self.worker.is_alive():
            self.health = 'shutdown_timeout'
