from types import SimpleNamespace
from datetime import datetime, timedelta, timezone
import unittest
from observador.acceptance_metrics import OwnedSampler
from observador.acceptance_report import empty_session
from observador.acceptance_session import SessionRecorder, termination_for_stop
from observador.stream import LabStream


class MetricsTest(unittest.TestCase):
    def test_stop_reason_distinguishes_exit_backend_and_both_expiry_clocks(self):
        now = [datetime(2026, 11, 3, tzinfo=timezone.utc)]
        elapsed = [0.0]
        stream = LabStream(now[0] + timedelta(minutes=15), clock=lambda: now[0], monotonic=lambda: elapsed[0])
        fixture = SimpleNamespace(poll=lambda: None)
        session = SimpleNamespace(stream=stream)
        self.assertEqual(termination_for_stop(fixture, None), 'not_started')
        self.assertEqual(termination_for_stop(fixture, session), 'operator_stop')
        stream.stop('backend_timeout')
        self.assertEqual(termination_for_stop(fixture, session), 'backend_error')
        elapsed[0] = 900
        now[0] -= timedelta(hours=1)  # Monotonic expiry survives a backwards wall clock.
        self.assertEqual(termination_for_stop(fixture, session), 'expired')
        elapsed[0] = 0
        now[0] = stream.expires_at
        self.assertEqual(termination_for_stop(fixture, session), 'expired')
        fixture.poll = lambda: 0
        self.assertEqual(termination_for_stop(fixture, session), 'fixture_exit')

    def test_samples_only_registered_handles_and_cpu_is_delta_not_machine_enumeration(self):
        opened = []
        class Probe:
            def __init__(self, pid):
                opened.append(pid)
                self.calls = 0
                self.closed = False
            def read(self):
                self.calls += 1
                return 42, self.calls * .1, self.calls * 1024, self.calls * 2048
            def close(self):
                self.closed = True
        elapsed = [10.0]
        data = empty_session()
        sampler = OwnedSampler(data, probe_factory=Probe, clock=lambda: elapsed[0])
        sampler.register('fixture', SimpleNamespace(pid=123, poll=lambda: None))
        elapsed[0] += .5
        sampler.sample()
        metric = data['metrics']['processes']['fixture']
        self.assertEqual(opened, [123])
        self.assertAlmostEqual(metric['cpu_single_core_sample_peak_percent'], 20)
        self.assertEqual(metric['ram_working_set_sample_peak_bytes'], 2048)
        self.assertEqual(metric['samples'], 2)
        self.assertEqual(data['metrics']['processes']['provider']['availability'], 'not_sampled')
        sampler.close()

    def test_access_failure_is_a_gap_not_fabricated_zero(self):
        def denied(_):
            raise OSError('SECRET user path')
        data = empty_session()
        sampler = OwnedSampler(data, probe_factory=denied)
        sampler.register('fixture', SimpleNamespace(pid=123, poll=lambda: None))
        self.assertEqual(data['metrics']['processes']['fixture']['availability'], 'unavailable')
        self.assertIsNone(data['metrics']['processes']['fixture']['cpu_single_core_sample_peak_percent'])
        sampler.close()

    def test_ack_latency_requires_matching_generation_and_active_ack(self):
        elapsed = [0.0]
        recorder = SessionRecorder(clock=lambda: elapsed[0])
        stream = SimpleNamespace(health='starting', generation=1, stopped=False, pending_ack_at=0,
                                 native_dropped=0, dropped=0, sequence_gaps=0, invalid=0)
        recorder.request_start()
        recorder.observe(stream)
        self.assertIsNone(recorder.data['metrics']['start_to_active_ack_ms'])
        elapsed[0] = .25
        stream.health, stream.pending_ack_at = 'active', None
        recorder.observe(stream)
        self.assertEqual(recorder.data['metrics']['start_to_active_ack_ms'], 250)
        recorder.request_pause(2)
        elapsed[0] += .1
        stream.generation, stream.health = 2, 'paused'
        recorder.observe(stream)
        self.assertAlmostEqual(recorder.data['metrics']['pause_ack_peak_ms'], 100)
        recorder.request_pause(3)
        stream.generation = 4
        recorder.observe(stream)
        self.assertEqual(recorder.data['metrics']['pause_unconfirmed'], 1)
