import unittest
from dataclasses import replace
from observador.sample import generate_sample
from observador.discovery import discover_patterns

class DiscoveryTest(unittest.TestCase):
    def test_identifies_six_step_pattern(self):
        patterns=discover_patterns(generate_sample(6), min_count=3)
        self.assertTrue(any(len(p["steps"])==6 and p["occurrences"]==6 for p in patterns))
    def test_separate_sessions(self):
        events=generate_sample(1)
        self.assertEqual(discover_patterns(events, min_count=2), [])

    def test_same_timestamp_uses_observation_sequence_before_random_ids(self):
        base = generate_sample(1)[0]
        events = []
        # Deliberately reversed UUID lexical order; native observation order is A,B,A,B.
        for index in range(4):
            events.append(replace(base, event_id=f'00000000-0000-0000-0000-{4-index:012d}',
                                  event_type='ui_action', target='A' if index % 2 == 0 else 'B',
                                  metadata={'source_sequence': index + 1}))
        result = discover_patterns(events, min_count=2, max_steps=2)
        self.assertTrue(any([step['target'] for step in pattern['steps']] == ['A', 'B']
                            and pattern['occurrences'] == 2 for pattern in result))
