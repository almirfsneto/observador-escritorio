"""Restrict only dedicated synthetic storage; never change an ancestor's ACL."""
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import stat
import sys


def reject_links(path):
    path = Path(path).absolute()
    for part in (path, *path.parents):
        if part.exists() or part.is_symlink():
            info = part.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                raise OSError('storage_link_rejected')
    if path.is_file() and path.stat().st_nlink != 1:
        raise OSError('storage_hardlink_rejected')


class WindowsSecurity:
    def __init__(self):
        self.api = ctypes.WinDLL('advapi32', use_last_error=True)
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.kernel.GetCurrentProcess.restype = wintypes.HANDLE
        self.kernel.LocalFree.argtypes = [ctypes.c_void_p]
        self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self.api.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
        self.api.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
        self.api.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
        self.api.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p]
        self.api.SetFileSecurityW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p]
        self.api.GetFileSecurityW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
        self.api.ConvertSecurityDescriptorToStringSecurityDescriptorW.argtypes = [ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p]

    def user_sid(self):
        token, size = wintypes.HANDLE(), wintypes.DWORD()
        if not self.api.OpenProcessToken(self.kernel.GetCurrentProcess(), 8, ctypes.byref(token)):
            raise OSError('storage_acl_unavailable')
        try:
            self.api.GetTokenInformation(token, 1, None, 0, ctypes.byref(size))
            data = ctypes.create_string_buffer(size.value)
            if not self.api.GetTokenInformation(token, 1, data, size, ctypes.byref(size)):
                raise OSError('storage_acl_unavailable')
            sid = ctypes.cast(data, ctypes.POINTER(ctypes.c_void_p))[0]
            text = ctypes.c_void_p()
            if not self.api.ConvertSidToStringSidW(sid, ctypes.byref(text)):
                raise OSError('storage_acl_unavailable')
            try:
                return ctypes.wstring_at(text)
            finally:
                self.kernel.LocalFree(text)
        finally:
            self.kernel.CloseHandle(token)

    def restrict(self, path, directory=False):
        flags = 'OICI' if directory else ''
        sddl = f'D:P(A;{flags};FA;;;SY)(A;{flags};FA;;;{self.user_sid()})'
        descriptor = ctypes.c_void_p()
        if not self.api.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, 1, ctypes.byref(descriptor), None):
            raise OSError('storage_acl_unavailable')
        try:
            if not self.api.SetFileSecurityW(str(path), 0x80000004, descriptor):
                raise OSError('storage_acl_unavailable')
        finally:
            self.kernel.LocalFree(descriptor)

    def dacl(self, path):
        size = wintypes.DWORD()
        self.api.GetFileSecurityW(str(path), 4, None, 0, ctypes.byref(size))
        descriptor = ctypes.create_string_buffer(size.value)
        if not self.api.GetFileSecurityW(str(path), 4, descriptor, size, ctypes.byref(size)):
            raise OSError('storage_acl_unavailable')
        text = ctypes.c_void_p()
        if not self.api.ConvertSecurityDescriptorToStringSecurityDescriptorW(descriptor, 1, 4, ctypes.byref(text), None):
            raise OSError('storage_acl_unavailable')
        try:
            return ctypes.wstring_at(text)
        finally:
            self.kernel.LocalFree(text)


def secure_directory(path):
    path = Path(path).absolute()
    reject_links(path)
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if sys.platform == 'win32':
        WindowsSecurity().restrict(path, directory=True)
    else:
        path.chmod(0o700)
    return path


def secure_file(path):
    path = Path(path).absolute()
    reject_links(path)
    if sys.platform == 'win32':
        WindowsSecurity().restrict(path)
    else:
        path.chmod(0o600)
