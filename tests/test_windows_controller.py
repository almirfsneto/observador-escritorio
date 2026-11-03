"""Automated real Tk/native lifecycle on Windows, with synthetic data and a temp DB."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from observador.lab_controller import LaboratoryWindow
from observador.native_session import creation_ticks
from observador.lab_queue import LabEventQueue


@unittest.skipUnless(sys.platform == 'win32', 'Windows controller smoke requires Windows')
class ControllerAutomationTest(unittest.TestCase):
    def test_visible_controller_pause_storage_and_owned_process_cleanup(self):
        import tkinter as tk
        root = Path(__file__).resolve().parents[1]
        target = root / 'tools/SyntheticWpfTaskApp/bin/Release/net8.0-windows/SyntheticWpfTaskApp.exe'
        observer = root / 'tools/WindowsObserver/bin/Release/net8.0-windows/WindowsObserver.exe'
        with tempfile.TemporaryDirectory() as temporary:
            database = Path(temporary) / 'events.sqlite3'
            window = LaboratoryWindow(tk, fixture_target=target, observer_target=observer, data_target=database)
            def pump(predicate, timeout=12):
                deadline = time.monotonic() + timeout
                while time.monotonic() < deadline:
                    window.root.update()
                    if predicate():
                        return
                    time.sleep(.01)
                self.fail('Controller lifecycle deadline exceeded')
            try:
                window.root.update()
                self.assertIsNone(window.session)
                self.assertFalse(window.persist.get())
                window.launch_btn.invoke()
                self.assertIsNone(window.session, 'Opening fixture must not start observation')
                self.assertIsNotNone(window.fixture)
                def exercise(phase):
                    process = subprocess.Popen(
                        ['powershell.exe', '-NoProfile', '-NonInteractive', '-File',
                         str(root / 'tools/exercise_fixture.ps1'), '-TargetPid', str(window.fixture.pid),
                         '-StartTicks', str(creation_ticks(window.fixture.pid)), '-TargetPath', str(target),
                         '-Phase', phase], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    try:
                        # Foreground activation sends window messages to Tk too:
                        # waiting synchronously here would freeze the test's own UI.
                        pump(lambda: process.poll() is not None, timeout=15)
                        output, _ = process.communicate(timeout=2)
                        self.assertEqual(process.returncode, 0, 'Synthetic GUI exercise failed')
                    finally:
                        if process.poll() is None:
                            process.kill()
                            process.wait(timeout=3)
                        process.stdout.close()
                        process.stderr.close()
                    data = json.loads(output)
                    if data['status'] == 'blocked':
                        self.skipTest('Hosted foreground desktop unavailable; manual controller validation required')
                    self.assertEqual(data['status'], 'ok')
                exercise('probe')
                window.persist.set(True)
                window.start_btn.invoke()
                pump(lambda: window.session is not None and window.session.stream.health == 'active')
                exercise('burst')
                pump(lambda: window.event_count >= 30 and window.sink.written >= 30)
                window.pause_btn.invoke()
                self.assertFalse(window.session.stream.enabled)
                pump(lambda: window.session.stream.health == 'paused')
                paused_count = window.event_count
                exercise('burst')
                for _ in range(10):
                    window.root.update()
                    time.sleep(.02)
                self.assertEqual(window.event_count, paused_count)
                window.pause_btn.invoke()
                pump(lambda: window.session.stream.health == 'active')
                for _ in range(250):
                    window.append('linha ficticia de teste')
                self.assertLessEqual(int(window.log.index('end-1c').split('.')[0]), 200)
                window.stop_btn.invoke()
                pump(lambda: window.cleanup is not None and not window.cleanup.is_alive())
                self.assertTrue(window.finished)
                self.assertIsNotNone(window.session.process.poll())
                self.assertIsNotNone(window.fixture.poll())
                self.assertFalse(window.sink.worker.is_alive())
                self.assertEqual(window.sink.discarded, 0)
                store = LabEventQueue(database)
                try:
                    saved = store.list_events()
                    self.assertEqual(len(saved), window.sink.written)
                    self.assertEqual(sum(event.action == 'invoke' for event in saved), 30,
                                     'All thirty actions must survive the visible UI and async writer')
                finally:
                    store.close()
                print('SYNTHETIC_CONTROLLER_COUNTS', json.dumps({
                    'timeline': window.event_count, 'written': window.sink.written,
                    'discarded': window.sink.discarded, 'children_stopped': True}))
            finally:
                window.stop()
                if window.cleanup:
                    window.cleanup.join(timeout=7)
                window.root.destroy()
