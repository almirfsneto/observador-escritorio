"""AI03 experiment ONLY. Not packaged/imported by production launchers."""
import ctypes
from ctypes import wintypes as W
import os
import json
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

# Allow only this repository's source when run as the isolated crash fixture.
if __name__=='__main__':
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from observador.acceptance_metrics import OwnedJob
from observador.cleanup import CleanupStatus
from observador.win32_handles import close_handle_once,declare_close_handle
from isolated_cleanup_diagnostic import CleanupDiagnostic

SCRIPT='import subprocess,sys,time;subprocess.Popen([sys.executable,"-I","-S","-c","import time;time.sleep(40)"],close_fds=True);f=open(sys.argv[1],"xb");f.write(b"1");f.close();time.sleep(40)'


class Startup(ctypes.Structure):
    _fields_=[('cb',W.DWORD),('reserved',W.LPWSTR),('desktop',W.LPWSTR),('title',W.LPWSTR)]+[
        (n,W.DWORD) for n in ('x','y','xs','ys','xc','yc','fill','flags')]+[
        ('show',W.WORD),('reserved_size',W.WORD),('reserved_bytes',ctypes.POINTER(W.BYTE)),
        ('stdin',W.HANDLE),('stdout',W.HANDLE),('stderr',W.HANDLE)]


class ProcessInfo(ctypes.Structure):
    _fields_=[('process',W.HANDLE),('thread',W.HANDLE),('pid',W.DWORD),('tid',W.DWORD)]


def kernel_api():
    if sys.platform!='win32':raise OSError('isolated_windows_required')
    api=ctypes.WinDLL('kernel32',use_last_error=True);declare_close_handle(api)
    for name,args,result in (
        ('CreateProcessW',[W.LPCWSTR,W.LPWSTR,ctypes.c_void_p,ctypes.c_void_p,W.BOOL,W.DWORD,
                          ctypes.c_void_p,W.LPCWSTR,ctypes.POINTER(Startup),ctypes.POINTER(ProcessInfo)],W.BOOL),
        ('IsProcessInJob',[W.HANDLE,W.HANDLE,ctypes.POINTER(W.BOOL)],W.BOOL),
        ('ResumeThread',[W.HANDLE],W.DWORD),('TerminateProcess',[W.HANDLE,W.UINT],W.BOOL),
        ('WaitForSingleObject',[W.HANDLE,W.DWORD],W.DWORD),('GetProcessId',[W.HANDLE],W.DWORD),
        ('GetCurrentProcess',[],W.HANDLE),
        ('DuplicateHandle',[W.HANDLE,W.HANDLE,W.HANDLE,ctypes.POINTER(W.HANDLE),W.DWORD,W.BOOL,W.DWORD],W.BOOL)):
        f=getattr(api,name);f.argtypes=args;f.restype=result
    return api


def minimal_environment(directory):
    return {'SystemRoot':os.environ['SystemRoot'],'TEMP':str(directory),'TMP':str(directory)}


