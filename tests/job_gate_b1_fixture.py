"""Finite Issue36 fixtures. No runtime integration and no collective termination."""
import ctypes
from ctypes import wintypes as W
import json
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

if __name__ == '__main__':
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))

from isolated_process_supervision import NativeWorker, disarm_job
from observador.cleanup import CleanupStatus
from observador.win32_handles import close_handle_once
from observador.owned_channel_win32 import Kernel
from test_job_at_creation_windows import duplicate_process

# Bounded synthetic descendant; its private slot is never copied to diagnostic output.
ROW_SCRIPT = r'''
import subprocess,sys,time
from pathlib import Path
marker=Path(sys.argv[1]);desc=None
try:
    if marker.with_suffix('.desc').exists():
        desc=subprocess.Popen([sys.executable,'-I','-S','-B','-c','import time;time.sleep(10)'],
                              close_fds=True,creationflags=int(sys.argv[2]))
    value=str(int(desc._handle)) if desc else 'ready'
    marker.write_text(value,encoding='ascii')
    end=time.monotonic()+10
    while time.monotonic()<end and not marker.with_suffix('.stop').exists():time.sleep(.005)
finally:
    if desc:
        if desc.poll() is None:desc.terminate()
        desc.wait(timeout=2);desc._handle.Close()
'''


def members(api, handle):
    class List(ctypes.Structure):
        _fields_=[('assigned',W.DWORD),('listed',W.DWORD),('ids',ctypes.c_size_t*16)]
    value=List()
    if not api.QueryInformationJobObject(handle,3,ctypes.byref(value),ctypes.sizeof(value),None):
        raise OSError('b1_query_unconfirmed')
    if value.listed>16 or value.listed!=value.assigned:
        raise OSError('b1_list_incomplete')
    ids=set(value.ids[:value.listed])
    if len(ids)!=value.listed or 0 in ids:raise OSError('b1_list_incomplete')
    return ids


def observe(worker,phase,known):
    if worker.job.close_state=='closed':
        return dict(phase=phase,consultable=False,members=None,active=None,known_present=None,
                    unknown=None,stable=None,job_closed=True)
    api=worker.job.api
    left=members(api,worker.job.handle)
    accounting=ctypes.create_string_buffer(48)
    if not api.QueryInformationJobObject(worker.job.handle,1,accounting,48,None):
        raise OSError('b1_accounting_unconfirmed')
    right=members(api,worker.job.handle)
    active=W.DWORD.from_buffer(accounting,40).value
    known_ids={worker.api.GetProcessId(h) for h in known}
    if 0 in known_ids:raise OSError('b1_known_reference_unconfirmed')
    return dict(phase=phase,consultable=True,members=len(right),active=active,
                known_present=len(right & known_ids),unknown=len(right-known_ids),
                stable=left==right and active==len(right),job_closed=False)


def stop_owned(owner,api):
    if owner.handle is None:return
    result=api.WaitForSingleObject(owner.handle,0)
    if result==258:
        stopped=api.TerminateProcess(owner.handle,1)
        if not stopped and api.WaitForSingleObject(owner.handle,0)!=0:
            raise OSError('b1_known_stop_unconfirmed')
    elif result!=0:raise OSError('b1_known_wait_unconfirmed')
    if api.WaitForSingleObject(owner.handle,2000)!=0:raise OSError('b1_known_exit_unconfirmed')


def finish(worker,desc=None):
    """Disarm FIRST. No job.close()/TerminateJobObject, even on error."""
    status=CleanupStatus();disarmed=False
    try:
        disarm_job(worker.job);disarmed=True
    except Exception:status.fail('session')
    for owner in (desc,worker.process):
        if owner is not None:
            status.attempt('provider',lambda o=owner:stop_owned(o,worker.api))
    status.attempt('session',worker.job._confirm_empty)
    status.attempt('provider',worker.delete_attributes)
    if disarmed:
        status.attempt('session',lambda:close_handle_once(worker.job,worker.job.api))
    for owner in (desc,worker.thread,worker.process):
        if owner is not None:
            # Keep a process capability if exit could not be proved; thread can close independently.
            if owner is not worker.thread and owner.handle is not None:
                if worker.api.WaitForSingleObject(owner.handle,0)!=0:
                    status.fail('provider');continue
            status.attempt('provider',lambda o=owner:close_handle_once(o,worker.api))
    status.finish()
    if not status.confirmed:raise OSError('b1_cleanup_unconfirmed')


