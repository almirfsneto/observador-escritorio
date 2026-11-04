from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from observador.acceptance_prepare import (CommandRunner, Preparation, PreparationError,
                                          artifact_hashes, binaries, parse_tests)
from observador.acceptance_report import finalize_report, new_report


class PreparationTest(unittest.TestCase):
    def test_test_summary_does_not_include_output_or_promote_manual_checks(self):
        result = parse_tests(0, 'C:\\Users\\Alice\\secret\nRan 23 tests in 1.0s\nOK (skipped=2)')
        self.assertEqual(result, {'status': 'PASSOU', 'discovered': 23, 'skipped': 2, 'failures': 0, 'errors': 0})
        self.assertNotIn('Alice', str(result))
        self.assertEqual(parse_tests(1, 'secret error')['status'], 'FALHOU')
        self.assertEqual(parse_tests(0, 'unproven')['status'], 'FALHOU')
        self.assertEqual(parse_tests(0, 'Ran 0 tests in 0.0s')['status'], 'FALHOU')
        self.assertEqual(parse_tests(0, 'Ran 2 tests in 0.1s\nFAILED (errors=1)')['status'], 'FALHOU')

    def test_interrupted_rerun_invalidates_previous_success(self):
        class Runner:
            def run(self, *args, **kwargs):
                raise PreparationError('command_timeout')
        report = new_report()
        report['automated_tests'] = parse_tests(0, 'Ran 2 tests in 0.1s\nOK')
        prep = Preparation('.', report, runner=Runner())
        prep.ready = True
        with self.assertRaises(PreparationError):
            prep.run_tests()
        self.assertEqual(report['automated_tests']['status'], 'FALHOU')
        self.assertIsNone(report['automated_tests']['discovered'])
        finalize_report(report)

    def test_timeout_stops_owned_command_but_allows_retry(self):
        runner = CommandRunner()
        with self.assertRaisesRegex(PreparationError, 'command_timeout'):
            runner.run([sys.executable, '-c', 'import time;time.sleep(30)'], cwd=Path.cwd(), timeout=.2)
        self.assertIsNone(runner.current)
        code, output = runner.run([sys.executable, '-c', 'print(42)'], cwd=Path.cwd(), timeout=10)
        self.assertEqual((code, output.strip()), (0, '42'))
        runner.cancel()
        with self.assertRaisesRegex(PreparationError, 'preparation_cancelled'):
            runner.run([sys.executable, '-c', 'print(42)'], cwd=Path.cwd(), timeout=10)

    def test_offline_build_pins_sdk_and_hashes_code_assemblies_not_just_apphost(self):
        class Runner:
            def __init__(self):
                self.commands = []
                self.config = None
            def run(self, args, **options):
                self.commands.append(args)
                if args[1] == '--list-sdks':
                    return 0, '8.0.408 [C:\\Users\\Alice\\dotnet]\n9.0.100 [C:\\private]'
                if args[1] == 'restore':
                    self.config = Path(args[args.index('--configfile')+1]).read_text()
                    self.assert_sdk = (Path(options['cwd'])/'global.json').read_text()
                return 0, ''
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for binary in binaries(root).values():
                binary.parent.mkdir(parents=True)
                for suffix in ('.exe', '.dll', '.deps.json', '.runtimeconfig.json'):
                    binary.with_name(binary.stem+suffix).write_bytes(b'synthetic')
            runner = Runner()
            report = new_report()
            prep = Preparation(root, report, runner=runner)
            with patch('observador.acceptance_prepare.shutil.which', return_value='dotnet'):
                prep.prepare()
            self.assertTrue(prep.ready)
            self.assertEqual(report['environment']['dotnet_sdk'], '8.0.408')
            self.assertNotIn('Alice', str(finalize_report(report)))
            self.assertIn('<clear />', runner.config)
            self.assertIn('8.0.408', runner.assert_sdk)
            self.assertTrue(all('--no-restore' in cmd for cmd in runner.commands if cmd[1]=='build'))
            builds = [cmd for cmd in runner.commands if cmd[1]=='build']
            self.assertEqual(len(builds),3)
            self.assertTrue(any('SyntheticTaskApp.csproj' in cmd[2] for cmd in builds))
            self.assertFalse(any('install' in cmd for cmd in runner.commands))
            self.assertTrue(prep.verify_artifacts())
            binary = binaries(root)['provider']
            binary.with_suffix('.dll').write_bytes(b'modified')
            self.assertFalse(prep.verify_artifacts())

    def test_missing_sdk_never_installs_or_builds(self):
        report = new_report()
        prep = Preparation('.', report)
        with patch('observador.acceptance_prepare.shutil.which', return_value=None):
            with self.assertRaises(PreparationError):
                prep.prepare()
        self.assertFalse(prep.ready)
        self.assertEqual(report['checks']['dotnet_sdk'], 'FALHOU')

    def test_command_output_is_bounded_and_telemetry_off(self):
        runner = CommandRunner()
        script = "import os; print(os.environ['DOTNET_CLI_TELEMETRY_OPTOUT']); print('x'*200000)"
        code, output = runner.run([sys.executable, '-c', script], cwd=Path.cwd(), timeout=10)
        self.assertEqual(code, 0)
        self.assertLessEqual(len(output), 32 * 4096)
        code, output = runner.run([sys.executable, '-c', "import os;print(os.environ['DOTNET_CLI_TELEMETRY_OPTOUT'])"],
                                  cwd=Path.cwd(), timeout=10)
        self.assertEqual((code, output.strip()), (0, '1'))
        runner.cancel()
