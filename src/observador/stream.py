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
        self.invalid = 0
        self.last_sequence = 0
        self.sequence_gaps = 0
        self.session = str(uuid4())
        self.started_at = utc(clock())
        self.last_received = monotonic()
        self.last_focus = None
        self.protocol_failure = None
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
            self.events.clear()
            self.last_focus = None
            self.last_sequence = 0
            self.health = 'starting' if active else 'paused'
            return {'command': 'start' if active else 'pause', 'generation': self.generation}

    def stop(self, reason='stopped'):
        with self.lock:
            self.stopped = True
            self.enabled = False
            self.events.clear()
            self.health = reason

    def receive(self, line):
        with self.lock:
            if not self.alive():
                return
            try:
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
                elif kind == 'health' and set(data) == {'kind', 'generation', 'dropped', 'callbacks'}:
                    if (type(data['dropped']) is not int or data['dropped'] < 0
                            or type(data['generation']) is not int):
                        raise ValueError()
                    counters = data['callbacks']
                    if (not isinstance(counters, dict) or set(counters) != {'focus', 'invoke', 'toggle', 'excluded', 'errors'}
                            or any(type(value) is not int or value < 0 for value in counters.values())):
                        raise ValueError()
                    self.native_callbacks = counters
                    self.native_dropped = max(self.native_dropped, data['dropped'])
                elif kind == 'ack' and set(data) == {'kind', 'generation', 'active'}:
                    if type(data['active']) is not bool or type(data['generation']) is not int:
                        raise ValueError()
                    if data['generation'] == self.generation:
                        if data['active'] != self.enabled:
                            raise ValueError()
                        self.health = 'active' if self.enabled else 'paused'
                elif kind == 'event':
                    self._event(data)
                elif kind == 'error' and set(data) == {'kind', 'code'} and data['code'] in {
                        'invalid_config', 'subscription_failed', 'backend_failure'}:
                    self.stop(data['code'])
                else:
                    raise ValueError()
                self.last_received = self.monotonic()
            except (ValueError, TypeError, KeyError, OverflowError):
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
            return
        self.last_focus = signature if data['action'] == 'focus' else None
        event = Event(1, str(uuid4()), stamp.isoformat(), 'laboratorio-sintetico', self.session,
                      'synthetic-app', 'window_focus' if data['action'] == 'focus' else 'ui_action',
                      data['action'], role + '-' + data['control_id'],
                      metadata={'control_role': role, 'category': 'laboratory'})
        event.validate()
        if len(self.events) >= self.capacity:
            self.dropped += 1
            return
        self.events.append(event)

    def drain(self, limit=100):
        with self.lock:
            if not self.alive() or not self.enabled:
                self.events.clear()
                return []
            return [self.events.popleft() for _ in range(min(limit, len(self.events)))]
