"""Issue33 experiment ONLY: synthetic worker, retained capabilities, no runtime IPC."""
import ctypes
from ctypes import wintypes as W
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace

if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from isolated_job_creation import CreationProbe
from observador.win32_handles import close_handle_once

NONCE = 'synthetic-supervision-v1'  # Public test context, NOT authentication.
PHASES = ('creation', 'membership', 'communication', 'cancel', 'ownership', 'disarm',
          'job_terminate', 'process_terminate', 'process_wait', 'job_zero',
          'attributes', 'job_close', 'thread_close', 'process_close', 'artifacts')
STATES = ('normal_done', 'blocked_after_join', 'pong_blocked', 'cancel_without_ack', 'cancel_ack', 'late_done')
COMMANDS = ('ping', 'cancel', 'release')

WORKER_SCRIPT = r'''
import json,os,sys,threading,time
from pathlib import Path
path=Path(sys.argv[1]); command=path.with_suffix('.command')
mode=path.with_suffix('.mode').read_text(encoding='ascii')
if mode not in ('normal','blocked'):raise SystemExit(2)
nonce='synthetic-supervision-v1'
def emit(state,seq):
    data=json.dumps(dict(v=1,nonce=nonce,seq=seq,state=state),sort_keys=True).encode('ascii')
    tmp=path.with_suffix('.writing');tmp.write_bytes(data);os.replace(tmp,path)
lock=threading.Lock();lock.acquire()
worker=threading.Thread(target=lambda: (lock.acquire(),lock.release()),daemon=False)
worker.start()
if mode=='normal':lock.release()
worker.join(timeout=.05)
emit('blocked_after_join' if worker.is_alive() else 'normal_done',0)
if not worker.is_alive():raise SystemExit(0)
previous=0
while True:
    if command.exists():
        with command.open('rb') as stream:raw=stream.read(257)
        if len(raw)>256:raise SystemExit(3)
        packet=json.loads(raw)
        if type(packet) is not dict or set(packet)!={'v','nonce','seq','command'} or type(packet['v']) is not int or packet['v']!=1 or packet['nonce']!=nonce:raise SystemExit(3)
        seq=packet['seq'];op=packet['command']
        if type(seq) is not int or not 1<=seq<=64 or op not in ('ping','cancel','release'):raise SystemExit(3)
        if seq>previous:
            previous=seq
            if op=='ping':emit('pong_blocked',seq)
            elif op=='cancel':emit('cancel_without_ack',seq)
            else:
                lock.release();worker.join(timeout=.1)
                if worker.is_alive():raise SystemExit(4)
                emit('late_done',seq);break
    time.sleep(.005)
'''


class Ledger:
    """Monotone facts, not worker-provided cleanup assertions."""
    def __init__(self, origin):
        if origin not in ('win32', 'injected'):
            raise ValueError('supervision_origin_rejected')
        self.origin = origin
        self.errors = dict.fromkeys(PHASES, 0)
        self.expired = self.cancel_requested = self.cancel_ack = False
        self.started = self.join_insufficient = self.worker_exit = self.job_zero = False
        self.handles_closed = self.attributes_deleted = False
        self.ticks = self.pongs = 0
        self.expiry_before_stop = False
        self.unknown_members = self.bulk_refused = self.job_quarantined = False
        self.finished = False

    def fail(self, phase):
        if phase not in PHASES:
            raise ValueError('supervision_phase_rejected')
        self.errors[phase] = min(64, self.errors[phase] + 1)

    def expire(self):
        self.expired = True

    def acknowledge_cancel(self):
        if not self.cancel_requested:
            self.fail('communication')
            raise OSError('supervision_ack_rejected')
        self.cancel_ack = True

    def snapshot(self):
        physical = self.finished and self.worker_exit and self.job_zero and self.handles_closed and self.attributes_deleted
        return dict(kind='synthetic_process_supervision', origin=self.origin,
                    worker_state='deadline_expired' if self.expired else 'exited' if self.worker_exit else 'running',
                    deadline_expired=self.expired, expiry_before_stop=self.expiry_before_stop,
                    worker_started=self.started, join_insufficient=self.join_insufficient,
                    root_ticks=self.ticks, root_pongs=self.pongs, root_responsive=self.ticks >= 3,
                    ui_state='unknown', cancel_requested=self.cancel_requested, cancel_acknowledged=self.cancel_ack,
                    process_exit_confirmed=self.worker_exit, job_zero_confirmed=self.job_zero,
                    handles_closed=self.handles_closed, attributes_deleted=self.attributes_deleted,
                    physical_cleanup_confirmed=bool(physical),
                    cleanup_state='confirmed' if physical and not any(self.errors.values()) else 'cleanup_unconfirmed',
                    unknown_members=self.unknown_members, bulk_termination_refused=self.bulk_refused,
                    job_quarantined=self.job_quarantined, errors=dict(self.errors))


