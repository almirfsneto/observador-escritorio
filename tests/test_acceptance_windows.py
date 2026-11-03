"""Real Windows acceptance-launcher checks. Automated origin can never become human acceptance."""
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest

from observador.acceptance_prepare import Preparation, artifact_hashes
from observador.acceptance_report import new_report, validate_report
from observador.acceptance_wizard import AcceptanceWizard
from windows_support import prepare_foreground


@unittest.skipUnless(sys.platform == 'win32', 'Windows acceptance integration requires Windows')
class WindowsAcceptanceTest(unittest.TestCase):
    def test_real_offline_preparation_builds_and_hashes_without_installation(self):
        root = Path(__file__).resolve().parents[1]
        report = new_report('automated_test')
        prep = Preparation(root, report)
        try:
            prep.prepare()
            self.assertTrue(prep.ready)
            self.assertTrue(prep.verify_artifacts())
            self.assertEqual(report['checks']['offline_build'], 'PASSOU')
            self.assertTrue(all(result['status'] == 'NAO_EXECUTADO' for result in report['manual_checks'].values()))
        finally:
            prep.runner.cancel()

    def test_guided_window_samples_owned_processes_and_exports_without_raw_data(self):
        import tkinter as tk
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            wizard = AcceptanceWizard(tk, root, destination=Path(temporary) / 'reports', origin='automated_test')
            def pump(predicate, timeout=12):
                deadline = time.monotonic() + timeout
                while time.monotonic() < deadline:
                    wizard.root.update()
                    if predicate():
                        return
                    time.sleep(.01)
                self.fail('Acceptance UI deadline exceeded')
            try:
                wizard.root.update()
                self.assertEqual(wizard.labs, [])
                self.assertTrue(all(result['status'] == 'NAO_EXECUTADO' for result in wizard.report['manual_checks'].values()))
                # This test injects proven test prerequisites, not a human result.
                wizard.preparation.ready = True
                wizard.report['artifacts'] = artifact_hashes(root)
                wizard.report['automated_tests'] = {'status': 'PASSOU', 'discovered': 1, 'skipped': 0, 'failures': 0, 'errors': 0}
                wizard.open_lab()
                lab = wizard.labs[0]
                self.assertIsNone(lab.session)
                self.assertFalse(lab.persist.get())
                lab.launch_btn.invoke()
                self.assertIsNone(lab.session)
                if not prepare_foreground(lab.fixture, tick=wizard.root.update):
                    self.skipTest('Hosted foreground unavailable; manual Windows 10/11 trial still required')
                lab.start_btn.invoke()
                pump(lambda: lab.session and lab.session.stream.health == 'active')
                lab.secondary_btn.invoke()
                self.assertIsNotNone(lab.secondary)
                lab.pause_btn.invoke()
                pump(lambda: lab.session.stream.health == 'paused')
                self.assertGreaterEqual(lab.recorder.data['metrics']['pause_ack_samples'], 1)
                lab.stop_btn.invoke()
                pump(lambda: lab.cleanup and not lab.cleanup.is_alive())
                lab.close()
                wizard.root.update()
                wizard.export()
                reports = list((Path(temporary) / 'reports').glob('aceite-*.json'))
                self.assertEqual(len(reports), 1)
                report = json.loads(reports[0].read_text(encoding='utf-8'))
                validate_report(report)
                self.assertEqual(report['origin'], 'automated_test')
                self.assertEqual(report['human_gate'], 'PENDENTE_REVISAO_HUMANA')
                self.assertFalse(report['pilot_authorized'])
                data = report['sessions'][0]
                self.assertTrue(data['children_stopped'])
                for role in ('controller', 'fixture', 'provider', 'fixture_secondary'):
                    metric = data['metrics']['processes'][role]
                    self.assertEqual(metric['availability'], 'sampled')
                    self.assertGreater(metric['samples'], 0)
                self.assertNotIn(str(root), reports[0].read_text(encoding='utf-8'))
                self.assertNotIn('"pid"', json.dumps(report['sessions'][0]['metrics']))
                print('ACCEPTANCE_REPORT_VERIFIED', json.dumps({'sessions': len(report['sessions']),
                      'children_stopped': data['children_stopped'], 'human_gate': report['human_gate']}))
            finally:
                wizard.close()
                pump(lambda: not wizard.active_lab() and not (wizard.worker and wizard.worker.is_alive()))
