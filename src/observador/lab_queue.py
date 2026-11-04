"""Synthetic queue with bounded main DB, auxiliary budget and explicit losses."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import queue
import re
import sqlite3
import threading
import time
from itertools import islice
from copy import deepcopy

from .collector import utc
from .store import EventStore
from .store import DDL
from .private_directory import reject_links, secure_directory, secure_file
from .storage_budget import StorageBudget
from .lab_faults import LabFaultPlan


class LabEventQueue(EventStore):
    def __init__(self, path, *, max_db_bytes=4 * 1024 * 1024, max_events=10000,
                 retention=timedelta(hours=1), clock=lambda: datetime.now(timezone.utc),
                 max_total_bytes=None, min_free_bytes=1024*1024, fault_plan=None):
        if max_db_bytes < 65536 or max_events < 1 or not timedelta(0) < retention <= timedelta(days=1):
            raise ValueError('invalid laboratory retention or quota')
        self.clock, self.retention, self.max_events = clock, retention, max_events
        self.rejected = self.purged = 0
        if fault_plan is not None and type(fault_plan) is not LabFaultPlan:
            raise ValueError('synthetic_fault_plan_required')
        self.fault_plan = fault_plan
        self.last_error = 'none'
        self.last_outcome = dict(written=0,duplicates=0,rejected=0,uncertain=0)
        self.usable = True
        self.committed_total = 0
        self.health = 'ready'
        path = Path(path).absolute()
        if path.is_symlink() or path.parent.is_symlink() or (path.exists() and path.stat().st_size > max_db_bytes):
            raise ValueError('existing queue exceeds quota or is a symlink')
        reject_links(path)
        secure_directory(path.parent)
        self.path = path
        self.budget = StorageBudget(path, max_db_bytes, max_total_bytes, min_free_bytes)
        self.budget.check()
        if any(path.with_name(path.name+suffix).exists() for suffix in ('-wal','-shm')):
            raise OSError('unsupported_existing_wal_queue')
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
            self.rows_at_open = self.conn.execute('SELECT COUNT(*) FROM events').fetchone()[0]
            self.rows_current = self.rows_at_open
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
            self._hit('purge_before_commit')
        self.purged += deleted
        self.rows_current = self.conn.execute('SELECT COUNT(*) FROM events').fetchone()[0]
        self._hit('purge_after_commit')
        self.budget.check(reserve=False)
        return self.purged

    def _hit(self, stage):
        if self.fault_plan:
            self.fault_plan.hit(stage)

    def diagnostics_snapshot(self):
        return dict(rows_at_open=self.rows_at_open,rows_current=self.rows_current,
                    purged=self.purged,last_error=self.last_error,budget=self.budget.snapshot())

    def append_batch(self, events):
        events = tuple(islice(events,101))
        self.last_outcome = dict(written=0,duplicates=0,rejected=len(events),uncertain=0)
        try:
            return self._append_batch(events)
        except (ValueError,TypeError,AttributeError,OverflowError):
            self.rejected += len(events)
            self.last_error = 'projection'
            raise ValueError('synthetic_queue_projection_rejected') from None

    def _append_batch(self, events):
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
        committed = False
        commit_attempted = False
        attempted = False
        inserted = extra = duplicates = 0
        if not self.usable:
            self.rejected += len(rows)
            self.health = 'storage_unavailable'
            return 0
        try:
            if not self.usable:
                raise OSError('storage_closed_after_rollback_failure')
            self.purge()
            self._hit('before_transaction')
            self.conn.execute('BEGIN IMMEDIATE')
            attempted = True
            # Reject conflicting UUIDs instead of silently accepting changed payloads.
            unique = {}
            for row in rows:
                previous = unique.setdefault(row[0],row[-1])
                saved = self.conn.execute('SELECT payload_json FROM events WHERE event_id=?',(row[0],)).fetchone()
                if previous != row[-1] or (saved and saved[0] != row[-1]):
                    raise ValueError('conflicting_synthetic_event')
            inserted = self.conn.executemany('INSERT OR IGNORE INTO events VALUES (?, ?, ?, ?, ?, ?)', rows).rowcount
            duplicates = len(rows)-inserted
            self._hit('after_insert')
            count = self.conn.execute('SELECT COUNT(*) FROM events').fetchone()[0]
            extra = max(0,count-self.max_events)
            if extra:
                self.conn.execute('DELETE FROM events WHERE event_id IN '
                                  '(SELECT event_id FROM events ORDER BY timestamp_utc,event_id LIMIT ?)',(extra,))
            self.budget.check(reserve=False)  # Observe a live rollback journal.
            self._hit('before_commit')
            commit_attempted = True
            self.conn.commit()
            committed = True
            self.purged += extra
            self.committed_total += inserted
            self.rows_current = count-extra
            self.last_outcome = dict(written=inserted,duplicates=duplicates,rejected=0,uncertain=0)
            self.health = 'ready'
            self.last_error = 'none'
            self._hit('after_commit')
            self.budget.check(reserve=False)
            return inserted
        except (sqlite3.Error,OSError,ValueError) as error:
            # SQLite may return BUSY or FULL; do not copy exception text into health logs.
            code = getattr(error, 'sqlite_errorcode', 0) or 0
            code &= 0xff
            self.health = 'quota_full' if code == sqlite3.SQLITE_FULL else 'storage_unavailable'
            self.last_error = ('post_commit' if committed else 'busy' if code == sqlite3.SQLITE_BUSY else
                               'full' if code == sqlite3.SQLITE_FULL else 'projection' if isinstance(error,ValueError) else 'io')
            if committed:
                return inserted  # Known commit; do not count it again as rejection.
            # FULL/IOERR may auto-rollback SQLite before commit was even called.
            rolled_back = not attempted or (not commit_attempted and not self.conn.in_transaction)
            if self.conn.in_transaction:
                try:
                    self._hit('before_rollback')
                    self.conn.rollback()
                    rolled_back = True
                    self._hit('after_rollback')
                except (sqlite3.Error,OSError):
                    self.last_error = 'rollback_failed'
                    self.usable = False
                    self.conn.close()  # Best effort: recovery must be checked after reopening.
            if rolled_back:
                self.last_outcome = dict(written=0,duplicates=0,rejected=len(rows),uncertain=0)
                self.rejected += len(rows)
            else:
                self.last_outcome = dict(written=0,duplicates=0,rejected=0,uncertain=len(rows))
                self.last_error = 'commit_unknown' if self.usable else 'rollback_failed'
                self.usable = False
            if isinstance(error,ValueError):
                # Already accounted here, unlike validation before the transaction.
                return 0
            return 0

    def insert(self, event):
        return self.append_batch([event]) == 1


class AsyncLabQueue:
    """One SQLite owner; snapshots and UI submission never execute SQL or scan disk."""
    def __init__(self, path, *, capacity=16, **options):
        if type(capacity) is not int or not 1 <= capacity <= 64:
            raise ValueError('queue_capacity_rejected')
        self.path, self.options = path, options
        self.pending = queue.Queue(maxsize=capacity)
        self.shutdown = threading.Event()
        self.discarded = self.written = self.purged = 0
        self.health = 'starting'
        self.lock = threading.RLock()
        self.ledger = dict(received=0,enqueued=0,ingress_rejected=0,buffered=0,inflight=0,
                           written=0,duplicates=0,write_rejected=0,uncertain=0)
        self.storage_sample = None
        self.last_batch_ms = None
        self.worker = threading.Thread(target=self._run, daemon=True)
        self.worker.start()

    def submit(self, events):
        with self.lock:
            self.ledger['received'] += len(events)
            if not events:
                return
            if self.shutdown.is_set() or len(events)>100:
                self.ledger['ingress_rejected'] += len(events)
                self.discarded += len(events)
                return
            try:
                self.pending.put_nowait(tuple(events))
                self.ledger['enqueued'] += len(events)
                self.ledger['buffered'] += len(events)
            except queue.Full:
                self.ledger['ingress_rejected'] += len(events)
                self.discarded += len(events)

    def diagnostics_snapshot(self):
        with self.lock:
            storage=deepcopy(self.storage_sample)
            balance=('unavailable' if storage is None or storage['rows_current'] is None else
                     'balanced' if storage['rows_at_open']+self.ledger['written']-storage['purged']==storage['rows_current']
                     and not self.ledger['uncertain'] else 'unreconciled')
            return dict(health=self.health,shutdown=self.shutdown.is_set(),worker_alive=self.worker.is_alive(),
                        capacity_batches=self.pending.maxsize,ledger=dict(self.ledger),
                        storage=storage,last_batch_ms=self.last_batch_ms,row_balance=balance)

    def _sample(self, store):
        sample = store.diagnostics_snapshot() if store else None
        with self.lock:
            if sample is not None:
                self.storage_sample = sample
                self.purged = sample['purged']

    def _fail_pending(self):
        # Caller owns lock. Inflight was settled separately, exactly once.
        self.shutdown.set()
        while True:
            try:
                batch = self.pending.get_nowait()
                self.ledger['buffered'] -= len(batch)
                self.ledger['write_rejected'] += len(batch)
                self.discarded += len(batch)
            except queue.Empty:
                return

    def _run(self):
        store = None
        batch = ()
        try:
            store = LabEventQueue(self.path, **self.options)
            self._sample(store)
            with self.lock:
                self.health = 'ready'
            while not self.shutdown.is_set() or not self.pending.empty():
                try:
                    batch = self.pending.get(timeout=.1)
                except queue.Empty:
                    store.purge()
                    self._sample(store)
                    continue
                with self.lock:
                    self.ledger['buffered'] -= len(batch)
                    self.ledger['inflight'] += len(batch)
                try:
                    started = time.monotonic()
                    store.append_batch(batch)
                    outcome = store.last_outcome
                except (OSError,ValueError,TypeError,sqlite3.Error):
                    outcome = dict(written=0,duplicates=0,rejected=len(batch),uncertain=0)
                    store.health = 'storage_unavailable'
                sample = store.diagnostics_snapshot()
                with self.lock:
                    self.storage_sample = sample
                    self.purged = sample['purged']
                    self.last_batch_ms = max(0,(time.monotonic()-started)*1000)
                    self.ledger['inflight'] -= len(batch)
                    for target,source in (('written','written'),('duplicates','duplicates'),
                                          ('write_rejected','rejected'),('uncertain','uncertain')):
                        self.ledger[target] += outcome[source]
                    self.written = self.ledger['written']
                    self.discarded += outcome['rejected']
                    self.health = store.health
                    batch = ()
                    if self.health != 'ready' or outcome['uncertain']:
                        self._fail_pending()
                        break
        except (OSError,ValueError,TypeError,sqlite3.Error):
            with self.lock:
                self.health = 'storage_unavailable'
                if batch:
                    self.ledger['inflight'] -= len(batch)
                    self.ledger['uncertain'] += len(batch)
                self._fail_pending()
        finally:
            if store:
                try:
                    store.close()
                except sqlite3.Error:
                    with self.lock:
                        self.health = 'storage_unavailable'

    def close(self):
        self.shutdown.set()
        self.worker.join(timeout=3)
        if self.worker.is_alive():
            with self.lock:
                self.health = 'shutdown_timeout'