def decode_record(raw):
    try:
        if not isinstance(raw, bytes) or len(raw) > 256:
            raise ValueError()
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError()
                result[key] = value
            return result
        value = json.loads(raw, object_pairs_hook=unique)
        if (type(value) is not dict or set(value) != {'v', 'nonce', 'seq', 'state'}
                or type(value['v']) is not int or value['v'] != 1 or value['nonce'] != NONCE
                or type(value['seq']) is not int or not 0 <= value['seq'] <= 64
                or type(value['state']) is not str or value['state'] not in STATES):
            raise ValueError()
        return value
    except Exception:
        raise OSError('supervision_communication_rejected') from None


def job_members(api, job, known_handles):
    """Only query this anonymous Job; unknown member IDs never become capabilities."""
    class Members(ctypes.Structure):
        _fields_ = [('assigned', W.DWORD), ('listed', W.DWORD), ('ids', ctypes.c_size_t * 16)]
    value = Members()
    if not api.QueryInformationJobObject(job.handle, 3, ctypes.byref(value), ctypes.sizeof(value), None):
        raise OSError('supervision_members_unconfirmed')
    if value.listed > 16 or value.assigned != value.listed:
        raise OSError('supervision_members_unconfirmed')
    ids = set(value.ids[:value.listed])
    if len(ids) != value.listed:
        raise OSError('supervision_members_unconfirmed')
    known = {api.GetProcessId(h) for h in known_handles}
    if 0 in known:
        raise OSError('supervision_members_unconfirmed')
    return len(ids), bool(ids - known)


def disarm_job(job):
    # Preserve all limits except kill-on-close. Do NOT close a possibly shared Job armed.
    class Limits(ctypes.Structure):
        _fields_ = [('time1', ctypes.c_int64), ('time2', ctypes.c_int64), ('flags', W.DWORD),
                    ('min', ctypes.c_size_t), ('max', ctypes.c_size_t), ('active', W.DWORD),
                    ('affinity', ctypes.c_size_t), ('priority', W.DWORD), ('schedule', W.DWORD)]
    class Extended(ctypes.Structure):
        _fields_ = [('basic', Limits), ('io', ctypes.c_uint64 * 6), ('memory', ctypes.c_size_t * 4)]
    value = Extended()
    if not job.api.QueryInformationJobObject(job.handle, 9, ctypes.byref(value), ctypes.sizeof(value), None):
        raise OSError('supervision_disarm_unconfirmed')
    value.basic.flags &= ~0x2000
    if not job.api.SetInformationJobObject(job.handle, 9, ctypes.byref(value), ctypes.sizeof(value)):
        raise OSError('supervision_disarm_unconfirmed')
    check = Extended()
    if (not job.api.QueryInformationJobObject(job.handle, 9, ctypes.byref(check), ctypes.sizeof(check), None)
            or check.basic.flags & 0x2000):
        raise OSError('supervision_disarm_unconfirmed')


