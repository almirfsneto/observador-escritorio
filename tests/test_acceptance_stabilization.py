"""Constructed fixtures only. Never reads or versions the operator's local JSON."""
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from observador.acceptance_report import new_report,empty_session,finalize_report,validate_report,ReportError,REPORT_SCHEMA
from observador.acceptance_prepare import parse_tests,source_state,Preparation
from observador.acceptance_review import build_review,write_review,REVIEW_SCHEMA,NativeHealthObservation
from observador.acceptance_test_runner import summarize,read_summary,MARKER,CATEGORIES
from observador.acceptance_session import SessionRecorder
from observador.acceptance_wizard import test_status_text,AcceptanceWizard


def constructed_trial(os='windows11',origin='operator_guided'):
    r=new_report(origin);r['environment'].update(os_family=os,os_build=22631 if os=='windows11' else 19045)
    r['automated_tests']=dict(status='PASSOU',discovered=76,skipped=1,failures=0,errors=0)
    for check in r['manual_checks'].values():check.update(status='PASSOU',observation='SEM_ANOMALIA')
    for index in range(3):
        session=empty_session();session.update(capture_started=True,termination='expired' if index<2 else 'operator_stop',children_stopped=True)
        session['counters']['events_accepted']=10;session['counters']['invoke']=10
        if index==0:
            session['persistence_enabled']=True;session['counters']['queue_written']=10;session['counters']['native_dropped']=1
        r['sessions'].append(session)
    return r


