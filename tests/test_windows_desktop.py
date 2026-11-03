"""Automated hosted-desktop exercise. A skip is evidence of unavailable desktop, not a pass."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import time
import unittest

from observador.native_session import NativeSession


@unittest.skipUnless(sys.platform == 'win32', 'Windows desktop automation requires Windows')
class DesktopAutomationTest(unittest.TestCase):
    def test_synthetic_invokes_and_password_exclusion(self):
        root = Path(__file__).resolve().parents[1]
        target = root / 'tools/SyntheticTaskApp/bin/Release/net8.0-windows/SyntheticTaskApp.exe'
        observer = root / 'tools/WindowsObserver/bin/Release/net8.0-windows/WindowsObserver.exe'
        fixture = subprocess.Popen([str(target)])
        session = None
        try:
            time.sleep(1)
            session = NativeSession(fixture, target, datetime.now(timezone.utc) + timedelta(seconds=40),
                                    executable=observer)
            deadline = time.monotonic() + 8
            while not session.stream.ready and not session.stream.stopped and time.monotonic() < deadline:
                time.sleep(.02)
            self.assertTrue(session.stream.ready, 'Native UIA subscription failed')
            session.set_active(True)
            def exercise(phase):
                result = subprocess.run(
                    ['powershell.exe', '-NoProfile', '-NonInteractive', '-File',
                     str(root / 'tools/exercise_fixture.ps1'), '-TargetPid', str(fixture.pid),
                     '-StartTicks', str(session.expected_ticks), '-TargetPath', str(target), '-Phase', phase],
                    text=True, capture_output=True, timeout=15)
                self.assertEqual(result.returncode, 0, 'Synthetic UI exercise failed')
                data = json.loads(result.stdout)
                if data['status'] == 'blocked':
                    self.skipTest('Hosted runner has no usable foreground desktop; manual Windows validation required')
                self.assertEqual(data['status'], 'ok')
            exercise('burst')
            time.sleep(.5)
            self.assertFalse(session.stream.stopped, (session.stream.health, session.stream.protocol_failure))
            events = session.stream.drain(limit=256)
            invokes = [event for event in events if event.action == 'invoke']
            self.assertGreaterEqual(len(invokes), 20, 'Rapid synthetic invokes were lost')
            self.assertGreaterEqual(len({event.target for event in invokes}), 2)
            print('SYNTHETIC_UIA_COUNTS', json.dumps({'invokes': len(invokes),
                  'distinct_controls': len({event.target for event in invokes}),
                  'native_dropped': session.stream.native_dropped, 'python_dropped': session.stream.dropped}))
            self.assertNotIn('PROCESSO-FICTICIO', json.dumps([event.to_dict() for event in events]))
            self.assertNotIn('SENHA-FICTICIA', json.dumps([event.to_dict() for event in events]))
            exercise('password')
            time.sleep(.5)
            self.assertEqual(session.stream.drain(), [], 'Password focus must never be emitted')
        finally:
            if session:
                session.close()
            if fixture.poll() is None:
                fixture.terminate()
            fixture.wait(timeout=3)
