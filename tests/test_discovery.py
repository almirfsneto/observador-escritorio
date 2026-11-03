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
