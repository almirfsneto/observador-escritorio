"""Opt-in isolated Windows IPC experiment. Never connects to the observer or inbox.

Peer authentication is an owned-child CAPABILITY argument: a retained process
handle, explicit inheritance list and bootstrap possession bind the proof to the
child we launched. No claim against same-token process injection/handle theft or
administrator. Blocking laboratory API; not called by Tk or acceptance v1.
"""
from concurrent.futures import Future,TimeoutError
from copy import deepcopy
from pathlib import Path
import queue
import secrets
import subprocess
import sys
import threading
import time
from uuid import uuid4

from . import owned_channel_protocol as wire
from .owned_channel_win32 import Kernel
from .acceptance_metrics import OwnedJob
from .private_directory import reject_links

_LAUNCH_LOCK=threading.Lock()
FAULTS={'normal','wrong_key','wrong_identity','bad_mac','short_mac','duplicate','nan','oversize','truncated','flood','stall','stall_sample','exit'}


class OwnedSyntheticChannel:
    """Disabled until start(); one worker, one outstanding operation, <=64 messages.

    The only executable/entrypoint are this interpreter and the owned IPC fixture.
    No attach-to-PID, caller executable, named endpoint, socket or observer adapter.
    """
    def __init__(self,*,ttl_ms=30000,io_timeout=2.0,fault='normal',decoy_handles=()):
        wire.integer(ttl_ms,1000,900000)
        if type(io_timeout) not in (int,float) or not .2<=io_timeout<=5 or fault not in FAULTS:wire.reject()
        if type(decoy_handles) is not tuple or len(decoy_handles)>8:wire.reject()
        for handle in decoy_handles:wire.integer(handle,1)
        self.ttl_ms=ttl_ms;self.io_timeout=float(io_timeout);self.fault=fault;self.decoys=decoy_handles
        self.state='disabled';self._key=None;self._process=None;self._job=None;self._kernel=None
        self._thread=None;self._cancel_handle=None;self._stop=threading.Event();self._queue=queue.Queue(maxsize=1)
        self._operation=threading.Lock();self._lock=threading.RLock();self._handles=set()
        self._epoch=str(uuid4());self.session=str(uuid4());self._generation=0;self._sequence=0;self._ordinal=0
        self._nonce=None;self._binding=None;self._deadline=None;self._last_clock=None;self._messages=0
        self._peer_verified=False;self._bootstrap_closed=False;self._shutdown_confirmed=True
        self._last_error='none';self._proof_flags=None;self._phase='disabled';self._cleanup_errors=0

    @property
    def process(self):return self._process

    def snapshot(self):
        with self._lock:
            return dict(state=self.state,owned_peer_authenticated=self._peer_verified,
                        inherited_handle_count=4 if self._binding else 0,bootstrap_closed=self._bootstrap_closed,
                        proof_flags=deepcopy(self._proof_flags),messages=self._messages,
                        worker_alive=bool(self._thread and self._thread.is_alive()),
                        process_running=bool(self._process and self._process.poll() is None),
                        shutdown_confirmed=self._shutdown_confirmed,last_error=self._last_error,phase=self._phase,
                        cleanup_errors=self._cleanup_errors,
                        fixture_exit_code=self._process.returncode if self._process else None,
                        adapter_enabled=False,inbox_ack=False,uia_pause_ack=False)

    def _guard(self):
        now=time.monotonic()
        if self._stop.is_set():raise OSError('owned_channel_cancelled')
        if self._last_clock is not None and now<self._last_clock:raise OSError('owned_channel_clock_rejected')
        self._last_clock=now
        if self._deadline is not None and now>=self._deadline:raise OSError('owned_channel_expired')
        if self._process and self._process.poll() is not None:raise OSError('owned_peer_exited')

    def assert_owned_peer(self,process):
        # Compare the object retained by the launcher, not a PID supplied in JSON.
        if process is not self._process or self._binding is None or self._kernel is None:wire.reject()
        if self._kernel.identity(int(process._handle))!=self._binding['child']:wire.reject()

    def _take_handle(self,value):self._handles.add(value);return value

    def _close_handle(self,value):
        if value in self._handles:
            self._kernel.close(value);self._handles.remove(value)

    def _launch(self):
        if sys.platform!='win32':raise OSError('owned_channel_windows_required')
        self._phase='launch';self._kernel=Kernel();self._deadline=time.monotonic()+self.ttl_ms/1000
        with self._lock:self._cancel_handle=self._kernel.own_thread_handle()
        script=Path(__file__).with_name('owned_channel_child.py').absolute()
        reject_links(script);reject_links(Path(sys.executable).absolute())
        digest=wire.fixture_digest()
        pairs=[]
        for _ in range(3):
            pair=self._kernel.pipe();pairs.append(pair)
            for handle in pair:self._take_handle(handle)
        (command_read,self._command_write),(self._response_read,response_write),(key_read,key_write)=pairs
        parent_handle=self._take_handle(self._kernel.parent_query_handle())
        inherited=[command_read,response_write,key_read,parent_handle]
        allowed_handles=tuple(inherited)
        if any(self._kernel.flags(handle) is None for handle in self.decoys):wire.reject()
        parent_identity=self._kernel.identity(self._kernel.current())
        startup=subprocess.STARTUPINFO();startup.lpAttributeList={'handle_list':inherited}
        # No stdio redirection: CPython would add three handles to handle_list.
        # Null standard handles also prevent child exceptions from becoming logs.
        startup.dwFlags|=subprocess.STARTF_USESTDHANDLES
        startup.hStdInput=startup.hStdOutput=startup.hStdError=0
        args=[sys.executable,'-I','-S','-B',str(script),'--owned-ipc-fixture',
              *(str(h) for h in inherited),self.fault]
        self._job=OwnedJob()
        with _LAUNCH_LOCK:
            try:
                for handle in inherited:self._kernel.inherit(handle,True)
                self._process=subprocess.Popen(args,close_fds=True,startupinfo=startup,
                                               creationflags=subprocess.CREATE_NO_WINDOW)
            finally:
                for handle in allowed_handles:self._kernel.inherit(handle,False)
        self._phase='identity';self._job.assign(self._process)
        delivered=startup.lpAttributeList['handle_list']
        if len(delivered)!=4 or set(delivered)!=set(allowed_handles):wire.reject()
        self._decoys_absent=self._kernel.no_inherited_objects(int(self._process._handle),self.decoys)
        if not self._decoys_absent:wire.reject()
        child_identity=self._kernel.identity(int(self._process._handle))
        if child_identity['pid']!=self._process.pid or child_identity['session_slot']!=parent_identity['session_slot']:wire.reject()
        if wire.fixture_digest()!=digest:wire.reject()
        self._binding=dict(parent=parent_identity,child=child_identity,fixture_sha256=digest,ttl_ms=self.ttl_ms,handle_count=4)
        for handle in inherited:self._close_handle(handle)
        self._phase='bootstrap';self._key=secrets.token_bytes(32)
        self._kernel.write(key_write,self._key,min(self._deadline,time.monotonic()+5),self._guard)
        self._close_handle(key_write);self._bootstrap_closed=True
        self._phase='handshake';self._pair()
        self._phase='commands';return self._command('start',0)

    def _packet(self,kind,payload,sequence):
        return wire.seal(self._key,'parent',kind=kind,epoch=self._epoch,session=self.session,
                         generation=self._generation,sequence=sequence,nonce=self._nonce,
                         binding=self._binding,payload=payload)

    def _send_raw(self,packet,timeout):
        if type(packet) is not bytes or not 0<len(packet)<=wire.MAX_WIRE+4:wire.reject()
        self._kernel.write(self._command_write,packet,min(self._deadline,time.monotonic()+timeout),self._guard)

    def _exchange(self,raw,kind,sequence,timeout):
        self._guard();self.assert_owned_peer(self._process)
        if self._messages>=wire.MAX_MESSAGES:wire.reject()
        self._messages+=1
        self._send_raw(wire.length_header(len(raw))+raw,timeout)
        until=min(self._deadline,time.monotonic()+timeout)
        size=wire.frame_size(self._kernel.read(self._response_read,4,until,self._guard))
        response=self._kernel.read(self._response_read,size,until,self._guard)
        result=wire.verify(response,self._key,'child',kind=kind,epoch=self._epoch,session=self.session,
                           generation=self._generation,sequence=sequence,nonce=self._nonce,binding=self._binding)
        self.assert_owned_peer(self._process)
        return result

    def _pair(self):
        self._generation+=1;self._nonce=secrets.token_hex(32);self._sequence=0
        proof=self._exchange(self._packet('hello',{'action':'pair'},0),'proof',0,5)
        self._proof_flags={k:v for k,v in proof.items() if k!='action'}
        self._proof_flags['decoys_absent']=self._decoys_absent
        self._peer_verified=True

    def _command(self,action,ordinal):
        self._sequence+=1
        expected_state={'pause':'paused','stop':'closed'}.get(action,'active')
        response=self._exchange(self._packet('command',dict(action=action,ordinal=ordinal),self._sequence),
                                'ack',self._sequence,self.io_timeout)
        if response['action']!=action or response['ordinal']!=ordinal or response['state']!=expected_state:wire.reject()
        self.state=expected_state
        if action=='sample':self._ordinal=ordinal
        return response

    def _worker(self):
        try:
            while not self._stop.is_set():
                try:item=self._queue.get(timeout=.02)
                except queue.Empty:
                    if self._process:self._guard()
                    continue
                op,value,future=item
                try:
                    if op=='start':result=self._launch()
                    elif op=='resume':
                        if self.state!='paused':wire.reject()
                        self._pair();result=self._command('resume',0)
                    elif op=='raw':
                        self._send_raw(value,self.io_timeout)
                        until=min(self._deadline,time.monotonic()+self.io_timeout)
                        # Any reply to a deliberately invalid frame is still validated/rejected.
                        size=wire.frame_size(self._kernel.read(self._response_read,4,until,self._guard))
                        wire.decode(self._kernel.read(self._response_read,size,until,self._guard));wire.reject()
                    elif op=='check_peer':self.assert_owned_peer(value);result=True
                    elif op=='sample':
                        if self.state!='active':wire.reject()
                        result=self._command('sample',self._ordinal+1)
                    elif op=='pause':
                        if self.state!='active':wire.reject()
                        result=self._command('pause',0)
                    elif op=='stop':result=self._command('stop',0)
                    else:wire.reject()
                    future.set_result(result)
                    if self.state=='closed':break
                except Exception:
                    future.set_exception(wire.ChannelError('owned_channel_failed_closed_at_'+self._phase));raise
        except Exception:
            self._last_error='failed_closed';self.state='failed'
        finally:
            self._cleanup()

    def _cleanup_problem(self):
        self._shutdown_confirmed=False;self._cleanup_errors+=1
        self._last_error='cleanup_unconfirmed';self.state='failed'

    def _cleanup(self):
        self._stop.set();self._peer_verified=False;self._key=None
        if self._process and self._process.poll() is None:
            try:self._process.kill()
            except OSError:pass
        if self._job:
            try:self._job.close()
            except OSError:self._cleanup_problem()
        if self._process:
            try:self._process.wait(timeout=2)
            except (OSError,subprocess.TimeoutExpired):self._cleanup_problem()
        if self._kernel:
            for handle in tuple(self._handles):
                try:self._close_handle(handle)
                except OSError:self._cleanup_problem()
        with self._lock:
            if self._cancel_handle is not None:
                try:self._kernel.close(self._cancel_handle)
                except OSError:self._cleanup_problem()
                finally:self._cancel_handle=None # Never retry a numeric slot with uncertain ownership.
        while True:
            try:_,_,future=self._queue.get_nowait()
            except queue.Empty:break
            if not future.done():future.set_exception(wire.ChannelError('owned_channel_failed_closed'))

    def _call(self,op,value=None):
        if not self._operation.acquire(blocking=False):raise wire.ChannelError('owned_channel_busy')
        try:
            if op=='start':
                if self.state!='disabled':wire.reject()
                self.state='starting';self._thread=threading.Thread(target=self._worker,daemon=True)
                self._thread.start()
            elif not self._thread or not self._thread.is_alive() or self._stop.is_set():wire.reject()
            future=Future();self._queue.put_nowait((op,value,future))
            try:return future.result(timeout=8 if op in ('start','resume') else self.io_timeout+2)
            except TimeoutError:
                self.close();raise wire.ChannelError('owned_channel_timeout') from None
        finally:self._operation.release()

    def start(self):return self._call('start')
    def sample(self):return self._call('sample')
    def pause(self):return self._call('pause')
    def resume(self):return self._call('resume')
    def stop(self):return self._call('stop')

    def close(self):
        self._stop.set()
        if self._process and self._process.poll() is None:
            try:self._process.kill()
            except OSError:pass
        with self._lock:
            if self._kernel:
                try:self._kernel.cancel_thread(self._cancel_handle)
                except OSError:self._cleanup_problem()
        if self._thread and self._thread is not threading.current_thread():self._thread.join(timeout=3)
        self._shutdown_confirmed=self._shutdown_confirmed and not bool(self._thread and self._thread.is_alive())
        if self.state!='failed':self.state='closed'
