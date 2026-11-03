from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from observador.acceptance_report import (MANUAL_STEPS, REPORT_SCHEMA, ReportError, empty_session,
    finalize_report, new_report, validate_report, write_report)


class AcceptanceReportTest(unittest.TestCase):
    def test_empty_report_is_explicitly_unexecuted_and_never_authorizes_pilot(self):
        schema_path = Path(__file__).resolve().parents[1] / 'docs/ACEITE_REPORT_SCHEMA.json'
        self.assertEqual(json.loads(schema_path.read_text(encoding='utf-8')), REPORT_SCHEMA)
        report = finalize_report(new_report())
        self.assertFalse(report['pilot_authorized'])
        self.assertEqual(report['human_gate'], 'PENDENTE_REVISAO_HUMANA')
        self.assertTrue(all(item['status'] == 'NAO_EXECUTADO' for item in report['manual_checks'].values()))
        self.assertIn('commit_unavailable', report['gaps'])
        self.assertIn('preparation_incomplete', report['gaps'])

    def test_manual_passes_are_self_reports_not_automatic_acceptance(self):
        report = new_report('automated_test')
        for key in MANUAL_STEPS:
            report['manual_checks'][key] = {'status': 'PASSOU', 'observation': 'SEM_ANOMALIA'}
        result = finalize_report(report)
        self.assertEqual(result['origin'], 'automated_test')
        self.assertFalse(result['pilot_authorized'])
        self.assertEqual(result['human_gate'], 'PENDENTE_REVISAO_HUMANA')

    def test_rejects_forbidden_data_everywhere_without_echoing_values(self):
        secret = r'Alice CPF 123.456.789-00 C:\Clientes\Segredo host-escritorio 10.1.2.3'
        cases = []
        for key in ('hostname', 'username', 'ip', 'window_title', 'password', 'screenshot', 'path'):
            report = new_report()
            report[key] = secret
            cases.append(report)
        report = new_report()
        report['manual_checks']['senha']['observation'] = secret
        cases.append(report)
        report = new_report()
        report['environment']['os_edition'] = secret
        cases.append(report)
        report = new_report()
        report['source']['commit'] = secret
        cases.append(report)
        report = new_report()
        report['sessions'] = [empty_session()]
        report['sessions'][0]['metrics']['processes']['controller']['pid'] = 123
        cases.append(report)
        for report in cases:
            with self.assertRaises(ReportError) as error:
                finalize_report(report)
            self.assertNotIn(secret, str(error.exception))

    def test_rejects_nan_boolean_counters_and_unproven_success(self):
        for value in (float('nan'), float('inf'), -1, True, '123', 10**500):
            report = new_report()
            report['sessions'] = [empty_session()]
            report['sessions'][0]['metrics']['pause_ack_peak_ms'] = value
            with self.assertRaises(ReportError):
                finalize_report(report)
        report = new_report()
        report['automated_tests']['status'] = 'PASSOU'
        with self.assertRaises(ReportError):
            finalize_report(report)
        report = new_report()
        report['checks']['artifact_hashes'] = 'PASSOU'
        with self.assertRaises(ReportError):
            finalize_report(report)

    def test_no_files_written_for_invalid_report_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'repository'
            root.mkdir()
            outside = Path(temporary) / 'results'
            report = new_report()
            report['hostname'] = 'fictitious-host'
            with self.assertRaises(ReportError):
                write_report(report, root, outside)
            self.assertFalse(outside.exists())
            report = new_report()
            path = write_report(report, root, outside)
            saved = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(saved, finalize_report(report))
            with self.assertRaises(FileExistsError):
                write_report(report, root, outside)

    def test_refuses_repository_other_git_roots_and_symlink_destinations(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'repository'
            root.mkdir()
            (root / '.git').mkdir()
            for output in (root, root / 'reports'):
                with self.assertRaises(ReportError):
                    write_report(new_report(), root, output)
            other = Path(temporary) / 'other'
            other.mkdir()
            (other / '.git').mkdir()
            with self.assertRaises(ReportError):
                write_report(new_report(), root, other / 'results')

    def test_session_not_started_cannot_claim_events(self):
        report = new_report()
        report['sessions'] = [empty_session()]
        report['sessions'][0]['counters']['events_accepted'] = 1
        with self.assertRaises(ReportError):
            validate_report(report)
