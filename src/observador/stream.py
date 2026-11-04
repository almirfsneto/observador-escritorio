"""Bounded, generation-aware laboratory event stream. No raw UI data accepted."""
from collections import deque
from datetime import datetime, timedelta, timezone
import json
import re
import threading
import time
from uuid import uuid4

from .collector import ROLES, utc
from .events import Event


class LabStream:
    def __init__(self, expires_at, *, clock=lambda: datetime.now(timezone.utc),
                 monotonic=time.monotonic, capacity=256):
        self.clock, self.monotonic = clock, monotonic
        self.expires_at = utc(expires_at)
        self.deadline = monotonic() + max(0, (self.expires_at - utc(clock())).total_seconds())
        self.capacity = capacity
        self.events = deque()
        self.lock = threading.RLock()
        self.generation = 0
        self.enabled = False
        self.stopped = False
        self.ready = False
        self.health = 'paused'
        self.dropped = 0
        self.native_dropped = 0
        self.native_callbacks = {}
        self.native_queues = None
        self.last_health_received = None
        self.flow = dict(received=0,accepted=0,rejected=0,coalesced=0,overflow=0,drained=0,discarded=0)
        self.invalid = 0
        self.last_sequence = 0
        self.sequence_gaps = 0
        self.session = str(uuid4())
        self.started_at = utc(clock())
        self.last_received = monotonic()
        self.pending_ack_at = None
        self.last_focus = None
        self.protocol_failure = None
        self.native_error = None
        self.validation_stage = 'shape'

    def alive(self):
        if utc(self.clock()) >= self.expires_at or self.monotonic() >= self.deadline:
            self.stop()
        return not self.stopped

    def command(self, active):
        with self.lock:
            if not self.alive():
                return None
            self.generation += 1
            self.enabled = active
            self._clear()
            self.last_focus = None
            self.last_sequence = 0
            self.health = 'starting' if active else 'pausing'
            self.pending_ack_at = self.monotonic()
            return {'command': 'start' if active else 'pause', 'generation': self.generation}

    def stop(self, reason='stopped'):
        with self.lock:
            self.stopped = True
            self.enabled = False
            self._clear()
            self.health = reason

    def _clear(self):
        self.flow['discarded'] += len(self.events)
        self.events.clear()

    def diagnostics_snapshot(self):
        with self.lock:
            self.alive()
            return dict(enabled=self.enabled,stopped=self.stopped,ready=self.ready,
                        expired=utc(self.clock())>=self.expires_at or self.monotonic()>=self.deadline,
                        pending_ack=self.pending_ack_at is not None,flow=dict(self.flow),buffered=len(self.events),
                        capacity=self.capacity,invalid_messages=self.invalid,sequence_gaps=self.sequence_gaps,
                        native_callbacks=dict(self.native_callbacks),native_dropped=self.native_dropped,
                        native_queues=dict(self.native_queues) if self.native_queues else None,
                        native_age_ms=None if self.last_health_received is None else max(0,(self.monotonic()-self.last_health_received)*1000))

    def receive(self, line):
        with self.lock:
            if not self.alive():
                return
            try:
                kind = None
                self.validation_stage = 'shape'
                if len(line) > 4096:
                    raise ValueError()
                data = json.loads(line)
                if not isinstance(data, dict):
                    raise ValueError()
                kind = data.get('kind')
                if kind == 'ready' and set(data) == {'kind', 'pid', 'start_ticks'}:
                    if self.ready or type(data['pid']) is not int or type(data['start_ticks']) is not int:
                        raise ValueError()
                    # Process identity is checked by NativeSession before this call.
                    self.ready = True
                    if self.pending_ack_at is not None:
                        self.pending_ack_at = self.monotonic()
                elif kind == 'health' and set(data) in ({'kind','generation','dropped','callbacks'},
                                                       {'kind','generation','dropped','callbacks','queues'}):
                    if (type(data['dropped']) is not int or data['dropped'] < 0
                            or type(data['generation']) is not int):
                        raise ValueError()
                    counters = data['callbacks']
                    if (not isinstance(counters, dict) or set(counters) != {'focus', 'invoke', 'toggle', 'excluded', 'errors'}
                            or any(type(value) is not int or value < 0 for value in counters.values())):
                        raise ValueError()
                    self.native_callbacks = counters
                    if 'queues' in data:
                        queues=data['queues']
                        if (type(queues) is not dict or set(queues) != {'output_depth','output_capacity','focus_depth','focus_capacity'}
                                or any(type(value) is not int for value in queues.values())
                                or queues['output_capacity'] != 512 or queues['focus_capacity'] != 256
                                or not 0<=queues['output_depth']<=512 or not 0<=queues['focus_depth']<=256):
                            raise ValueError()
                        self.native_queues=queues
                    self.last_health_received=self.monotonic()
                    self.native_dropped = max(self.native_dropped, data['dropped'])
                elif kind == 'ack' and set(data) == {'kind', 'generation', 'active'}:
                    if type(data['active']) is not bool or type(data['generation']) is not int:
                        raise ValueError()
                    if data['generation'] == self.generation:
                        if data['active'] != self.enabled:
                            raise ValueError()
                        self.health = 'active' if self.enabled else 'paused'
                        self.pending_ack_at = None
                elif kind == 'event':
                    self.flow['received'] += 1
                    self._event(data)
                elif kind == 'error' and set(data) == {'kind', 'code', 'hresult'} and type(data['hresult']) is int and data['code'] in {
                        'invalid_config', 'subscription_failed', 'backend_failure',
                        'fixture_window_unavailable', 'uia_root_failed', 'focus_subscription_failed',
                        'invoke_subscription_failed', 'toggle_subscription_failed'}:
                    self.native_error = data['hresult']
                    self.stop(data['code'])
                else:
                    raise ValueError()
                self.last_received = self.monotonic()
            except (ValueError, TypeError, KeyError, OverflowError):
                if kind == 'event':
                    self.flow['rejected'] += 1
                self.invalid += 1
                self.protocol_failure = self.validation_stage
                self.stop('protocol_error')

    def _event(self, data):
        if set(data) != {'kind', 'generation', 'sequence', 'timestamp_utc', 'action', 'role', 'control_id'}:
            raise ValueError()
        if (type(data['generation']) is not int or type(data['sequence']) is not int
                or data['sequence'] <= 0 or type(data['role']) is not int
                or data['action'] not in {'focus', 'invoke', 'toggle'}
                or not isinstance(data['timestamp_utc'], str)
                or not isinstance(data['control_id'], str)
                or not re.fullmatch('[a-f0-9]{16}', data['control_id'])):
            raise ValueError()
        self.validation_stage = 'timestamp'
        stamp = utc(datetime.fromisoformat(data['timestamp_utc'].replace('Z', '+00:00')))
        # Windows runtimes can expose clocks with different resolutions. Local
        # receipt/monotonic time still enforce expiry; never accept unbounded future dates.
        if not self.started_at <= stamp <= utc(self.clock()) + timedelta(milliseconds=100) or stamp >= self.expires_at:
            raise ValueError()
        if not self.ready or not self.enabled or data['generation'] != self.generation:
            self.flow['rejected'] += 1
            return  # Paused and superseded generations never reach the timeline.
        self.validation_stage = 'sequence'
        if data['sequence'] <= self.last_sequence:
            raise ValueError()
        if self.last_sequence:
            self.sequence_gaps += data['sequence'] - self.last_sequence - 1
        self.last_sequence = data['sequence']
        role = ROLES.get(data['role'], 'control')
        signature = (role, data['control_id'])
        if data['action'] == 'focus' and self.last_focus == signature:
            self.flow['coalesced'] += 1
            return
        self.last_focus = signature if data['action'] == 'focus' else None
        event = Event(1, str(uuid4()), stamp.isoformat(), 'laboratorio-sintetico', self.session,
                      'synthetic-app', 'window_focus' if data['action'] == 'focus' else 'ui_action',
                      data['action'], role + '-' + data['control_id'],
                      metadata={'control_role': role, 'category': 'laboratory',
                                'source_sequence': data['sequence']})
        event.validate()
        if len(self.events) >= self.capacity:
            self.dropped += 1
            self.flow['overflow'] += 1
            return
        self.events.append(event)
        self.flow['accepted'] += 1

    def drain(self, limit=100):
        with self.lock:
            if not self.alive() or not self.enabled:
                self._clear()
                return []
            events = [self.events.popleft() for _ in range(min(limit, len(self.events)))]
            self.flow['drained'] += len(events)
            return events

    def check_health(self):
        with self.lock:
            if not self.alive():
                return False
            if self.ready and self.pending_ack_at is not None and self.monotonic() - self.pending_ack_at > 3:
                self.stop('command_timeout')
            elif self.monotonic() - self.last_received > 5:
                self.stop('backend_timeout')
            return not self.stopped
