"""Exercise the source entrypoint without opening a desktop or installing a package."""
import os
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import patch


class AcceptanceLauncherTest(unittest.TestCase):
    def test_entrypoint_finds_checkout_from_another_working_directory(self):
        repository = Path(__file__).resolve().parents[1]
        previous_directory, previous_path = Path.cwd(), sys.path[:]
        try:
            with tempfile.TemporaryDirectory(prefix='synthetic launcher ') as temporary:
                os.chdir(temporary)
                with patch('observador.acceptance_wizard.main') as main:
                    runpy.run_path(str(repository / 'tools/validar_laboratorio.py'), run_name='__main__')
                main.assert_called_once_with(repository)
        finally:
            os.chdir(previous_directory)
            sys.path[:] = previous_path

    def test_unsupported_python_stops_before_opening_or_preparing(self):
        repository = Path(__file__).resolve().parents[1]
        with patch('sys.version_info', (3, 10, 0)), patch('observador.acceptance_wizard.main') as main:
            with self.assertRaisesRegex(SystemExit, 'Python 3.11'):
                runpy.run_path(str(repository / 'tools/validar_laboratorio.py'), run_name='__main__')
            main.assert_not_called()
