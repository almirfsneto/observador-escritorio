"""Unattended native lifecycle tests; protocol-test mode never registers UIA."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
import sys
import time
import unittest

from observador.native_session import NativeSession, creation_ticks


@unittest.skipUnless(sys.platform == 'win32', 'Native lifecycle requires Windows')
class NativeProtocolTest(unittest.TestCase):
    def setUp(self):
        self.executable = (Path(__file__).resolve().parents[1] / 'tools' / 'WindowsObserver'
                           / 'bin' / 'Release' / 'net8.0-windows' / 'WindowsObserver.exe')
        self.fixture = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(40)'])
        self.session = None

    def tearDown(self):
        if self.session:
            self.session.close()
        if self.fixture.poll() is None:
            self.fixture.terminate()
        self.fixture.wait(timeout=3)

    def wait_for(self, predicate, timeout=8):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(.01)
        self.fail('Native protocol deadline exceeded')

    def launch(self, seconds=15):
        self.session = NativeSession(self.fixture, sys.executable,
                                     datetime.now(timezone.utc) + timedelta(seconds=seconds),
                                     executable=self.executable, protocol_test=True)
        self.wait_for(lambda: self.session.stream.ready or self.session.stream.stopped)
        self.assertTrue(self.session.stream.ready)
        return self.session

    def test_ready_burst_pause_resume_and_clean_stop(self):
        session = self.launch()
        session.set_active(True)
        self.wait_for(lambda: len(session.stream.events) > 0)
        self.assertLessEqual(len(session.stream.events), session.stream.capacity)
        session.set_active(False)
        self.assertEqual(session.stream.drain(), [])
        self.wait_for(lambda: session.stream.health == 'paused')
        session.set_active(True)
        self.wait_for(lambda: len(session.stream.events) > 0)
        self.assertTrue(all(event.action == 'invoke' for event in session.stream.drain()))
        session.close()
        session.close()
        self.assertIsNotNone(session.process.poll())
        self.assertFalse(session.reader.is_alive())
        self.assertFalse(session.writer.is_alive())

    def test_native_expires_without_controller_commands(self):
        # Keep stdin open and do not create NativeSession: its own expiry/kill
        # fallback must not mask a broken native watchdog or observation deadline.
        process = subprocess.Popen([str(self.executable), '--protocol-test', str(self.fixture.pid),
                                    sys.executable, str(creation_ticks(self.fixture.pid)),
                                    (datetime.now(timezone.utc) + timedelta(seconds=6)).isoformat()],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        try:
            code = process.wait(timeout=10)
            # The native watchdog intentionally uses TerminateProcess after its
            # teardown grace. Both bounded native paths satisfy expiry; Python
            # never kills the provider before this assertion.
            self.assertIn(code, (0, 4294967295))
            print('NATIVE_EXPIRY_EXIT', code)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=3)
            process.stdin.close()
            process.stdout.close()

    def test_rejects_different_creation_time(self):
        result = subprocess.run([str(self.executable), '--protocol-test', str(self.fixture.pid),
                                 sys.executable, str(creation_ticks(self.fixture.pid) + 1),
                                 (datetime.now(timezone.utc) + timedelta(seconds=10)).isoformat()],
                                input='', text=True, capture_output=True, timeout=8)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, '')

    def test_eof_from_dead_controller_stops_provider(self):
        process = subprocess.Popen([str(self.executable), '--protocol-test', str(self.fixture.pid),
                                    sys.executable, str(creation_ticks(self.fixture.pid)),
                                    (datetime.now(timezone.utc) + timedelta(seconds=10)).isoformat()],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        try:
            process.stdin.close()
            code = process.wait(timeout=8)
            self.assertIn(code, (0, 4294967295))
            print('NATIVE_EOF_EXIT', code)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=3)
            process.stdout.close()
