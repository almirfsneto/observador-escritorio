"""Experimental current-user DPAPI envelope. Does not encrypt the live SQLite DB."""
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import sys

from .events import Event
from .private_directory import secure_directory, secure_file, reject_links

MAGIC = b'OBS-SYNTHETIC-DPAPI-1\x00'
MAX_BYTES = 8 * 1024 * 1024


def _crypt(payload, decrypt=False):
    if sys.platform != 'win32' or not isinstance(payload, bytes) or not 0 < len(payload) <= MAX_BYTES:
        raise ValueError('dpapi_platform_or_size_rejected')
    class Blob(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]
    api = ctypes.WinDLL('crypt32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    source = ctypes.create_string_buffer(payload)
    entropy = ctypes.create_string_buffer(MAGIC)
    incoming = Blob(len(payload), ctypes.cast(source, ctypes.POINTER(ctypes.c_ubyte)))
    context = Blob(len(MAGIC), ctypes.cast(entropy, ctypes.POINTER(ctypes.c_ubyte)))
    output = Blob()
    function = api.CryptUnprotectData if decrypt else api.CryptProtectData
    function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.POINTER(Blob), ctypes.c_void_p,
                         ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    function.restype = wintypes.BOOL
    # USER scope: deliberately omit CRYPTPROTECT_LOCAL_MACHINE. Never prompt UI.
    if not function(ctypes.byref(incoming), None, ctypes.byref(context), None, None, 1, ctypes.byref(output)):
        raise OSError('dpapi_operation_failed')
    try:
        if not 0 < output.size <= MAX_BYTES:
            raise ValueError('dpapi_size_rejected')
        return ctypes.string_at(output.data, output.size)
    finally:
        if output.data:
            ctypes.memset(output.data, 0, output.size)
            kernel.LocalFree(output.data)


def protect(payload):
    return MAGIC + _crypt(payload)


def unprotect(envelope):
    if not isinstance(envelope, bytes) or not envelope.startswith(MAGIC):
        raise ValueError('dpapi_envelope_rejected')
    return _crypt(envelope[len(MAGIC):], decrypt=True)


def write_archive(store, destination):
    """Explicit local archive of a validated LabEventQueue; no generic file encryption."""
    from .lab_queue import LabEventQueue
    if not isinstance(store, LabEventQueue):
        raise ValueError('synthetic_queue_required')
    events = store.list_events()
    # Do not write or copy unvalidated database fields to an archive.
    for event in events:
        validate_archive_event(event)
    payload = json.dumps({'schema_version': 1, 'kind': 'synthetic_event_archive',
                          'events': [event.to_dict() for event in events]}, separators=(',', ':')).encode('utf-8')
    envelope = protect(payload)
    destination = Path(destination).absolute()
    reject_links(destination)
    secure_directory(destination.parent)
    # ACL is inherited from the restricted directory before any content is written.
    with destination.open('xb') as stream:
        secure_file(destination)
        stream.write(envelope)
    return len(events)


def validate_archive_event(event):
    import re
    event.validate()
    if (event.app != 'synthetic-app' or event.device_id != 'laboratorio-sintetico'
            or event.event_type not in ('window_focus', 'ui_action')
            or event.action not in ('focus', 'invoke', 'toggle') or event.duration_ms != 0
            or (event.event_type == 'window_focus') != (event.action == 'focus')
            or event.screenshot_ref is not None
            or not {'category', 'control_role'} <= set(event.metadata) <= {'category', 'control_role', 'source_sequence'}
            or event.metadata['category'] != 'laboratory'
            or not re.fullmatch(r'(button|checkbox|combobox|edit|listitem|menuitem|tab|window|control)-[a-f0-9]{16}', event.target)):
        raise ValueError('archive_projection_rejected')


def read_archive(path):
    path = Path(path)
    reject_links(path)
    if path.stat().st_size > MAX_BYTES + len(MAGIC):
        raise ValueError('dpapi_size_rejected')
    try:
        document = json.loads(unprotect(path.read_bytes()))
        if set(document) != {'schema_version', 'kind', 'events'} or type(document['schema_version']) is not int or document['schema_version'] != 1 or document['kind'] != 'synthetic_event_archive':
            raise ValueError()
        if not isinstance(document['events'], list) or len(document['events']) > 10000:
            raise ValueError()
        events = [Event.from_dict(row) for row in document['events']]
        for event in events:
            validate_archive_event(event)
        return events
    except (ValueError, TypeError, KeyError):
        raise ValueError('archive_payload_rejected') from None
