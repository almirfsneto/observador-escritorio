from dataclasses import replace
from datetime import datetime,timedelta
import unittest
from uuid import uuid4

from observador.mining_evaluation import evaluate_synthetic_mining,labelled_corpus
from observador.task_discovery import discover_tasks,compatible_variant


class MiningNegativesTest(unittest.TestCase):
    def test_labelled_similar_but_distinct_and_interrupted_tasks_are_not_merged(self):
        evaluation=evaluate_synthetic_mining()
        self.assertEqual(evaluation['traces'],10)
        self.assertEqual(evaluation['pairs'],45)
        self.assertEqual(evaluation['false_positive'],0)
        self.assertEqual(evaluation['false_negative'],0)
        self.assertEqual(evaluation['true_positive'],17)
        self.assertEqual(evaluation['true_negative'],28)
        self.assertEqual(evaluation['precision'],1)
        self.assertEqual(evaluation['recall'],1)
        self.assertFalse(evaluation['real_world_accuracy_claim'])
        print('SYNTHETIC_MINING_EVALUATION',evaluation)

    def test_sequence_preserves_source_order_and_gap_or_clock_regression_cuts_task(self):
        events,_,_=labelled_corpus()
        trace=events[:4]
        ordered=discover_tasks(trace+list(reversed(events[4:])))
        self.assertTrue(ordered['candidates'])
        # Same session but a gap in observed sequence must not invent intermediate steps.
        broken=[replace(trace[0],event_id=str(uuid4()),metadata={**trace[0].metadata,'source_sequence':1}),
                replace(trace[1],event_id=str(uuid4()),metadata={**trace[1].metadata,'source_sequence':5})]
        result=discover_tasks(broken)
        self.assertEqual(result['candidates'],[])
        self.assertIn('observation_sequence_gap',result['gaps'])
        # A backwards source clock must not be sorted into a fictional causal order.
        backwards=[trace[0],replace(trace[1],timestamp_utc=(datetime.fromisoformat(trace[0].timestamp_utc)-timedelta(seconds=1)).isoformat())]
        self.assertIn('source_clock_regressed',discover_tasks(backwards)['gaps'])

    def test_click_focus_duplicates_interruptions_and_denied_sources(self):
        events,_,_=labelled_corpus();base=events[0]
        noise=[replace(base,event_id=str(uuid4()),action='click',metadata={**base.metadata,'source_sequence':i+1}) for i in range(6)]
        noise+= [replace(base,event_id=str(uuid4()),event_type='window_focus',action='focus',metadata={**base.metadata,'source_sequence':i+7}) for i in range(6)]
        self.assertEqual(discover_tasks(noise)['candidates'],[])
        self.assertEqual(discover_tasks(events+events[:1])['duplicates_removed'],1)
        split=[replace(base,event_id=str(uuid4()),session_id=str(uuid4())) for _ in range(4)]
        self.assertEqual(discover_tasks(split)['candidates'],[])
        with self.assertRaises(ValueError):discover_tasks([replace(base,app='Denied App')])
        with self.assertRaises(ValueError):discover_tasks([base,replace(base,event_id=str(uuid4()))])

    def test_known_filtered_focus_does_not_create_a_fake_missing_sequence(self):
        events,_,_=labelled_corpus()
        first=events[0];second=events[1]
        focus=replace(first,event_id=str(uuid4()),event_type='window_focus',action='focus',metadata={**first.metadata,'source_sequence':2})
        second=replace(second,metadata={**second.metadata,'source_sequence':3})
        result=discover_tasks([first,focus,second])
        self.assertNotIn('observation_sequence_gap',result['gaps'])