def matrix_row(directory,descendant,no_window):
    marker=Path(directory)/'row';worker=NativeWorker(marker);worker.fixture_script=ROW_SCRIPT
    worker.descendant_console=not no_window
    create=worker.api.CreateProcessW
    def create_selected(*args):
        values=list(args)
        if not no_window:values[5] &= ~0x08000000
        return create(*values)
    worker.api.CreateProcessW=create_selected
    def forbidden_bulk(*args):raise AssertionError('b1_bulk_forbidden')
    worker.job.api.TerminateJobObject=forbidden_bulk
    desc=None;phases=[]
    try:
        if descendant:marker.with_suffix('.desc').write_text('synthetic',encoding='ascii')
        phases.append(observe(worker,'before_create',[]))
        worker.create()
        known=[worker.process.handle]
        phases.append(observe(worker,'after_create',known))
        worker.verify();worker.delete_attributes()
        phases.append(observe(worker,'before_resume',known))
        worker.resume()
        phases.append(observe(worker,'after_resume',known))
        until=time.monotonic()+8
        while not marker.exists() and time.monotonic()<until:time.sleep(.005)
        if not marker.exists():raise OSError('b1_fixture_not_ready')
        # Buffered private file may be visible just before its tiny write completes.
        value=''
        while not value and time.monotonic()<until:
            value=marker.read_text(encoding='ascii');time.sleep(.005)
        if descendant:
            if not value.isdigit() or len(value)>20:raise OSError('b1_private_capability_rejected')
            desc=duplicate_process(Kernel(),worker.process.handle,int(value));known.append(desc.handle)
        elif value!='ready':raise OSError('b1_fixture_not_ready')
        phases.append(observe(worker,'ready',known))
        phases.append(observe(worker,'before_close',known))
    finally:finish(worker,desc)
    phases.append(observe(worker,'after_close',[]))
    return dict(origin='win32',descendant=descendant,no_window=no_window,
                ambient_job=worker.ambient_job,phases=phases,job_zero=worker.job.processes_confirmed,
                job_disarmed_before_close=True,bulk_termination_calls=0,
                own_processes_exited=True,resources_closed=True)


def owner(stage,marker):
    worker=NativeWorker(marker)
    try:
        if stage=='armed':
            worker.marker.with_suffix('.mode').write_text('blocked',encoding='ascii')
            worker.create();worker.verify();worker.delete_attributes()
        else:
            worker.start();until=time.monotonic()+8
            while worker.read()!='blocked_after_join':
                if time.monotonic()>=until:raise OSError('b1_fixture_not_ready')
                time.sleep(.005)
        snapshot=observe(worker,'death_barrier',[worker.process.handle])
        if not snapshot['stable']:raise OSError('b1_snapshot_unstable')
        if stage=='armed':
            if snapshot['unknown'] or snapshot['known_present']!=1:raise OSError('b1_armed_ownership_unconfirmed')
        else:disarm_job(worker.job)
        # PRIVATE only: consumed by our intermediary; diagnostic emitted later contains no slots.
        print(json.dumps(dict(slot=int(worker.process.handle),snapshot=snapshot,disarmed=stage=='disarmed')),flush=True)
        while True:
            if sys.stdin.readline().strip()=='stop':break
            time.sleep(.005)  # EOF of relay is not cooperative cleanup; observer kills both roots.
    finally:finish(worker)


def relay(stage,marker):
    from isolated_suspended_spawn import minimal_environment
    script=Path(__file__).resolve()
    process=subprocess.Popen([sys.executable,'-I','-S','-B',str(script),'owner',stage,str(marker)],
                             stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                             text=True,close_fds=True,env=minimal_environment(Path(marker).parent),
                             creationflags=subprocess.CREATE_NO_WINDOW)
    kernel=Kernel();child=None
    try:
        packet=json.loads(process.stdout.readline(2048))
        child=duplicate_process(kernel,int(process._handle),packet['slot'])
        print(json.dumps(dict(owner_slot=int(process._handle),worker_slot=child.handle,
                              snapshot=packet['snapshot'],disarmed=packet['disarmed'])),flush=True)
        sys.stdin.readline()
    finally:
        if process.poll() is None:
            process.stdin.write('stop\n');process.stdin.flush();process.wait(timeout=5)
        if child:close_handle_once(child,kernel.api)
        process.stdin.close();process.stdout.close()
        own=SimpleNamespace(handle=process._handle.Detach(),close_state='open')
        close_handle_once(own,kernel.api)


if __name__=='__main__':
    try:
        if sys.argv[1]=='row':
            print('ready',flush=True)
            sys.stdin.readline()
            result=matrix_row(sys.argv[4],sys.argv[2]=='desc',sys.argv[3]=='no_window')
            print(json.dumps(result,sort_keys=True),flush=True)
        elif sys.argv[1]=='owner':owner(sys.argv[2],Path(sys.argv[3]))
        elif sys.argv[1]=='relay':relay(sys.argv[2],Path(sys.argv[3]))
        else:raise ValueError()
    except Exception:raise SystemExit('b1_fixture_failed') from None
