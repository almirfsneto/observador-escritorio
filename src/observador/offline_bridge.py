"""Offline synthetic inbox and explicit file ACKs. No socket, daemon or auto capture."""
from copy import deepcopy
from datetime import datetime,timezone
import hashlib
import json
import re
from pathlib import Path
import sqlite3
import threading
import time
from uuid import UUID,uuid4

from .lab_faults import LabFaultPlan
from .events import Event
from .web_events import validate_web_export
from .dpapi_archive import validate_archive_event
from .private_directory import secure_directory,secure_file,reject_links
from .storage_budget import StorageBudget
from .acceptance_report import safe_output_directory

ORIGINS={'web':'http://127.0.0.1:8765','windows':'owned_synthetic_process'}
BATCH_KEYS={'schema_version','kind','bridge_epoch','generation','batch_sequence','batch_id','source','events'}
ACK_KEYS={'schema_version','kind','bridge_epoch','generation','batch_sequence','batch_id','source_instance',
          'digest','accepted_count','written_count','source_gap_count','source_last_sequence','scope','status'}
MAX_BYTES=256*1024
EVENT_TTL_MS=3600*1000
RECEIPT_TTL_MS=24*3600*1000
MAX_BATCH_MARKERS=1024
MAX_EVENT_MARKERS=10000


class BridgeError(ValueError):pass


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)

def uuid(value):
    try:
        if type(value) is not str or str(UUID(value))!=value:raise ValueError()
    except (ValueError,TypeError,AttributeError):raise BridgeError('bridge_identity_rejected') from None
    return value


def number(value,minimum=1,maximum=2**53-1):
    if type(value) is not int or not minimum<=value<=maximum:raise BridgeError('bridge_number_rejected')
    return value


def validate_source(source):
    try:
        if type(source) is not dict or set(source)!={'kind','version','instance','origin','tab_slot'}:raise ValueError()
        if source['kind'] not in ORIGINS or type(source['version']) is not int or source['version']!=1:raise ValueError()
        uuid(source['instance'])
        if source['origin']!=ORIGINS[source['kind']]:raise ValueError()
        if source['kind']=='web':number(source['tab_slot'],1,2)
        elif source['tab_slot'] is not None:raise ValueError()
        return source
    except (ValueError,TypeError,KeyError,AttributeError):raise BridgeError('bridge_source_rejected') from None


def validate_batch(batch):
    try:
        if type(batch) is not dict or set(batch)!=BATCH_KEYS or batch['schema_version']!=1 or type(batch['schema_version']) is not int or batch['kind']!='synthetic_source_batch':raise ValueError()
        source=validate_source(batch['source'])
        uuid(batch['bridge_epoch']);uuid(batch['batch_id'])
        number(batch['generation']);number(batch['batch_sequence'])
        if type(batch['events']) is not list or not 1<=len(batch['events'])<=100 or len(canonical(batch).encode())>MAX_BYTES:raise ValueError()
        if source['kind']=='web':
            events=validate_web_export(dict(schema_version=1,kind='synthetic_web_extension',capture_real=False,pilot_authorized=False,
                                           events=batch['events'],dropped=0,rejected=0))
        else:
            events=[Event.from_dict(row) for row in batch['events']]
            for event,row in zip(events,batch['events']):
                if set(event.to_dict())!=set(row):raise ValueError()
                validate_archive_event(event)
        previous=0;identities=set()
        for event in events:
            uuid(event.event_id)
            if event.session_id!=source['instance'] or event.event_id in identities:raise ValueError()
            sequence=number(event.metadata.get('source_sequence'))
            if sequence<=previous:raise ValueError()
            previous=sequence;identities.add(event.event_id)
        return events
    except (ValueError,TypeError,KeyError,AttributeError,OverflowError):raise BridgeError('bridge_batch_rejected') from None


