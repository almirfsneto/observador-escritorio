from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
import unittest

from observador.native_session import NativeSession, creation_ticks
from windows_support import prepare_foreground


@unittest.skipUnless(sys.platform == 'win32', 'Native comparative coverage requires Windows desktop')
class ComparativeCoverageTest(unittest.TestCase):
    def test_wpf_winforms_uia_and_process_scoped_winevent_probe(self):
        root = Path(__file__).resolve().parents[1]
        observer = root/'tools/WindowsObserver/bin/Release/net8.0-windows/WindowsObserver.exe'
        results = {}
        for project in ('SyntheticWpfTaskApp', 'SyntheticTaskApp'):
            target = root/f'tools/{project}/bin/Release/net8.0-windows/{project}.exe'
            fixture = subprocess.Popen([str(target)])
            session = probe = None
            try:
                if not prepare_foreground(fixture):
                    self.skipTest('Foreground unavailable; no comparative desktop coverage proved')
                expires = datetime.now(timezone.utc)+timedelta(seconds=35)
                session = NativeSession(fixture, target, expires, executable=observer)
                session.set_active(True)
                deadline = time.monotonic()+8
                while session.stream.health != 'active' and not session.stream.stopped and time.monotonic()<deadline:
                    time.sleep(.02)
                self.assertEqual(session.stream.health, 'active')
                probe = subprocess.Popen([str(observer), '--coverage-probe', str(fixture.pid), str(target),
                                         str(creation_ticks(fixture.pid)), expires.isoformat()],
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                        text=True, encoding='utf-8')
                ready = queue.Queue()
                reader = threading.Thread(target=lambda: ready.put(probe.stdout.readline()), daemon=True)
                reader.start()
                self.assertEqual(json.loads(ready.get(timeout=8)), {'kind':'coverage_ready'})
                reader.join(timeout=1)
                started = time.monotonic()
                exercise = subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-File',str(root/'tools/exercise_fixture.ps1'),
                                          '-TargetPid',str(fixture.pid),'-StartTicks',str(creation_ticks(fixture.pid)),
                                          '-TargetPath',str(target),'-Phase','burst'], capture_output=True, text=True, timeout=15)
                self.assertEqual(exercise.returncode, 0, 'Synthetic comparative exercise failed')
                self.assertEqual(json.loads(exercise.stdout)['status'], 'ok')
                time.sleep(.3)
                events = session.stream.drain(limit=256)
                output, _ = probe.communicate('stop\n', timeout=5)
                diagnostic = json.loads(output)
                self.assertEqual(probe.returncode, 0)
                self.assertEqual(diagnostic['kind'], 'coverage_result')
                if diagnostic['invoked'] + diagnostic['state_changes'] == 0:
                    self.assertIsNone(diagnostic['callback_delivery_peak_ms'])
                invokes = [event for event in events if event.action == 'invoke']
                if project == 'SyntheticWpfTaskApp':
                    self.assertEqual(len(invokes), 30)
                self.assertLessEqual(len(invokes), 30)
                session.set_active(False)
                deadline = time.monotonic()+4
                while session.stream.health != 'paused' and time.monotonic()<deadline:
                    time.sleep(.02)
                self.assertEqual(session.stream.health, 'paused')
                self.assertEqual(session.stream.drain(), [])
                results['wpf' if project == 'SyntheticWpfTaskApp' else 'winforms'] = {
                    'stimulated':30, 'uia_invokes':len(invokes), 'distinct_uia_controls':len({event.target for event in invokes}),
                    'native_dropped':session.stream.native_dropped, 'python_dropped':session.stream.dropped,
                    'exercise_elapsed_ms':round((time.monotonic()-started)*1000), 'winevent':diagnostic}
            finally:
                if probe:
                    if probe.poll() is None:
                        probe.kill()
                    probe.communicate(timeout=3)
                if session:
                    session.close()
                if fixture.poll() is None:
                    fixture.terminate()
                fixture.wait(timeout=3)
        print('SYNTHETIC_COMPARATIVE_COVERAGE', json.dumps(results))
