"""One checked close attempt; quarantine uncertain ownership, never retry a slot."""
from ctypes import wintypes


def declare_close_handle(api):
    api.CloseHandle.argtypes = [wintypes.HANDLE]
    api.CloseHandle.restype = wintypes.BOOL


def close_handle_once(owner, api):
    if getattr(owner, 'close_state', 'open') == 'failed':
        raise OSError('cleanup_unconfirmed')
    if owner.handle is None:
        owner.close_state = 'closed'
        return
    owner.close_state = 'failed'  # Also sticky if the wrapper raises.
    try:
        closed = api.CloseHandle(owner.handle)
    except OSError:
        raise OSError('cleanup_unconfirmed') from None
    if not closed:
        raise OSError('cleanup_unconfirmed')
    owner.handle = None
    owner.close_state = 'closed'