def make_batch(ticket,events,batch_sequence=None,batch_id=None):
    if type(ticket) is not dict or set(ticket)!={'schema_version','kind','bridge_epoch','generation','source','next_batch_sequence','next_source_sequence','remaining_ms'} or ticket['kind']!='synthetic_bridge_ticket' or type(ticket['schema_version']) is not int or ticket['schema_version']!=1:
        raise BridgeError('bridge_ticket_rejected')
    validate_source(ticket['source']);uuid(ticket['bridge_epoch']);number(ticket['generation'])
    number(ticket['next_source_sequence']);number(ticket['next_batch_sequence']);number(ticket['remaining_ms'],1,900000)
    batch=dict(schema_version=1,kind='synthetic_source_batch',bridge_epoch=ticket['bridge_epoch'],generation=ticket['generation'],
        batch_sequence=ticket['next_batch_sequence'] if batch_sequence is None else batch_sequence,batch_id=batch_id or str(uuid4()),source=deepcopy(ticket['source']),
        events=[event.to_dict() for event in events])
    validate_batch(batch)
    return batch


def validate_ack(ack):
    try:
        if type(ack) is not dict or set(ack)!=ACK_KEYS or type(ack['schema_version']) is not int or ack['schema_version']!=1 or ack['kind']!='synthetic_bridge_ack':raise ValueError()
        for key in ('bridge_epoch','batch_id','source_instance'):uuid(ack[key])
        for key in ('generation','batch_sequence','accepted_count','written_count','source_last_sequence'):number(ack[key])
        number(ack['source_gap_count'],0)
        if (ack['accepted_count']!=ack['written_count'] or ack['accepted_count']>100 or not re.fullmatch('[a-f0-9]{64}',ack['digest'])
                or ack['scope']!='durable_local_inbox_not_business_completion' or ack['status']!='committed'):raise ValueError()
        return ack
    except (ValueError,TypeError,KeyError):raise BridgeError('bridge_ack_rejected') from None


def write_bridge_document(document,repository,destination):
    if type(document) is not dict:raise BridgeError('bridge_document_rejected')
    if document.get('kind')=='synthetic_bridge_ack':validate_ack(document)
    elif document.get('kind')=='synthetic_source_batch':validate_batch(document)
    elif document.get('kind')=='synthetic_bridge_ticket':
        # Validate exact ticket structure without introducing events.
        if set(document)!={'schema_version','kind','bridge_epoch','generation','source','next_batch_sequence','next_source_sequence','remaining_ms'}:
            raise BridgeError('bridge_ticket_rejected')
        validate_source(document['source']);uuid(document['bridge_epoch']);number(document['generation'])
        number(document['next_batch_sequence']);number(document['next_source_sequence']);number(document['remaining_ms'],1,900000)
        if type(document['schema_version']) is not int or document['schema_version']!=1:raise BridgeError('bridge_ticket_rejected')
    else:raise BridgeError('bridge_document_rejected')
    path=Path(destination).absolute()
    safe_output_directory(repository,path.parent).mkdir(parents=True,exist_ok=True,mode=0o700)
    with path.open('x',encoding='utf-8') as stream:stream.write(canonical(document)+'\n')
    return path


