"""Win32 test setup for a window owned by a synthetic child; no text or UI values."""
import time


def prepare_foreground(process, *, tick=lambda: None, timeout=10):
    import ctypes
    from ctypes import wintypes
    api = ctypes.WinDLL('user32', use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    api.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    api.EnumWindows.restype = wintypes.BOOL
    api.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    api.IsWindowVisible.argtypes = [wintypes.HWND]
    api.IsWindowVisible.restype = wintypes.BOOL
    api.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
    api.GetWindow.restype = wintypes.HWND
    api.SetForegroundWindow.argtypes = [wintypes.HWND]
    api.SetForegroundWindow.restype = wintypes.BOOL
    api.GetForegroundWindow.restype = wintypes.HWND
    found = []
    @callback_type
    def visit(handle, _):
        owner = wintypes.DWORD()
        api.GetWindowThreadProcessId(handle, ctypes.byref(owner))
        if (owner.value == process.pid and api.IsWindowVisible(handle)
                and not api.GetWindow(handle, 4)):  # GW_OWNER; reject transient owned windows.
            found.append(handle)
            return False
        return True
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        tick()
        if process.poll() is not None:
            raise AssertionError('Synthetic fixture exited before desktop preparation')
        found.clear()
        api.EnumWindows(visit, 0)
        if found:
            api.SetForegroundWindow(found[0])
            tick()
            owner = wintypes.DWORD()
            api.GetWindowThreadProcessId(api.GetForegroundWindow(), ctypes.byref(owner))
            if owner.value == process.pid:
                return True
        time.sleep(.02)
    return False
