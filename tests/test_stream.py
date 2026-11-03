from datetime import datetime, timedelta, timezone
import json
import unittest

from observador.stream import LabStream
from observador.discovery import discover_patterns


class StreamTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)
        self.elapsed = 10
        self.stream = LabStream(self.now + timedelta(minutes=15), clock=lambda: self.now,
                                monotonic=lambda: self.elapsed, capacity=4)
        self.send(kind='ready', pid=123, start_ticks=456)
        self.stream.command(True)

    def send(self, **data):
        self.stream.receive(json.dumps(data))

    def event(self, sequence=1, action='invoke', control_id='0000000000000001', **extra):
        data = dict(kind='event', generation=self.stream.generation, sequence=sequence,
                    timestamp_utc=self.now.isoformat(), action=action, role=50000, control_id=control_id)
        data.update(extra)
        self.send(**data)

    def test_repeated_actions_are_not_deduplicated(self):
        self.event(1)
        self.event(2)
        self.assertEqual(len(self.stream.drain()), 2)

    def test_focus_distinguishes_two_buttons_and_suppresses_same_focus(self):
        self.event(1, action='focus')
        self.event(2, action='focus')
        self.event(3, action='focus', control_id='0000000000000002')
        self.assertEqual(len(self.stream.drain()), 2)

    def test_pause_resume_discards_queued_and_inflight_generation(self):
        self.event()
        old = self.stream.generation
        self.stream.command(False)
        self.assertEqual(self.stream.drain(), [])
        self.stream.command(True)
        self.event(2, generation=old)
        self.assertEqual(self.stream.drain(), [])
        self.event(3)
        self.assertEqual(len(self.stream.drain()), 1)

    def test_pause_is_confirmed_only_by_matching_ack_and_missing_ack_stops(self):
        self.stream.command(False)
        self.assertEqual(self.stream.health, 'pausing')
        self.send(kind='ack', generation=self.stream.generation - 1, active=False)
        self.assertEqual(self.stream.health, 'pausing')
        self.send(kind='ack', generation=self.stream.generation, active=False)
        self.assertEqual(self.stream.health, 'paused')
        self.stream.command(True)
        self.elapsed += 4
        self.assertFalse(self.stream.check_health())
        self.assertEqual(self.stream.health, 'command_timeout')

    def test_command_sent_before_readiness_gets_ack_budget_after_handshake(self):
        stream = LabStream(self.now + timedelta(minutes=15), clock=lambda: self.now,
                           monotonic=lambda: self.elapsed)
        stream.command(True)
        self.elapsed += 4
        stream.receive(json.dumps({'kind': 'ready', 'pid': 123, 'start_ticks': 456}))
        self.assertTrue(stream.check_health())
        self.elapsed += 4
        self.assertFalse(stream.check_health())

    def test_burst_is_bounded_and_reports_loss(self):
        for i in range(1, 1001):
            self.event(i)
        self.assertEqual(len(self.stream.events), 4)
        self.assertEqual(self.stream.dropped, 996)
        self.assertEqual(len(self.stream.drain()), 4)

    def test_monotonic_expiry_even_if_wall_clock_rolls_back(self):
        self.now -= timedelta(hours=1)
        self.elapsed += 901
        self.assertFalse(self.stream.alive())
        self.assertIsNone(self.stream.command(True))

    def test_native_expiry_and_stop_are_permanent(self):
        self.now += timedelta(minutes=15)
        self.assertEqual(self.stream.drain(), [])
        self.now -= timedelta(minutes=10)
        self.assertIsNone(self.stream.command(True))

    def test_raw_fields_or_unknown_commands_fail_closed(self):
        self.event(value='SENHA-FICTICIA-NAO-COLETAR')
        self.assertTrue(self.stream.stopped)
        self.assertEqual(self.stream.health, 'protocol_error')
        self.assertEqual(self.stream.drain(), [])

    def test_invalid_timestamp_type_fails_closed(self):
        self.event(timestamp_utc=None)
        self.assertTrue(self.stream.stopped)

    def test_bounded_windows_clock_resolution_tolerance(self):
        self.event(timestamp_utc=(self.now + timedelta(milliseconds=15)).isoformat())
        self.assertEqual(len(self.stream.drain()), 1)
        self.event(2, timestamp_utc=(self.now + timedelta(seconds=1)).isoformat())
        self.assertTrue(self.stream.stopped)
        self.assertEqual(self.stream.protocol_failure, 'timestamp')

    def test_reordered_sequence_fails_closed_and_gap_reported(self):
        self.event(1)
        self.event(4)
        self.assertEqual(self.stream.sequence_gaps, 2)
        self.event(3)
        self.assertEqual(self.stream.health, 'protocol_error')

    def test_rapid_microtask_pattern_keeps_control_identity(self):
        self.stream.capacity = 100
        for repetition in range(6):
            for step in range(2):
                self.now += timedelta(milliseconds=20)
                self.event(repetition * 2 + step + 1, control_id=f'{step + 1:016x}')
        events = self.stream.drain()
        patterns = discover_patterns(events, min_count=3, max_steps=2)
        self.assertTrue(any(p['occurrences'] == 6 and p['median_duration_seconds'] == .02 for p in patterns))
        self.assertNotIn('SENHA', json.dumps([event.to_dict() for event in events]))


if __name__ == '__main__':
    unittest.main()
