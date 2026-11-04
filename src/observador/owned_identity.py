"""Identity from a retained Popen capability, never from a PID lookup."""
import ctypes
from ctypes import wintypes as W
import subprocess
import sys
from .win32_handles import close_handle_once,declare_close_handle


class OwnedProcessIdentity:
    def __init__(self,process):
        if sys.platform!='win32' or not isinstance(process,subprocess.Popen) or process.poll() is not None:
            raise OSError('owned_identity_unavailable')
        self.source=process;self.handle=None;self.close_state='open'
        self.api=ctypes.WinDLL('kernel32',use_last_error=True);api=self.api
        declare_close_handle(api)
        for name,args,result in (
            ('GetCurrentProcess',[],W.HANDLE),('GetProcessId',[W.HANDLE],W.DWORD),
            ('WaitForSingleObject',[W.HANDLE,W.DWORD],W.DWORD),
            ('GetProcessTimes',[W.HANDLE]+[ctypes.POINTER(W.FILETIME)]*4,W.BOOL),
            ('DuplicateHandle',[W.HANDLE,W.HANDLE,W.HANDLE,ctypes.POINTER(W.HANDLE),W.DWORD,W.BOOL,W.DWORD],W.BOOL)):
            function=getattr(api,name);function.argtypes=args;function.restype=result
        original=int(process._handle);self.identity=self._read(original)
        if self.identity[0]!=process.pid:raise OSError('owned_identity_unavailable')
        current=api.GetCurrentProcess();out=W.HANDLE()
        if not api.DuplicateHandle(current,original,current,ctypes.byref(out),0x1000|0x100000,False,0):
            raise OSError('owned_identity_unavailable')
        self.handle=out.value

    def _read(self,handle):
        if self.api.WaitForSingleObject(handle,0)!=258:raise OSError('owned_identity_unavailable')
        pid=self.api.GetProcessId(handle);times=[W.FILETIME() for _ in range(4)]
        if not pid or not self.api.GetProcessTimes(handle,*(ctypes.byref(v) for v in times)):
            raise OSError('owned_identity_unavailable')
        return pid,(times[0].dwHighDateTime<<32|times[0].dwLowDateTime)

    def ticks(self):
        if self.close_state!='open' or self._read(self.handle)!=self.identity:
            raise OSError('owned_identity_unavailable')
        return self.identity[1]+504911232000000000

    def close(self):close_handle_once(self,self.api)


def creation_ticks(process):
    owner=OwnedProcessIdentity(process)
    try:return owner.ticks()
    finally:
        try:owner.close()
        except OSError as error:
            error.resource=owner
            raise
