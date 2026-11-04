"""Win32 handle IO for OWNED laboratory children only. Never enumerates processes."""
import ctypes
from ctypes import wintypes as W
import hashlib
import os
import sys
import time


class Kernel:
    def __init__(self):
        if sys.platform!='win32':raise OSError('owned_channel_windows_required')
        self.api=ctypes.WinDLL('kernel32',use_last_error=True)
        api=self.api
        declarations={
            'CreatePipe':([ctypes.POINTER(W.HANDLE),ctypes.POINTER(W.HANDLE),ctypes.c_void_p,W.DWORD],W.BOOL),
            'SetHandleInformation':([W.HANDLE,W.DWORD,W.DWORD],W.BOOL),
            'GetHandleInformation':([W.HANDLE,ctypes.POINTER(W.DWORD)],W.BOOL),
            'CloseHandle':([W.HANDLE],W.BOOL),
            'ReadFile':([W.HANDLE,ctypes.c_void_p,W.DWORD,ctypes.POINTER(W.DWORD),ctypes.c_void_p],W.BOOL),
            'WriteFile':([W.HANDLE,ctypes.c_void_p,W.DWORD,ctypes.POINTER(W.DWORD),ctypes.c_void_p],W.BOOL),
            'PeekNamedPipe':([W.HANDLE,ctypes.c_void_p,W.DWORD,ctypes.c_void_p,ctypes.POINTER(W.DWORD),ctypes.c_void_p],W.BOOL),
            'GetCurrentProcess':([],W.HANDLE),
            'DuplicateHandle':([W.HANDLE,W.HANDLE,W.HANDLE,ctypes.POINTER(W.HANDLE),W.DWORD,W.BOOL,W.DWORD],W.BOOL),
            'GetProcessId':([W.HANDLE],W.DWORD),
            'GetProcessTimes':([W.HANDLE]+[ctypes.POINTER(W.FILETIME)]*4,W.BOOL),
            'QueryFullProcessImageNameW':([W.HANDLE,W.DWORD,W.LPWSTR,ctypes.POINTER(W.DWORD)],W.BOOL),
            'ProcessIdToSessionId':([W.DWORD,ctypes.POINTER(W.DWORD)],W.BOOL),
            'WaitForSingleObject':([W.HANDLE,W.DWORD],W.DWORD),
            'OpenThread':([W.DWORD,W.BOOL,W.DWORD],W.HANDLE),
            'CancelSynchronousIo':([W.HANDLE],W.BOOL),
            'CreateEventW':([ctypes.c_void_p,W.BOOL,W.BOOL,W.LPCWSTR],W.HANDLE),
        }
        for name,(args,result) in declarations.items():
            function=getattr(api,name);function.argtypes=args;function.restype=result

    def pipe(self):
        read,write=W.HANDLE(),W.HANDLE()
        if not self.api.CreatePipe(ctypes.byref(read),ctypes.byref(write),None,65536):raise OSError('owned_pipe_failed')
        return int(read.value),int(write.value)

    def close(self,handle):
        if handle is not None:self.api.CloseHandle(handle)

    def inherit(self,handle,allowed):
        if not self.api.SetHandleInformation(handle,1,int(allowed)):raise OSError('owned_handle_flags_failed')

    def flags(self,handle):
        flags=W.DWORD()
        return flags.value if self.api.GetHandleInformation(handle,ctypes.byref(flags)) else None

    def current(self):return self.api.GetCurrentProcess()

    def parent_query_handle(self):
        result=W.HANDLE();current=self.current()
        if not self.api.DuplicateHandle(current,current,current,ctypes.byref(result),0x1000|0x100000,False,0):
            raise OSError('owned_parent_handle_failed')
        return int(result.value)

    def alive(self,handle):return self.api.WaitForSingleObject(handle,0)==258

    def identity(self,handle):
        if not self.alive(handle):raise OSError('owned_peer_exited')
        pid=self.api.GetProcessId(handle)
        values=[W.FILETIME() for _ in range(4)]
        if not pid or not self.api.GetProcessTimes(handle,*(ctypes.byref(v) for v in values)):raise OSError('owned_identity_failed')
        size=W.DWORD(32768);image=ctypes.create_unicode_buffer(size.value)
        if not self.api.QueryFullProcessImageNameW(handle,0,image,ctypes.byref(size)):raise OSError('owned_identity_failed')
        if os.path.normcase(image.value)!=os.path.normcase(os.path.abspath(sys.executable)):
            raise OSError('owned_image_path_rejected')
        slot=W.DWORD()
        if not self.api.ProcessIdToSessionId(pid,ctypes.byref(slot)):raise OSError('owned_identity_failed')
        with open(image.value,'rb') as stream:
            digest=hashlib.file_digest(stream,'sha256').hexdigest()
        created=values[0]
        return dict(pid=pid,start_ticks=(created.dwHighDateTime<<32|created.dwLowDateTime)+504911232000000000,
                    session_slot=slot.value,image_sha256=digest)

    def cancel_thread(self,native_id):
        if native_id is None:return
        handle=self.api.OpenThread(1,False,native_id) # THREAD_TERMINATE for CancelSynchronousIo
        if handle:
            try:self.api.CancelSynchronousIo(handle)
            finally:self.close(handle)

    def read(self,handle,size,until,guard):
        result=bytearray()
        while len(result)<size:
            guard()
            if time.monotonic()>=until:raise OSError('owned_io_timeout')
            available=W.DWORD()
            if not self.api.PeekNamedPipe(handle,None,0,None,ctypes.byref(available),None):raise OSError('owned_pipe_eof')
            if not available.value:
                time.sleep(.005);continue
            count=min(size-len(result),available.value,4096)
            buffer=ctypes.create_string_buffer(count);read=W.DWORD()
            if not self.api.ReadFile(handle,buffer,count,ctypes.byref(read),None) or not read.value:raise OSError('owned_pipe_eof')
            result.extend(buffer.raw[:read.value])
        return bytes(result)

    def expect_eof(self,handle,until,guard):
        while time.monotonic()<until:
            guard();available=W.DWORD()
            if not self.api.PeekNamedPipe(handle,None,0,None,ctypes.byref(available),None):
                if ctypes.get_last_error()==109:return
                raise OSError('owned_bootstrap_failed')
            if available.value:raise OSError('owned_bootstrap_length_failed')
            time.sleep(.005)
        raise OSError('owned_io_timeout')

    def write(self,handle,data,until,guard):
        offset=0
        while offset<len(data):
            guard()
            if time.monotonic()>=until:raise OSError('owned_io_timeout')
            chunk=data[offset:offset+4096];buffer=ctypes.create_string_buffer(chunk);written=W.DWORD()
            if not self.api.WriteFile(handle,buffer,len(chunk),ctypes.byref(written),None) or not written.value:raise OSError('owned_pipe_eof')
            offset+=written.value
        return offset