class NativeWorker(CreationProbe):
    fixture_script = WORKER_SCRIPT

    def __init__(self, marker, mode='blocked', **kwargs):
        self.ledger = Ledger('injected' if kwargs.get('api') is not None else 'win32')
        self.last_record = None
        self.request_seq = 0
        self.mode = mode
        if mode not in ('normal', 'blocked'):
            raise ValueError('supervision_mode_rejected')
        super().__init__(marker, **kwargs)

    def abort(self):
        self.ledger.fail('creation')
        super().abort()

    def start(self):
        try:
            self.marker.with_suffix('.mode').write_text(self.mode, encoding='ascii')
            self.create()
            self.verify()
            self.delete_attributes()
            self.resume()
        except Exception:
            self.ledger.fail('membership' if self.phases['membership'] == 'failed' else 'creation')
            raise OSError('supervision_start_unconfirmed') from None

    def alive(self):
        result = self.api.WaitForSingleObject(self.process.handle, 0)
        if result not in (0, 258):
            raise OSError('supervision_wait_unconfirmed')
        return result == 258

    def read(self):
        if not self.marker.exists():
            return None
        with self.marker.open('rb') as stream:
            value = decode_record(stream.read(257))
        if value == self.last_record:
            return None  # Atomic file delivery may be observed repeatedly.
        if value['seq'] != self.request_seq:
            raise OSError('supervision_sequence_rejected')
        if self.last_record is not None and value['seq'] <= self.last_record['seq']:
            raise OSError('supervision_sequence_rejected')
        self.last_record = value
        return value['state']

    def write(self, command):
        if command not in COMMANDS or self.request_seq >= 64:
            raise OSError('supervision_command_rejected')
        self.request_seq += 1
        value = dict(v=1, nonce=NONCE, seq=self.request_seq, command=command)
        path = self.marker.with_suffix('.command')
        tmp = self.marker.with_suffix('.sending')
        tmp.write_bytes(json.dumps(value, sort_keys=True).encode('ascii'))
        tmp.replace(path)

    def close(self):
        l = self.ledger
        if l.finished:
            if l.snapshot()['cleanup_state'] != 'confirmed':
                raise OSError('supervision_cleanup_unconfirmed')
            return
        def attempt(phase, action):
            try:
                action()
                return True
            except Exception:
                l.fail(phase)
                return False
        attempt('attributes', self.delete_attributes)
        l.attributes_deleted = self.attribute_state == 'deleted'
        job = self.job
        safe = job is not None and job.handle is not None
        if safe:
            try:
                count, unknown = job_members(self.api_with_job(), job,
                                             [self.process.handle] if self.process.handle is not None else [])
                if unknown:
                    l.unknown_members = True
                    raise OSError('supervision_ownership_unconfirmed')
                if self.process.handle is not None and self.alive():
                    member = W.BOOL()
                    if (not self.api.IsProcessInJob(self.process.handle, job.handle, ctypes.byref(member))
                            or not member.value or count == 0):
                        raise OSError('supervision_ownership_unconfirmed')
            except Exception:
                safe = False
                l.fail('ownership')
                l.bulk_refused = True
        disarmed = False
        if job is not None and job.handle is not None:
            if safe:
                def terminate_job():
                    if not job.api.TerminateJobObject(job.handle, 1):
                        raise OSError('supervision_job_stop_unconfirmed')
                attempt('job_terminate', terminate_job)
            else:
                disarmed = attempt('disarm', lambda: disarm_job(job))
                l.job_quarantined = not disarmed
        if self.process.handle is not None:
            if not safe or l.errors['job_terminate']:
                def terminate_known():
                    if self.alive() and not self.api.TerminateProcess(self.process.handle, 1):
                        raise OSError('supervision_process_stop_unconfirmed')
                attempt('process_terminate', terminate_known)
            def confirm_exit():
                if self.api.WaitForSingleObject(self.process.handle, 2000) != 0:
                    raise OSError('supervision_process_exit_unconfirmed')
                l.worker_exit = True
            attempt('process_wait', confirm_exit)
        else:
            l.worker_exit = True  # No successful process creation.
        if job is not None and job.handle is not None:
            attempt('job_zero', job._confirm_empty)
            l.job_zero = job.processes_confirmed
            if safe or disarmed:
                attempt('job_close', lambda: close_handle_once(job, job.api))
        else:
            l.job_zero = True  # No Job allocated.
        for phase, owner in (('thread_close', self.thread), ('process_close', self.process)):
            attempt(phase, lambda o=owner: close_handle_once(o, self.api))
        l.handles_closed = (self.thread.close_state == self.process.close_state == 'closed'
                            and (job is None or job.close_state == 'closed'))
        def artifacts():
            for path in (self.marker, *(self.marker.with_suffix(s) for s in ('.mode', '.command', '.writing', '.sending'))):
                path.unlink(missing_ok=True)
        attempt('artifacts', artifacts)
        l.finished = True
        if l.snapshot()['cleanup_state'] != 'confirmed':
            raise OSError('supervision_cleanup_unconfirmed')

    def api_with_job(self):
        return SimpleNamespace(QueryInformationJobObject=self.job.api.QueryInformationJobObject,
                               GetProcessId=self.api.GetProcessId)