class SuspendedProbe:
    def __init__(self,marker):
        self.api=kernel_api();self.marker=Path(marker).absolute();self.assigned=False;self.job_attached=False
        self.status=CleanupStatus();self.process=SimpleNamespace(handle=None,close_state='open')
        self.thread=SimpleNamespace(handle=None,close_state='open');self.job=OwnedJob()
        self.diagnostic=CleanupDiagnostic();self.diagnostic_origin='win32'
        # Observe the actual calls without changing BOOLs, waits or failure policy.
        terminate=self.job.api.TerminateJobObject
        self.job.api.TerminateJobObject=lambda *a:self.diagnostic.boolean_call('job_terminate',lambda:terminate(*a))
        close=self.job.api.CloseHandle
        self.job.api.CloseHandle=lambda *a:self.diagnostic.boolean_call('job_handle_close',lambda:close(*a))
        confirm=self.job._confirm_empty
        def confirm_empty():
            try:confirm()
            except Exception:
                self.diagnostic.note('job_zero','failed');raise
            self.diagnostic.note('job_zero','passed')
        self.job._confirm_empty=confirm_empty
        startup=Startup();startup.cb=ctypes.sizeof(startup);startup.flags=0x100 # Null stdio.
        info=ProcessInfo()
        command=ctypes.create_unicode_buffer(subprocess.list2cmdline([sys.executable,'-I','-S','-c',SCRIPT,str(self.marker)]))
        env=minimal_environment(self.marker.parent)
        block=ctypes.create_unicode_buffer('\0'.join(k+'='+env[k] for k in sorted(env))+'\0\0')
        try:
            # CREATE_SUSPENDED | CREATE_NO_WINDOW | CREATE_UNICODE_ENVIRONMENT;
            # bInheritHandles=False: no endpoint, secret or job handle is delivered.
            if not self.api.CreateProcessW(sys.executable,command,None,None,False,0x4|0x08000000|0x400,
                                           block,str(Path(sys.executable).parent),ctypes.byref(startup),ctypes.byref(info)):
                raise OSError('isolated_spawn_failed')
            self.process.handle=info.process;self.thread.handle=info.thread
        except Exception:
            self.close();raise

    def assign(self):
        self.job.assign(SimpleNamespace(_handle=self.process.handle))
        self.job_attached=True
        member=W.BOOL()
        if not self.api.IsProcessInJob(self.process.handle,self.job.handle,ctypes.byref(member)) or not member.value:
            raise OSError('isolated_job_membership_unconfirmed')
        self.assigned=True

    def resume(self):
        if not self.assigned:raise OSError('isolated_resume_refused')
        if self.api.ResumeThread(self.thread.handle)!=1:raise OSError('isolated_resume_failed')

    def start(self,fault=None):
        if fault not in (None,'before_assign','after_assign'):
            raise ValueError('isolated_fault_rejected')
        if fault=='before_assign':raise OSError('injected_pre_resume_failure')
        self.assign()
        if fault=='after_assign':raise OSError('injected_pre_resume_failure')
        self.resume()

    def _confirm_process_exit(self):
        # Reuse the original 2-second process wait budget, including fallback.
        deadline=time.monotonic()+2
        killed_by_job=self.job_attached and self.job.cleanup_confirmed and self.job.processes_confirmed
        initial=2000 if killed_by_job else 0
        result=self.diagnostic.wait(lambda:self.api.WaitForSingleObject(self.process.handle,initial))
        if result==0:
            self.diagnostic.process_exit_confirmed=True
            return
        if result!=258:raise OSError('isolated_wait_failed')
        terminated=self.diagnostic.boolean_call('process_fallback',lambda:self.api.TerminateProcess(self.process.handle,1))
        remaining=max(0,min(2000,int((deadline-time.monotonic())*1000)))
        result=self.diagnostic.wait(lambda:self.api.WaitForSingleObject(self.process.handle,remaining))
        self.diagnostic.process_exit_confirmed=result==0
        if not terminated:
            self.diagnostic.after_failure_wait='passed' if result==0 else 'timeout' if result==258 else 'failed'
            # Keep the failed BOOL/error visible. Only the observed exit race can
            # be classified as recovered; no other API or handle error is forgiven.
            if (self.diagnostic.native_errors['process_fallback']=='access_denied' and result==0
                    and self.job.cleanup_confirmed and self.job.processes_confirmed):
                self.diagnostic.exit_race_confirmed=True
            else:raise OSError('isolated_stop_failed')
        if result!=0:raise OSError('isolated_stop_unconfirmed')

    def close(self):
        if self.status.finished:
            if not self.status.confirmed:raise OSError('isolated_cleanup_unconfirmed')
            return
        self.status.attempt('session',self.job.close)
        if self.process.handle is not None:
            try:self._confirm_process_exit()
            except Exception:
                self.status.fail('provider')
                # Diagnostic observation only, with no additional wait budget or
                # promotion of an earlier unclassified failure.
                try:
                    result=self.api.WaitForSingleObject(self.process.handle,0)
                    self.diagnostic.after_failure_wait='passed' if result==0 else 'timeout' if result==258 else 'failed'
                    if result==0:self.diagnostic.process_exit_confirmed=True
                except Exception:self.diagnostic.after_failure_wait='failed'
        for phase,owner in (('thread_handle_close',self.thread),('process_handle_close',self.process)):
            def close_owner(o=owner,p=phase):
                try:close_handle_once(o,self.api)
                except Exception:
                    self.diagnostic.note(p,'failed',native=True);raise
                self.diagnostic.note(p,'passed')
            self.status.attempt('provider',close_owner)
        self.status.finish()
        if not self.status.confirmed:
            print('ISOLATED_CLEANUP_DIAGNOSTIC '+json.dumps(self.diagnostic.snapshot(self),sort_keys=True),flush=True)
            raise OSError('isolated_cleanup_unconfirmed')


def duplicate_owned_launcher_child(api,launcher,slot):
    # A slot is only a locator in our retained launcher, not proof of identity.
    if not isinstance(launcher,subprocess.Popen) or launcher.poll() is not None or not 0<slot<2**64:
        raise OSError('isolated_launcher_unavailable')
    out=W.HANDLE()
    if not api.DuplicateHandle(int(launcher._handle),slot,api.GetCurrentProcess(),ctypes.byref(out),
                               1|0x1000|0x100000,False,0):raise OSError('isolated_duplicate_failed')
    return SimpleNamespace(handle=out.value,close_state='open')


if __name__=='__main__':
    if len(sys.argv)!=4 or sys.argv[1]!='--crash-fixture' or sys.argv[2] not in ('before_assign','after_assign'):
        raise SystemExit('isolated_arguments_rejected')
    probe=SuspendedProbe(sys.argv[3])
    try:
        if sys.argv[2]=='after_assign':probe.assign()
        print('ready '+str(probe.process.handle),flush=True) # Consumed privately by the test; never logged.
        sys.stdin.readline()
    finally:probe.close()
