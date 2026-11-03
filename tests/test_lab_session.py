from datetime import datetime, timedelta, timezone
from pathlib import PureWindowsPath
import unittest

from observador.lab_session import LAB_DURATION_MINUTES, make_lab_policy, validate_lab_executable


class LaboratoryPolicyTest(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2026, 11, 3, 12, tzinfo=timezone(timedelta(hours=-3)))
        self.path = r"C:\Work\tools\SyntheticTaskApp\bin\Release\net8.0-windows\SyntheticTaskApp.exe"

    def test_allows_only_dedicated_named_executable(self):
        for invalid in (
            r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
            r"C:\Windows\explorer.exe",
            "SyntheticTaskApp.exe",
            r"C:\Lab\Other.exe",
        ):
            with self.subTest(path=invalid), self.assertRaises(ValueError):
                validate_lab_executable(invalid)
        validate_lab_executable(self.path)
        self.assertEqual(PureWindowsPath(self.path).name, "SyntheticTaskApp.exe")

    def test_policy_limited_to_fifteen_minutes(self):
        policy = make_lab_policy(self.path, self.start)
        self.assertTrue(policy.permits(self.start))
        self.assertFalse(policy.permits(self.start + timedelta(minutes=LAB_DURATION_MINUTES)))
        self.assertEqual(len(policy.applications), 1)
        self.assertEqual(policy.applications[0].alias, "synthetic-app")

    def test_requires_timezone_aware_clock(self):
        with self.assertRaises(ValueError):
            make_lab_policy(self.path, self.start.replace(tzinfo=None))

    def test_policy_never_includes_generic_browsers_or_office(self):
        policy = make_lab_policy(self.path, self.start)
        self.assertEqual(policy.applications[0].executable, self.path)
        self.assertNotIn("explorer.exe", policy.applications[0].executable.lower())


if __name__ == "__main__":
    unittest.main()
