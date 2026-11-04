from copy import deepcopy
from pathlib import Path
import json
import unittest

from observador.web_events import validate_web_export
from test_storage_hardening import event


class WebContractTest(unittest.TestCase):
    def export(self):
        row=event().to_dict()
        row.update(app='synthetic-web',event_type='browser_action',action='save')
        row['metadata'].update(category='synthetic',source_sequence=1)
        return dict(schema_version=1,kind='synthetic_web_extension',capture_real=False,pilot_authorized=False,
                    events=[row],dropped=0,rejected=0)

    def test_compatible_event_and_minimal_manifest(self):
        self.assertEqual(len(validate_web_export(self.export())),1)
        root=Path(__file__).resolve().parents[1]
        manifest=json.loads((root/'browser-extension/manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['permissions'],['storage'])
        self.assertEqual(manifest['host_permissions'],['http://127.0.0.1/synthetic-lab/*'])
        self.assertFalse(manifest['content_scripts'][0]['all_frames'])

    def test_rejects_pii_extra_fields_values_permissions_and_sequences(self):
        for key,value in [('url','http://client/?token=secret'),('hostname','private'),('password','secret')]:
            document=self.export()
            document['events'][0][key]=value
            with self.assertRaisesRegex(ValueError,'^synthetic_web_export_rejected$'):
                validate_web_export(document)
        for change in [dict(action='secret'),dict(target='client-name'),dict(app='real-app'),dict(screenshot_ref='secret.png')]:
            document=self.export()
            document['events'][0].update(change)
            with self.assertRaises(ValueError):validate_web_export(document)
        document=self.export()
        document['events'].append(deepcopy(document['events'][0]))
        with self.assertRaises(ValueError):validate_web_export(document)
