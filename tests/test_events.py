import unittest
from dataclasses import replace
from observador.sample import generate_sample
from observador.events import Event

class EventsTest(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(generate_sample(1)[0].schema_version, 1)
    def test_utc_required(self):
        with self.assertRaises(ValueError):
            replace(generate_sample(1)[0], timestamp_utc="2026-10-26T12:00:00").validate()
    def test_reject_sensitive_metadata_key(self):
        with self.assertRaises(ValueError):
            replace(generate_sample(1)[0], metadata={"password":"test"}).validate()
    def test_reject_unsafe_screenshot_path(self):
        with self.assertRaises(ValueError):
            replace(generate_sample(1)[0], screenshot_ref="../sensitive.png").validate()

    def test_reject_windows_rooted_screenshot_and_wrong_types(self):
        for path in [r'\private.png', r'\\server\private.png', '/private.png', '', 'a//b.png']:
            with self.subTest(path=path), self.assertRaises(ValueError):
                replace(generate_sample(1)[0], screenshot_ref=path).validate()
        with self.assertRaises(ValueError):
            replace(generate_sample(1)[0], duration_ms=True).validate()

    def test_metadata_values_cannot_carry_arbitrary_payloads(self):
        for metadata in [{'control_role': {'password': 'secret'}}, {'category': 'customer-data'},
                         {'confidence': float('nan')}, {'http_status': True}, {'result': 'secret'}]:
            with self.subTest(metadata=metadata), self.assertRaises(ValueError):
                replace(generate_sample(1)[0], metadata=metadata).validate()