class Supervisor:
    def __init__(self, backend, *, clock=time.monotonic, idle=lambda: time.sleep(.005)):
        self.backend = backend
        self.ledger = backend.ledger
        self.clock, self.idle = clock, idle

    def run(self, *, duration=.2, startup_budget=8, cancel_event=None, on_tick=None):
        l = self.ledger
        reason = 'creation'
        try:
            self.backend.start()
            reason = 'communication'
            startup_end = self.clock() + startup_budget
            deadline = None
            ping_sent = False
            while True:
                l.ticks = min(100000, l.ticks + 1)
                if on_tick:
                    on_tick(self)
                state = self.backend.read()
                if state is not None:
                    if state == 'cancel_ack':
                        l.acknowledge_cancel()
                    elif state == 'cancel_without_ack':
                        l.fail('cancel')
                        break
                    elif state == 'pong_blocked':
                        l.pongs += 1
                    elif state in ('normal_done', 'blocked_after_join'):
                        if l.started:
                            raise OSError('supervision_start_repeated')
                        l.started = True
                        l.join_insufficient = state == 'blocked_after_join'
                        deadline = self.clock() + duration
                    elif state == 'late_done':
                        pass  # Exit still requires kernel evidence; expiry is never reset.
                if deadline is not None and self.clock() >= deadline:
                    l.expire()  # Monotone; happens BEFORE cancellation or teardown.
                    l.expiry_before_stop = True
                    break
                if not self.backend.alive():
                    if not l.started:
                        final_state = self.backend.read()
                        if final_state not in ('normal_done', 'blocked_after_join'):
                            raise OSError('supervision_start_unconfirmed')
                        l.started = True
                        l.join_insufficient = final_state == 'blocked_after_join'
                    break
                if cancel_event is not None and cancel_event.is_set():
                    l.cancel_requested = True
                    self.backend.write('cancel')
                    # Request alone is not cancellation/exit; backend stays blocked.
                    l.fail('cancel')
                    break
                if l.started and l.join_insufficient and not ping_sent:
                    self.backend.write('ping')
                    ping_sent = True
                if not l.started and self.clock() >= startup_end:
                    l.fail('communication')
                    l.expire()
                    l.expiry_before_stop = True
                    break
                self.idle()
                reason = 'communication'
        except Exception:
            l.fail(reason)
        finally:
            try:
                self.backend.close()
            except Exception:
                if not any(l.errors.values()):
                    l.fail('process_wait')
        return l.snapshot()


def crash_fixture(stage, marker):
    if stage not in ('before_start', 'after_start', 'nested_after_start'):
        raise OSError('supervision_stage_rejected')
    if stage == 'nested_after_start':
        print('prepare', flush=True)
        if sys.stdin.readline().strip() != 'create':
            raise OSError('supervision_control_rejected')
    worker = NativeWorker(marker)
    try:
        if stage == 'before_start':
            worker.marker.with_suffix('.mode').write_text('blocked', encoding='ascii')
            worker.create()
            worker.verify()
            worker.delete_attributes()
        else:
            worker.start()
            until = time.monotonic() + 8
            while True:
                state = worker.read()
                if state == 'blocked_after_join':
                    break
                if time.monotonic() >= until:
                    raise OSError('supervision_start_unconfirmed')
                time.sleep(.005)
        count, unknown = job_members(worker.api_with_job(), worker.job, [worker.process.handle])
        if unknown or count != 1:
            raise OSError('supervision_ownership_unconfirmed')
        # Private capability transfer, consumed only by root; never forwarded to logs.
        print(json.dumps(dict(slot=int(worker.process.handle), stage=stage,
                              blocked=stage!='before_start', ownership_checked=True)), flush=True)
        if sys.stdin.readline().strip() != 'cleanup':
            raise OSError('supervision_control_rejected')
    finally:
        worker.close()


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('supervision_arguments_rejected')
    try:
        crash_fixture(sys.argv[1], Path(sys.argv[2]))
    except Exception:
        raise SystemExit('supervision_fixture_failed') from None
