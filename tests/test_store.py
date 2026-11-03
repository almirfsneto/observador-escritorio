import tempfile
from pathlib import Path
import unittest
from observador.sample import generate_sample
from observador.store import EventStore

class StoreTest(unittest.TestCase):
    def test_insert_idempotence(self):
        with tempfile.TemporaryDirectory() as p:
            s=EventStore(Path(p)/"db.sqlite3")
            try:
                ev=generate_sample(1)[0]
                self.assertTrue(s.insert(ev))
                self.assertFalse(s.insert(ev))
                self.assertEqual(len(s.list_events()), 1)
            finally: s.close()
    def test_export_round_trip(self):
        with tempfile.TemporaryDirectory() as p:
            s=EventStore(Path(p)/"db.sqlite3")
            try:
                for ev in generate_sample(1): s.insert(ev)
                target=Path(p)/"events.jsonl"
                self.assertEqual(s.export_jsonl(target),6)
                self.assertEqual(len(target.read_text(encoding="utf-8").splitlines()),6)
            finally: s.close()