def read_batch(path):
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError()
            result[key]=value
        return result
    try:
        with Path(path).open('rb') as source:payload=source.read(MAX_BYTES+1)
        if len(payload)>MAX_BYTES:raise ValueError()
        batch=json.loads(payload,object_pairs_hook=pairs,parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        validate_batch(batch)
        return batch
    except (ValueError,TypeError,RecursionError,UnicodeError):raise BridgeError('bridge_batch_rejected') from None


class OfflineBridge:
    """Single caller/owner thread for SQLite; locks serialize admission/control ACK.

    Sources are DECLARED synthetic provenance authorized by a trusted caller.
    This file bridge does not authenticate browser origin or replace native PID binding.
    """
    def __init__(self,path,*,clock=lambda:datetime.now(timezone.utc),monotonic=time.monotonic,fault_plan=None):
        self.clock,self.monotonic=clock,monotonic
        if fault_plan is not None and type(fault_plan) is not LabFaultPlan:raise BridgeError('bridge_fault_plan_rejected')
        self.fault_plan=fault_plan
        self.metrics=dict(events_purged=0,receipts_purged=0,ack_recovered=0,receipt_unavailable=0,
                          capacity_rejected=0,storage_errors=0,clock_regressions=0)
        self._clock_floor=int(self.clock().timestamp()*1000)
        self._mono_floor=self.monotonic()
        self.state='disabled';self.bindings={};self.lock=threading.RLock()
        self.path=Path(path).absolute();reject_links(self.path)
        safe_output_directory(Path(__file__).resolve().parents[2],self.path.parent)
        secure_directory(self.path.parent)
        self.budget=StorageBudget(self.path,4*1024*1024)
        self.budget.check()
        existed=self.path.exists() and self.path.stat().st_size>0
        if existed and self.path.stat().st_size>4*1024*1024:raise BridgeError('bridge_database_too_large')
        if any(self.path.with_name(self.path.name+suffix).exists() for suffix in ('-wal','-shm')):raise BridgeError('bridge_wal_rejected')
        for entry in self.path.parent.iterdir():secure_file(entry)
        self.conn=sqlite3.connect(self.path,timeout=.05)
        try:
            secure_file(self.path)
            if existed and (self.conn.execute('PRAGMA application_id').fetchone()[0]!=0x4f425342 or self.conn.execute('PRAGMA user_version').fetchone()[0] not in (1,2)):
                raise BridgeError('bridge_database_format_rejected')
            self.conn.execute('PRAGMA journal_mode=DELETE');self.conn.execute('PRAGMA synchronous=FULL')
            self.conn.execute('PRAGMA secure_delete=ON');self.conn.execute('PRAGMA cache_spill=OFF')
            self.conn.execute('PRAGMA temp_store=MEMORY');self.conn.execute('PRAGMA cache_size=-2048')
            page_size=self.conn.execute('PRAGMA page_size').fetchone()[0]
            pages=4*1024*1024//page_size
            if self.conn.execute(f'PRAGMA max_page_count={pages}').fetchone()[0]>pages:raise BridgeError('bridge_database_too_large')
            if self.conn.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise BridgeError('bridge_integrity_failed')
            self.conn.execute('BEGIN IMMEDIATE')
            with self.conn:
                self._schema()
                self.conn.execute('INSERT OR IGNORE INTO meta VALUES (?,?)',('epoch',str(uuid4())))
                self.conn.execute('INSERT OR IGNORE INTO meta VALUES (?,?)',('generation','0'))
                self.epoch=str(uuid4())  # New process revokes previous uncommitted tickets.
                self.conn.execute('UPDATE meta SET value=? WHERE key="epoch"',(self.epoch,))
                self.generation=int(self.conn.execute('SELECT value FROM meta WHERE key="generation"').fetchone()[0])+1
                self.conn.execute('UPDATE meta SET value=? WHERE key="generation"',(str(self.generation),))
                self.conn.execute('PRAGMA application_id=1329746754')
                self.conn.execute('PRAGMA user_version=2')
        except Exception:
            self.conn.close();raise BridgeError('bridge_database_unavailable') from None
        self.expires=self.deadline=None
        self.last_clock=self.clock()
        try:self.purge()
        except Exception:
            self.conn.close();raise

    def _schema(self):
        self.conn.execute('CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY,value TEXT NOT NULL)')
        self.conn.execute('CREATE TABLE IF NOT EXISTS sources (instance TEXT PRIMARY KEY,source_json TEXT NOT NULL,last_batch INTEGER NOT NULL,last_sequence INTEGER NOT NULL)')
        self.conn.execute('CREATE TABLE IF NOT EXISTS receipts (instance TEXT NOT NULL,batch_id TEXT NOT NULL,digest TEXT NOT NULL,ack_json TEXT NOT NULL,PRIMARY KEY(instance,batch_id))')
        self.conn.execute('CREATE TABLE IF NOT EXISTS events (instance TEXT NOT NULL,event_id TEXT NOT NULL,source_sequence INTEGER NOT NULL,payload_json TEXT NOT NULL,PRIMARY KEY(instance,event_id))')
        # Markers have no TTL. Their finite capacity is an admission stop, never eviction.
        self.conn.execute('CREATE TABLE IF NOT EXISTS batch_markers (batch_id TEXT PRIMARY KEY,instance TEXT NOT NULL,digest TEXT NOT NULL)')
        self.conn.execute('CREATE TABLE IF NOT EXISTS event_markers (event_id TEXT PRIMARY KEY,instance TEXT NOT NULL)')
        for table in ('events','receipts'):
            columns={row[1] for row in self.conn.execute('PRAGMA table_info('+table+')')}
            if 'committed_ms' not in columns:
                self.conn.execute('ALTER TABLE '+table+' ADD COLUMN committed_ms INTEGER NOT NULL DEFAULT 0')
                # v1 had no admission clock. Grant a full window from migration, not event UTC.
                self.conn.execute('UPDATE '+table+' SET committed_ms=?',(self._clock_floor,))
        self.conn.execute('INSERT OR IGNORE INTO meta VALUES (?,?)',('retention_ms',str(self._clock_floor)))
        if self.conn.execute('PRAGMA user_version').fetchone()[0]==1:
            # Collision/over-capacity => rollback the entire migration, preserve original.
            self.conn.execute('INSERT INTO batch_markers SELECT batch_id,instance,digest FROM receipts')
            self.conn.execute('INSERT INTO event_markers SELECT event_id,instance FROM events')
        if (self.conn.execute('SELECT COUNT(*) FROM batch_markers').fetchone()[0]>MAX_BATCH_MARKERS or
                self.conn.execute('SELECT COUNT(*) FROM event_markers').fetchone()[0]>MAX_EVENT_MARKERS):
            raise BridgeError('bridge_marker_capacity_reached')

    def _hit(self,stage):
        if self.fault_plan:self.fault_plan.hit(stage)

    def _retention_now(self):
        persisted=int(self.conn.execute('SELECT value FROM meta WHERE key="retention_ms"').fetchone()[0])
        wall=int(self.clock().timestamp()*1000);mono=self.monotonic()
        if wall<self._clock_floor or mono<self._mono_floor or wall<persisted:
            self.metrics['clock_regressions']+=1
            if self.state in ('active','paused','disabled'):self.state='expired'
            # Freeze retention on backward wall/monotonic jumps, including across restart.
            return max(persisted,self._clock_floor)
        current=max(wall,persisted,self._clock_floor)
        self._clock_floor=current;self._mono_floor=mono
        return current

    def purge(self):
        '''Explicit synchronous maintenance; runs on open/read/ingest, even paused/expired.

        Expiration uses local admission time, not producer timestamps. No background daemon.
        '''
        with self.lock:
            try:
                self.budget.check()
                with self.conn:
                    self.conn.execute('BEGIN IMMEDIATE');self._assert_owner()
                    now=self._retention_now()
                    events=self.conn.execute('DELETE FROM events WHERE committed_ms<=?',(now-EVENT_TTL_MS,)).rowcount
                    receipts=self.conn.execute('DELETE FROM receipts WHERE committed_ms<=?',(now-RECEIPT_TTL_MS,)).rowcount
                    self.conn.execute('UPDATE meta SET value=? WHERE key="retention_ms"',(str(now),))
                    self.budget.check(reserve=False);self._hit('purge_before_commit')
                self.metrics['events_purged']+=events;self.metrics['receipts_purged']+=receipts
                self._hit('purge_after_commit')
                return dict(events=events,receipts=receipts)
            except (sqlite3.Error,OSError,BridgeError):
                self.metrics['storage_errors']+=1;self.state='failed'
                raise BridgeError('bridge_retention_failed_reopen_required') from None

    def retention_snapshot(self):
        '''Owner-thread diagnostic, not for UI callbacks; counters are process-local.'''
        counts={table:self.conn.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]
                for table in ('events','receipts','event_markers','batch_markers','sources')}
        return dict(schema_version=1,kind='synthetic_inbox_retention',state=self.state,counts=counts,
                    counters=dict(self.metrics),budget=self.budget.snapshot(),physical_quota=False)


    def authorize(self,source):
        source=deepcopy(validate_source(source))
        with self.lock:
            if self.state!='disabled' or len(self.bindings)>=3:raise BridgeError('bridge_authorization_closed')
            if source['kind']=='web' and any(v['kind']=='web' and v['tab_slot']==source['tab_slot'] and v['instance']!=source['instance'] for v in self.bindings.values()):raise BridgeError('bridge_tab_not_authorized')
            if source['kind']=='windows' and any(v['kind']=='windows' and v['instance']!=source['instance'] for v in self.bindings.values()):raise BridgeError('bridge_source_limit')
            saved=self.conn.execute('SELECT source_json FROM sources WHERE instance=?',(source['instance'],)).fetchone()
            if saved and saved[0]!=canonical(source):raise BridgeError('bridge_provenance_conflict')
            if self.conn.execute('SELECT COUNT(*) FROM sources').fetchone()[0]>=32 and not saved:raise BridgeError('bridge_source_limit')
            self.budget.check()
            with self.conn:
                self.conn.execute('BEGIN IMMEDIATE');self._assert_owner()
                self.conn.execute('INSERT OR IGNORE INTO sources VALUES (?,?,0,0)',(source['instance'],canonical(source)))
            self.bindings[source['instance']]=source

    def _expire(self):
        now=self.clock()
        if self.state in ('active','paused') and (now<self.last_clock or now>=self.expires or self.monotonic()>=self.deadline):self.state='expired'
        self.last_clock=now

    def _assert_owner(self):
        if self.conn.execute('SELECT value FROM meta WHERE key="epoch"').fetchone()[0]!=self.epoch:
            self.state='failed'
            raise BridgeError('bridge_owner_replaced')

    def control(self,action):
        with self.lock:
            self._expire()
            if action not in ('start','pause','resume','stop') or self.state in ('expired','stopped','failed'):raise BridgeError('bridge_control_rejected')
            if action=='start':
                if self.state!='disabled' or not self.bindings:raise BridgeError('bridge_control_rejected')
                from datetime import timedelta
                self.expires=self.clock()+timedelta(minutes=15);self.deadline=self.monotonic()+900
                self.state='active'
            elif action=='resume':
                if self.state!='paused':raise BridgeError('bridge_control_rejected')
                self.state='active'
            elif action=='pause':
                if self.state!='active':raise BridgeError('bridge_control_rejected')
                self.state='paused'
            else:self.state='stopped'
            self.generation+=1
            try:
                self.conn.execute('BEGIN IMMEDIATE')
                with self.conn:
                    self._assert_owner()
                    self.conn.execute('UPDATE meta SET value=? WHERE key="generation"',(str(self.generation),))
            except (sqlite3.Error,OSError,BridgeError):
                self.state='failed';raise BridgeError('bridge_control_persist_failed') from None
            return dict(schema_version=1,kind='synthetic_bridge_control_ack',generation=self.generation,state=self.state,
                        scope='bridge_admission_only_producers_not_confirmed')

    def ticket(self,instance):
        with self.lock:
            self._expire()
            self._assert_owner()
            if self.state!='active' or instance not in self.bindings:raise BridgeError('bridge_not_active')
            last_batch,last_sequence=self.conn.execute('SELECT last_batch,last_sequence FROM sources WHERE instance=?',(instance,)).fetchone()
            return dict(schema_version=1,kind='synthetic_bridge_ticket',bridge_epoch=self.epoch,generation=self.generation,
                source=deepcopy(self.bindings[instance]),next_batch_sequence=last_batch+1,next_source_sequence=last_sequence+1,
                remaining_ms=max(1,min(900000,int(min((self.expires-self.clock()).total_seconds(),self.deadline-self.monotonic())*1000))))

    def ingest(self,batch):
        events=validate_batch(batch);source=batch['source'];instance=source['instance']
        digest=hashlib.sha256(canonical(batch).encode()).hexdigest()
        with self.lock:
            self._expire()
            self._assert_owner()
            if self.bindings.get(instance)!=source:raise BridgeError('bridge_source_not_authorized')
            old=self.conn.execute('SELECT digest,ack_json,committed_ms FROM receipts WHERE instance=? AND batch_id=?',(instance,batch['batch_id'])).fetchone()
            if old and old[2]>self._retention_now()-RECEIPT_TTL_MS:
                if old[0]!=digest:raise BridgeError('bridge_batch_id_conflict')
                self.metrics['ack_recovered']+=1
                return json.loads(old[1])  # Historical durable ACK, no fresh admission even while paused.
            self.purge()
            marker=self.conn.execute('SELECT digest FROM batch_markers WHERE batch_id=?',(batch['batch_id'],)).fetchone()
            if marker:
                self.metrics['receipt_unavailable']+=1
                raise BridgeError('receipt_expired_or_unknown')
            if self.state!='active' or batch['bridge_epoch']!=self.epoch or batch['generation']!=self.generation:raise BridgeError('bridge_stale_or_inactive')
            last_batch,last_sequence=self.conn.execute('SELECT last_batch,last_sequence FROM sources WHERE instance=?',(instance,)).fetchone()
            if batch['batch_sequence']<=last_batch:
                self.metrics['receipt_unavailable']+=1
                raise BridgeError('receipt_expired_or_unknown')
            if batch['batch_sequence']!=last_batch+1:raise BridgeError('bridge_batch_replay_or_gap')
            if events[0].metadata['source_sequence']<=last_sequence:raise BridgeError('bridge_event_replay')
            if (self.conn.execute('SELECT COUNT(*) FROM receipts').fetchone()[0]>=128 or
                    self.conn.execute('SELECT COUNT(*) FROM events').fetchone()[0]+len(events)>10000 or
                    self.conn.execute('SELECT COUNT(*) FROM batch_markers').fetchone()[0]>=MAX_BATCH_MARKERS or
                    self.conn.execute('SELECT COUNT(*) FROM event_markers').fetchone()[0]+len(events)>MAX_EVENT_MARKERS):
                self.metrics['capacity_rejected']+=1
                raise BridgeError('bridge_capacity_reached_markers_preserved')
            missing=0;previous=last_sequence
            for event in events:
                sequence=event.metadata['source_sequence'];missing+=sequence-previous-1;previous=sequence
                if self.conn.execute('SELECT 1 FROM event_markers WHERE event_id=?',(event.event_id,)).fetchone():raise BridgeError('bridge_event_identity_reused')
            ack=dict(schema_version=1,kind='synthetic_bridge_ack',bridge_epoch=self.epoch,generation=self.generation,
                batch_sequence=batch['batch_sequence'],batch_id=batch['batch_id'],source_instance=instance,digest=digest,
                accepted_count=len(events),written_count=len(events),source_gap_count=missing,source_last_sequence=previous,
                scope='durable_local_inbox_not_business_completion',status='committed')
            try:
                self.budget.check();self._hit('before_transaction')
                with self.conn:
                    self.conn.execute('BEGIN IMMEDIATE')
                    self._assert_owner()
                    progress=self.conn.execute('SELECT last_batch,last_sequence FROM sources WHERE instance=?',(instance,)).fetchone()
                    if progress!=(last_batch,last_sequence):raise BridgeError('bridge_progress_changed')
                    committed_ms=self._retention_now()
                    if self.state!='active':raise BridgeError('bridge_clock_changed')
                    self.conn.executemany('INSERT INTO events VALUES (?,?,?,?,?)',[(instance,e.event_id,e.metadata['source_sequence'],canonical(e.to_dict()),committed_ms) for e in events])
                    self.conn.executemany('INSERT INTO event_markers VALUES (?,?)',[(e.event_id,instance) for e in events])
                    self.conn.execute('INSERT INTO batch_markers VALUES (?,?,?)',(batch['batch_id'],instance,digest))
                    self._hit('after_insert')
                    self.conn.execute('UPDATE sources SET last_batch=?,last_sequence=? WHERE instance=?',(batch['batch_sequence'],previous,instance))
                    self.conn.execute('INSERT INTO receipts VALUES (?,?,?,?,?)',(instance,batch['batch_id'],digest,canonical(ack),committed_ms))
                    self.budget.check(reserve=False);self._hit('before_commit')
                self._hit('after_commit')
            except (sqlite3.Error,OSError):
                self.state='failed';self.metrics['storage_errors']+=1
                raise BridgeError('bridge_commit_failed_retry_requires_receipt_check') from None
            return ack

    def source_events(self):
        # Never impose a global timestamp sort on independent sources.
        self.purge()
        result=[]
        for instance,source in sorted(self.bindings.items()):
            rows=self.conn.execute('SELECT payload_json FROM events WHERE instance=? ORDER BY source_sequence',(instance,)).fetchall()
            result.append(dict(source=deepcopy(source),events=[Event.from_dict(json.loads(row[0])) for row in rows],
                gaps=['no_global_order','timestamps_not_synchronized','declared_provenance_not_authentication','producer_pause_not_confirmed']))
        return result

    def close(self):
        self.state='stopped';self.conn.close()
