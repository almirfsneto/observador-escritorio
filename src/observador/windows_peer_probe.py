"""Identity preflight of an OWNED Windows child, without IPC/capture integration.

Not peer authentication: a future transport must bind its kernel peer handle/PID
to this same identity and enforce token/session/ACL. No process enumeration.
"""
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import subprocess
import sys

from .private_directory import reject_links


def inspect_owned_child(child,expected_path,expected_ticks,expected_session):
    """Only a Popen child handle retained by this caller; static errors, no paths.

    CPython Windows Popen retains the process handle. Query the same handle for
    creation time/image/PID; never reopen a PID supplied by an incoming message.
    """
    if (sys.platform!='win32' or type(child) is not subprocess.Popen or child.poll() is not None
            or type(expected_ticks) is not int or expected_ticks<=0
            or type(expected_session) is not int or expected_session<0):
        raise ValueError('owned_child_identity_rejected')
    try:
        expected=Path(expected_path).absolute();reject_links(expected)
        if not expected.is_file():raise ValueError()
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.GetProcessId.argtypes=[wintypes.HANDLE];kernel.GetProcessId.restype=wintypes.DWORD
        kernel.GetProcessTimes.argtypes=[wintypes.HANDLE]+[ctypes.POINTER(wintypes.FILETIME)]*4
        kernel.GetProcessTimes.restype=wintypes.BOOL
        kernel.QueryFullProcessImageNameW.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
        kernel.QueryFullProcessImageNameW.restype=wintypes.BOOL
        kernel.ProcessIdToSessionId.argtypes=[wintypes.DWORD,ctypes.POINTER(wintypes.DWORD)]
        kernel.ProcessIdToSessionId.restype=wintypes.BOOL
        handle=wintypes.HANDLE(int(child._handle))
        pid=kernel.GetProcessId(handle)
        if pid!=child.pid:raise ValueError()
        created,exited,kernel_time,user_time=(wintypes.FILETIME() for _ in range(4))
        if not kernel.GetProcessTimes(handle,ctypes.byref(created),ctypes.byref(exited),ctypes.byref(kernel_time),ctypes.byref(user_time)):raise ValueError()
        ticks=(created.dwHighDateTime<<32 | created.dwLowDateTime)+504911232000000000
        length=wintypes.DWORD(32768);buffer=ctypes.create_unicode_buffer(length.value)
        if not kernel.QueryFullProcessImageNameW(handle,0,buffer,ctypes.byref(length)):raise ValueError()
        if os.path.normcase(buffer.value)!=os.path.normcase(str(expected)):raise ValueError()
        session=wintypes.DWORD()
        if not kernel.ProcessIdToSessionId(pid,ctypes.byref(session)):raise ValueError()
        if ticks!=expected_ticks or session.value!=expected_session or child.poll() is not None:raise ValueError()
        return dict(pid=pid,start_ticks=ticks,session_slot=session.value)
    except (OSError,ValueError,TypeError,AttributeError):
        raise ValueError('owned_child_identity_rejected') from None
