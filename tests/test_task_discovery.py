from copy import deepcopy
from dataclasses import replace
from datetime import datetime,timedelta
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from uuid import uuid4

from observador.task_discovery import discover_tasks,synthetic_office_corpus


class TaskDiscoveryTest(unittest.TestCase):
    def test_groups_cross_session_variants_without_ephemeral_identity(self):
        corpus=synthetic_office_corpus()
        result=discover_tasks(corpus)
        matches=[candidate for candidate in result['candidates'] if [s['action'] for s in candidate['steps']]==['download','rename','move','register']]
        self.assertTrue(matches)
        candidate=matches[0]
        self.assertEqual(candidate['occurrences'],8)
        self.assertEqual(candidate['sessions'],8)
        self.assertGreaterEqual(len(candidate['variants']),3)
        self.assertEqual(candidate['rework_signals']['adjacent_repetitions'],2)
        self.assertIsNone(candidate['saving_scenario'])
        self.assertIn('temporal_not_causal',candidate['gaps'])
        self.assertFalse(result['pilot_authorized'])
        for event in corpus:self.assertNotIn(event.target,json.dumps(result))

    def test_overlaps_and_duplicates_are_not_independent_executions(self):
        base=synthetic_office_corpus(1)[0]
        events=[replace(base,event_id=str(uuid4()),timestamp_utc=(datetime.fromisoformat(base.timestamp_utc)+timedelta(seconds=i*.1)).isoformat(),
                        metadata={'category':'synthetic','control_role':'control','source_sequence':i+1}) for i in range(5)]
        result=discover_tasks(events+events[:1],max_steps=2)
        self.assertEqual(result['duplicates_removed'],1)
        self.assertEqual(result['candidates'][0]['occurrences'],2)
        self.assertEqual(result['candidates'][0]['confidence_heuristic'],'low')
        with self.assertRaises(ValueError):discover_tasks(events+[replace(events[0],action='rename')])

    def test_gaps_split_and_scenario_is_not_observed_saving(self):
        events=synthetic_office_corpus(4)
        result=discover_tasks(events,assumed_automation_seconds=.1)
        self.assertTrue(result['candidates'])
        for candidate in result['candidates']:
            scenario=candidate['saving_scenario']
            self.assertTrue(scenario['scenario_only'])
            self.assertFalse(scenario['feasibility_validated'])
            self.assertLessEqual(scenario['potential_seconds'],candidate['total_observed_span_seconds'])
        base=events[0]
        distant=[replace(base,event_id=str(uuid4()),timestamp_utc=(datetime.fromisoformat(base.timestamp_utc)+timedelta(minutes=i)).isoformat()) for i in range(3)]
        self.assertEqual(discover_tasks(distant)['candidates'],[])

    def test_same_timestamp_uses_source_sequence_and_never_exports_targets(self):
        events=synthetic_office_corpus(4)
        events=[replace(e,timestamp_utc=events[0].timestamp_utc,target='CLIENTE-FICTICIO-NUNCA-EXPORTAR') for e in reversed(events)]
        result=discover_tasks(events)
        self.assertTrue(result['candidates'])
        self.assertNotIn('CLIENTE',json.dumps(result))
        with self.assertRaises(ValueError):discover_tasks([replace(events[0],device_id='real-user')])
        with self.assertRaises(ValueError):discover_tasks(events,max_steps=100)
        with self.assertRaises(ValueError):discover_tasks(events,assumed_automation_seconds=float('nan'))

    def test_cli_writes_exclusively_and_errors_do_not_echo_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'synthetic-private-name.json'
            command=[sys.executable,'-m','observador.task_discovery','--out',str(output)]
            first=subprocess.run(command,capture_output=True,text=True,timeout=10)
            self.assertEqual(first.returncode,0)
            self.assertTrue(json.loads(output.read_text())['candidates'])
            before=output.read_bytes()
            second=subprocess.run(command,capture_output=True,text=True,timeout=10)
            self.assertNotEqual(second.returncode,0)
            self.assertNotIn(str(output),second.stderr)
            self.assertNotIn('Traceback',second.stderr)
            self.assertEqual(before,output.read_bytes())
