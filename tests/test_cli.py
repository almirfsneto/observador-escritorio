import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class CliTest(unittest.TestCase):
    def test_demo_analyze_export_and_idempotence(self):
        with tempfile.TemporaryDirectory() as directory:
            database = str(Path(directory) / 'demo.sqlite3')
            def cli(*args):
                result = subprocess.run([sys.executable, '-m', 'observador', *args],
                                        capture_output=True, text=True, check=True)
                return json.loads(result.stdout)
            self.assertEqual(cli('demo', '--db', database)['inserted'], 36)
            self.assertEqual(cli('demo', '--db', database)['inserted'], 0)
            report = Path(directory) / 'analysis.json'
            self.assertEqual(cli('analyze', '--db', database, '--out', str(report))['patterns'], 15)
            self.assertTrue(any(len(p['steps']) == 6 for p in json.loads(report.read_text())))
            output = Path(directory) / 'events.jsonl'
            self.assertEqual(cli('export', '--db', database, '--out', str(output))['exported'], 36)
            self.assertEqual(len(output.read_text().splitlines()), 36)