class AcceptanceStabilizationTest(unittest.TestCase):
    def test_constructed_three_session_pattern_exposes_all_four_caveats(self):
        r=constructed_trial();original=deepcopy(r);final=finalize_report(r);d=build_review(r)
        self.assertEqual(r,original)
        self.assertNotIn('windows11_trial_required',final['gaps'])
        self.assertIn('windows10_trial_required',final['gaps'])
        self.assertEqual(d['sessions']['count'],3);self.assertEqual(d['sessions']['expired'],2)
        self.assertEqual(d['sessions']['cleanup_confirmed'],3);self.assertEqual(d['sessions']['persistence_with_writes'],1)
        self.assertEqual(d['native']['reported_dropped'],1);self.assertIsNone(d['native']['loss_rate'])
        self.assertEqual(d['native']['attribution'],'unknown_from_aggregate')
        self.assertEqual(d['tests']['executed'],75);self.assertEqual(d['tests']['skip_categories']['unclassified'],1)
        self.assertIn('skip_details_unavailable',d['issues']);self.assertIn('commit_unavailable',d['issues'])
        self.assertIsNone(final['source']['commit']);self.assertFalse(d['pilot_authorized'])
        self.assertEqual(final['human_gate'],'PENDENTE_REVISAO_HUMANA')

    def test_os_flags_are_execution_declarations_not_acceptance(self):
        for os,other in (('windows10','windows11'),('windows11','windows10')):
            r=constructed_trial(os);r['manual_checks']['senha']['status']='FALHOU'
            result=finalize_report(r)
            self.assertNotIn(os+'_trial_required',result['gaps']);self.assertIn(other+'_trial_required',result['gaps'])
            self.assertIn('manual_checks_failed',build_review(r)['issues']);self.assertFalse(result['pilot_authorized'])
        for case in ('ci','no_sessions','no_manual','environment_only'):
            r=constructed_trial()
            if case=='ci':r['origin']='automated_test'
            elif case=='no_sessions':r['sessions']=[]
            elif case=='no_manual':
                for c in r['manual_checks'].values():c.update(status='NAO_EXECUTADO',observation='NAO_AVALIADO')
            else:r=new_report();r['environment']['os_family']='windows11'
            with self.subTest(case=case):self.assertIn('windows11_trial_required',finalize_report(r)['gaps'])

    def test_all_skipped_unknown_malformed_and_crlf_summaries_cannot_claim_success(self):
        for output in ('Ran 2 tests in 0.1s\nOK (skipped=2)','Ran 2 tests in 0.1s\nOK (skipped=3)',
                       'Ran 2 tests in 0.1s','Ran 2 tests in 0.1s\nOK (skipped=secret)',
                       'Ran 2 tests in 0.1s\nOK (skipped=1, skipped=1)',
                       'Ran '+('9'*5000)+' tests in 0.1s\nOK',
                       'Ran 2 tests in 0.1s\nOK (skipped=9999999999999999999)'):
            with self.subTest(output=output):self.assertEqual(parse_tests(0,output)['status'],'FALHOU')
        summary=parse_tests(0,'Ran 2 tests in 0.1s\r\n\r\nOK (skipped=1)\r\n')
        self.assertEqual(summary['status'],'PASSOU');self.assertEqual(summary['skipped'],1)
        self.assertIn('ignorados: 1',test_status_text(summary));self.assertIn('cobertura incompleta',test_status_text(summary))
        r=new_report();r['automated_tests']=dict(status='PASSOU',discovered=2,skipped=2,failures=0,errors=0)
        with self.assertRaises(ReportError):validate_report(r)

    def test_skip_details_are_closed_exact_categories_never_raw_reasons(self):
        class Case:
            def __init__(self,identity):self.identity=identity
            def id(self):return self.identity
        result=SimpleNamespace(testsRun=5,failures=[],errors=[],skipped=[
            (Case('test_windows_desktop.DesktopAutomationTest.test_synthetic_invokes_and_password_exclusion'),
             'Hosted runner has no usable foreground desktop; manual Windows validation required'),
            (Case('test_browser_extension.RealTest.case'),'Real browser test enabled in dedicated web CI job'),
            (Case('test_unknown.SecretTest'),'SYNTHETIC_SENTINEL secret/path')])
        packet=summarize(result,'win32')
        self.assertEqual(packet['skip_categories']['foreground_desktop_unavailable'],1)
        self.assertEqual(packet['skip_categories']['browser_dedicated'],1);self.assertEqual(packet['skip_categories']['unclassified'],1)
        self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(packet));self.assertNotIn('SecretTest',json.dumps(packet))
        auto=dict(status='PASSOU',discovered=5,skipped=3,failures=0,errors=0)
        self.assertEqual(read_summary(MARKER+json.dumps(packet),auto),packet)
        for mutate in ('extra','list','counts','duplicate'):
            bad=deepcopy(packet)
            if mutate=='extra':bad['raw']='SYNTHETIC_SENTINEL'
            elif mutate=='list':bad['skip_categories']=list(CATEGORIES)
            elif mutate=='counts':bad['executed']=5
            encoded=json.dumps(bad)
            if mutate=='duplicate':encoded='{"schema_version":1,'+encoded[1:]
            self.assertIsNone(read_summary(MARKER+encoded,auto))

    def test_real_validator_runner_keeps_skip_classification_in_bounded_final_packet(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'tests').mkdir()
            (root/'tests/test_synthetic.py').write_text('import unittest\nclass Synthetic(unittest.TestCase):\n def test_ok(self): pass\n @unittest.skip("SYNTHETIC_SENTINEL")\n def test_skip(self): pass\n')
            from observador.acceptance_prepare import CommandRunner
            runner=CommandRunner();self.addCleanup(runner.cancel)
            r=new_report();prep=Preparation(root,r,runner=runner);prep.ready=True
            # Exercise Preparation.run_tests itself using a minimal disposable source tree.
            import shutil
            package=root/'src/observador';package.mkdir(parents=True)
            (package/'__init__.py').write_text('')
            shutil.copyfile(Path(__file__).resolve().parents[1]/'src/observador/acceptance_test_runner.py',package/'acceptance_test_runner.py')
            summary=prep.run_tests();packet=prep.test_diagnostics
            self.assertEqual(summary['skipped'],1);self.assertEqual(packet['executed'],1)
            self.assertEqual(packet['skip_categories']['unclassified'],1)
            self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(packet))

    def test_zip_nested_in_git_cannot_borrow_parent_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);subprocess.run(['git','init','-q',str(root)],check=True,capture_output=True)
            subprocess.run(['git','-C',str(root),'-c','user.name=Synthetic','-c','user.email=synthetic@example.invalid',
                            'commit','--allow-empty','-q','-m','synthetic'],check=True,capture_output=True)
            archive=root/'extracted-zip';archive.mkdir()
            self.assertIsNotNone(source_state(root)['commit'])
            self.assertEqual(source_state(archive),dict(commit=None,modified=None))
        with tempfile.TemporaryDirectory() as tmp:
            with patch('observador.acceptance_prepare.subprocess.run') as git:
                self.assertEqual(source_state(tmp),dict(commit=None,modified=None));git.assert_not_called()

    def test_native_observations_are_sampled_phase_not_cause_or_final_delivery(self):
        import threading
        now=[10.0]
        stream=SimpleNamespace(lock=threading.RLock(),last_health_received=None,native_dropped=0,
                               stopped=False,health='active',native_callbacks={},native_queues=None,monotonic=lambda:now[0])
        observed=NativeHealthObservation();observed.observe(stream);self.assertEqual(observed.snapshot()['samples'],0)
        stream.last_health_received=9.9;stream.native_dropped=1;stream.native_callbacks={'errors':1}
        stream.native_queues={'output_depth':1,'focus_depth':0};observed.observe(stream)
        now[0]=12;observed.observe(stream);d=observed.snapshot()
        self.assertEqual(d['samples'],1);self.assertEqual(d['drop_increases_seen']['active'],1)
        self.assertGreaterEqual(d['last_sample_age_ms'],2000);self.assertFalse(d['final_health_confirmed'])
        stream.last_health_received=12;stream.stopped=True;observed.observe(stream)
        self.assertEqual(observed.snapshot()['reported_drop_highwater'],1)
        self.assertEqual(observed.snapshot()['drop_increases_seen']['stopped'],0)

    def test_diagnostic_schema_v1_unchanged_and_exclusive_local_write(self):
        root=Path(__file__).resolve().parents[1]
        self.assertEqual(json.loads((root/'docs/ACEITE_REPORT_SCHEMA.json').read_text()),REPORT_SCHEMA)
        self.assertEqual(json.loads((root/'docs/ACCEPTANCE_REVIEW_SCHEMA.json').read_text()),REVIEW_SCHEMA)
        r=constructed_trial()
        with tempfile.TemporaryDirectory() as tmp:
            p=write_review(r,root,Path(tmp)/'results');saved=json.loads(p.read_text())
            self.assertEqual(saved,build_review(r))
            with self.assertRaises(FileExistsError):write_review(r,root,p.parent)
            with self.assertRaises(ReportError):write_review(r,root,root/'diagnostics')
            bad=deepcopy(r);bad['hostname']='SYNTHETIC_SENTINEL'
            with self.assertRaises(ReportError) as error:build_review(bad)
            self.assertNotIn('SYNTHETIC_SENTINEL',str(error.exception))

    def test_secondary_diagnostic_write_failure_does_not_hide_saved_v1(self):
        class Variable:
            def __init__(self):self.value=''
            def set(self,value):self.value=value
        with tempfile.TemporaryDirectory() as tmp:
            r=constructed_trial()
            ui=SimpleNamespace(active_lab=lambda:False,worker=None,export_count=0,snapshot=lambda:r,labs=[],
                 preparation=SimpleNamespace(test_diagnostics=None),repository=Path(tmp)/'repo',destination=Path(tmp)/'results',
                 status=Variable(),output_status=Variable())
            # Match the three data-only sessions; no Tk/processes launched by this fixture.
            from observador.acceptance_review import NativeHealthObservation
            ui.labs=[SimpleNamespace(recorder=SimpleNamespace(native_health=NativeHealthObservation())) for _ in r['sessions']]
            with patch('observador.acceptance_review.write_review',side_effect=OSError('synthetic')):
                AcceptanceWizard.export(ui)
            self.assertEqual(len(list(ui.destination.glob('aceite-*.json'))),1)
            self.assertEqual(ui.export_count,1);self.assertIn('Relatório v1 salvo',ui.status.value)
            self.assertIn('não foi salvo',ui.status.value)
