from dataclasses import replace
from datetime import datetime, time, timedelta, timezone
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from observador.collector import Application, Collector, Observation, Policy
from observador.store import EventStore
from observador.windows import WindowsBackend


class CollectorTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 3, 10, tzinfo=timezone(timedelta(hours=-3)))
        self.apps = (Application(r'C:\Lab\Synthetic.exe', 'synthetic-app'),)
        self.policy = Policy(self.apps, self.now - timedelta(days=1),
                             self.now + timedelta(days=1), laboratory_enabled=True)
        self.backend = Mock()
        self.backend.observe.return_value = Observation(0, 50000, False)
        self.collector = Collector(self.policy, self.backend, 'lab-device', lambda: self.now)

    def test_defaults_do_not_consult_backend(self):
        for policy in [replace(self.policy, laboratory_enabled=False),
                       replace(self.policy, applications=()),
                       replace(self.policy, starts_at=self.now + timedelta(hours=1)),
                       replace(self.policy, work_start=time(11))]:
            self.assertIsNone(Collector(policy, self.backend, 'lab', lambda: self.now).poll())
        self.backend.observe.assert_not_called()

    def test_pause_stop_and_expiry(self):
        self.collector.pause()
        self.assertIsNone(self.collector.poll())
        self.backend.observe.assert_not_called()
        self.collector.resume()
        self.assertIsNotNone(self.collector.poll())
        self.now = self.policy.expires_at
        self.assertIsNone(self.collector.poll())
        self.collector.resume()
        self.now -= timedelta(hours=1)
        self.assertIsNone(self.collector.poll())
        self.assertEqual(self.backend.observe.call_count, 1)
        self.assertEqual(self.collector.health, 'stopped')

    def test_recheck_expiry_after_slow_backend(self):
        def delayed(_):
            self.now = self.policy.expires_at
            return Observation(0, 50000, False)
        self.backend.observe.side_effect = delayed
        self.assertIsNone(self.collector.poll())
        self.assertEqual(self.collector.health, 'stopped')

    def test_work_hours_use_local_timezone_and_end_is_exclusive(self):
        self.now = self.now.replace(hour=18)
        self.assertIsNone(self.collector.poll())
        self.backend.observe.assert_not_called()
        self.now = self.now.replace(hour=9)
        self.assertIsNotNone(self.collector.poll())

    def test_sensitive_denied_and_invalid_observations(self):
        for observation in [None, Observation(0, 50004, True),
                            Observation(-1, 50000, False), Observation(1, 50000, False),
                            Observation(True, 50000, False), Observation(0, 50000, None)]:
            self.backend.observe.return_value = observation
            self.assertIsNone(self.collector.poll())

    def test_no_values_and_sqlite_roundtrip(self):
        event = self.collector.poll()
        self.assertEqual(event.action, 'focus')
        self.assertEqual(event.target, 'button')
        self.assertNotIn('Synthetic.exe', json.dumps(event.to_dict()))
        self.assertIsNone(self.collector.poll())
        with tempfile.TemporaryDirectory() as directory:
            store = EventStore(Path(directory) / 'lab.sqlite3')
            try:
                store.insert(event)
                self.assertEqual(store.list_events(), [event])
            finally:
                store.close()

    def test_errors_do_not_leak_exception_messages(self):
        self.backend.observe.side_effect = OSError('SECRET window title')
        self.assertIsNone(self.collector.poll())
        self.assertEqual(self.collector.health, 'backend_error')
        self.backend.observe.side_effect = None
        self.assertIsNotNone(self.collector.poll())

    def test_invalid_configurations(self):
        with self.assertRaises(ValueError):
            Application('Synthetic.exe', 'lab')
        with self.assertRaises(ValueError):
            replace(self.policy, expires_at=self.policy.starts_at)
        with self.assertRaises(ValueError):
            replace(self.policy, applications=self.apps * 2)
        with self.assertRaises(ValueError):
            replace(self.policy, starts_at=datetime(2026, 11, 3))
        with self.assertRaises(ValueError):
            replace(self.policy, work_start=time(18), work_end=time(9))


class WindowsBridgeTest(unittest.TestCase):
    def test_empty_allowlist_never_launches_process(self):
        with patch('observador.windows.subprocess.run') as run:
            self.assertIsNone(WindowsBackend().observe(()))
            run.assert_not_called()

    def test_bridge_contract_without_windows(self):
        app = Application(r'C:\Lab\Synthetic.exe', 'lab')
        result = subprocess.CompletedProcess([], 0, '{"index":0,"role":50000,"password":false}', '')
        with patch('observador.windows.sys.platform', 'win32'), \
             patch.dict('os.environ', {'SystemRoot': r'C:\Windows'}), \
             patch('observador.windows.subprocess.CREATE_NO_WINDOW', 0, create=True), \
             patch('observador.windows.subprocess.run', return_value=result) as run:
            self.assertEqual(WindowsBackend().observe((app,)), Observation(0, 50000, False))
            self.assertEqual(json.loads(run.call_args.kwargs['input']), [app.executable])
            self.assertEqual(run.call_args.kwargs['timeout'], 8)
            self.assertNotIn('shell', run.call_args.kwargs)
            for output in ['null', '{"index":0,"role":50000,"password":false,"value":"secret"}',
                           '{"index":0,"role":50000,"password":"false"}']:
                result.stdout = output
                if output == 'null':
                    self.assertIsNone(WindowsBackend().observe((app,)))
                else:
                    with self.assertRaises(ValueError):
                        WindowsBackend().observe((app,))
