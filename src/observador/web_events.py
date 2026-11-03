"""Closed import contract for the local-only synthetic MV3 prototype."""
import json
from pathlib import Path
import re

from .events import Event

ACTIONS = frozenset(('save','review','download','rename','move','register','open_menu','select_menu',
                     'select_tab','submit','navigate','transition'))
ROLES = frozenset(('button','menuitem','tab','window','control'))
MAX_EXPORT_BYTES = 256 * 1024


def validate_web_export(document):
    try:
        if (type(document) is not dict or set(document) != {'schema_version','kind','capture_real','pilot_authorized','events','dropped','rejected'}
                or type(document['schema_version']) is not int or document['schema_version'] != 1
                or document['kind'] != 'synthetic_web_extension' or document['capture_real'] is not False
                or document['pilot_authorized'] is not False or type(document['events']) is not list or len(document['events']) > 256):
            raise ValueError()
        if any(type(document[key]) is not int or not 0 <= document[key] <= 2**53-1 for key in ('dropped','rejected')):
            raise ValueError()
        events, seen, sessions = [], set(), set()
        previous = 0
        for row in document['events']:
            if type(row) is not dict or len(json.dumps(row)) > 2048:
                raise ValueError()
            event = Event.from_dict(row)
            if (set(row) != set(event.to_dict()) or event.app != 'synthetic-web' or event.device_id != 'laboratorio-sintetico'
                    or event.event_type != 'browser_action' or event.action not in ACTIONS
                    or event.duration_ms != 0 or event.screenshot_ref is not None
                    or set(event.metadata) != {'category','control_role','source_sequence'}
                    or event.metadata['category'] != 'synthetic' or event.metadata['control_role'] not in ROLES
                    or not re.fullmatch(event.metadata['control_role'] + '-[a-f0-9]{16}', event.target)
                    or event.metadata['source_sequence'] <= previous or event.event_id in seen):
                raise ValueError()
            previous = event.metadata['source_sequence']
            sessions.add(event.session_id)
            seen.add(event.event_id)
            events.append(event)
        if len(sessions) > 1:
            raise ValueError()
        return events
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
        raise ValueError('synthetic_web_export_rejected') from None


def read_web_export(path):
    path = Path(path)
    if path.stat().st_size > MAX_EXPORT_BYTES:
        raise ValueError('synthetic_web_export_too_large')
    try:
        document = json.loads(path.read_bytes())
    except (ValueError, UnicodeError):
        raise ValueError('synthetic_web_export_rejected') from None
    return validate_web_export(document)
