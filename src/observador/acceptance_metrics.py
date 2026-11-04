"""Sample only explicitly registered owned process handles, never enumerate processes."""
import ctypes
from ctypes import wintypes
import subprocess
import sys
import time

from .win32_handles import close_handle_once, declare_close_handle


class ProcessProbe:
    def __init__(self, process=None):
        if sys.platform != 'win32':
            raise OSError('metrics_unavailable')
        if process is not None and (not isinstance(process, subprocess.Popen) or process.poll() is not None):
            raise OSError('metrics_unavailable')
        self.handle = None
        self.close_state = 'open'
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        declare_close_handle(self.kernel)
        self.kernel.GetCurrentProcess.restype = wintypes.HANDLE
        self.kernel.DuplicateHandle.argtypes = [wintypes.HANDLE, wintypes.HANDLE, wintypes.HANDLE,
            ctypes.POINTER(wintypes.HANDLE), wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        self.kernel.DuplicateHandle.restype = wintypes.BOOL
        self.kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        self.kernel.WaitForSingleObject.restype = wintypes.DWORD
        self.kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
        self.kernel.GetProcessTimes.restype = wintypes.BOOL
        self.kernel.K32GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
        self.kernel.K32GetProcessMemoryInfo.restype = wintypes.BOOL
        current = self.kernel.GetCurrentProcess()
        # Retain process locally throughout duplication. No OpenProcess/PID lookup.
        source = int(process._handle) if process is not None else current
        self.creation = self._creation(source)
        duplicate = wintypes.HANDLE()
        if not self.kernel.DuplicateHandle(current, source, current, ctypes.byref(duplicate),
                                           0x1000 | 0x10 | 0x100000, False, 0):
            raise OSError('metrics_unavailable')
        self.handle = duplicate.value

    def _creation(self, handle):
        if self.kernel.WaitForSingleObject(handle, 0) != 258:
            raise OSError('metrics_unavailable')
        values = [wintypes.FILETIME() for _ in range(4)]
        if not self.kernel.GetProcessTimes(handle, *(ctypes.byref(v) for v in values)):
            raise OSError('metrics_unavailable')
        return values[0].dwHighDateTime << 32 | values[0].dwLowDateTime

    def read(self):
        if self.close_state != 'open' or self._creation(self.handle) != self.creation:
            raise OSError('metrics_unavailable')
        class Memory(ctypes.Structure):
            _fields_ = [('cb', wintypes.DWORD), ('faults', wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in ('peak', 'working', 'ppeak', 'p', 'npeak', 'n', 'page', 'pagepeak')]
        created, exited, kernel, user = (wintypes.FILETIME() for _ in range(4))
        if not self.kernel.GetProcessTimes(self.handle, ctypes.byref(created), ctypes.byref(exited),
                                            ctypes.byref(kernel), ctypes.byref(user)):
            raise OSError('metrics_unavailable')
        memory = Memory()
        memory.cb = ctypes.sizeof(memory)
        if not self.kernel.K32GetProcessMemoryInfo(self.handle, ctypes.byref(memory), memory.cb):
            raise OSError('metrics_unavailable')
        ticks = lambda value: value.dwHighDateTime << 32 | value.dwLowDateTime
        return (ticks(created), (ticks(kernel) + ticks(user)) / 10_000_000,
                int(memory.working), int(memory.peak))

    def close(self):
        close_handle_once(self, self.kernel)


class OwnedSampler:
    def __init__(self, session, *, probe_factory=ProcessProbe, clock=time.monotonic):
        self.session, self.factory, self.clock = session, probe_factory, clock
        self.probes = {}
        self.previous = {}
        self.closed = False
        self.failed_probes = {}
        self.last_sample = float('-inf')

    def register(self, role, process=None, *, current_controller=False):
        if self.closed:
            return
        if role not in self.session['metrics']['processes'] or role in self.probes or role in self.failed_probes:
            return
        if current_controller != (role == 'controller'):
            raise ValueError('owned_role_required')
        if not current_controller and (process is None or process.poll() is not None):
            return
        try:
            probe = self.factory(None if current_controller else process)
            first = probe.read()
            self.probes[role] = probe
            self.previous[role] = (self.clock(), first[0], first[1])
            self._record(role, first, None)
        except OSError:
            if 'probe' in locals():
                self._close_probe(role, probe)
            self.session['metrics']['processes'][role]['availability'] = 'unavailable'

    def _close_probe(self, role, probe):
        try:
            probe.close()
        except OSError:
            self.failed_probes[role] = probe
            self.session['metrics']['processes'][role]['availability'] = 'unavailable'

    @property
    def cleanup_confirmed(self):
        return self.closed and not self.failed_probes

    def _record(self, role, values, cpu):
        metric = self.session['metrics']['processes'][role]
        metric['availability'] = 'sampled'
        metric['samples'] += 1
        if cpu is not None:
            metric['cpu_single_core_sample_peak_percent'] = max(metric['cpu_single_core_sample_peak_percent'] or 0, cpu)
        metric['ram_working_set_sample_peak_bytes'] = max(metric['ram_working_set_sample_peak_bytes'] or 0, values[2])
        metric['ram_working_set_process_lifetime_peak_bytes'] = max(metric['ram_working_set_process_lifetime_peak_bytes'] or 0, values[3])

    def sample(self, *, force=False):
        if self.closed:
            return
        now = self.clock()
        if not force and now - self.last_sample < .5:
            return
        self.last_sample = now
        for role, probe in list(self.probes.items()):
            try:
                value = probe.read()
                old_time, creation, old_cpu = self.previous[role]
                if value[0] != creation:
                    raise OSError('process_identity_changed')
                elapsed = now - old_time
                cpu = max(0, (value[1] - old_cpu) / elapsed * 100) if elapsed > 0 else None
                self._record(role, value, cpu)
                self.previous[role] = (now, creation, value[1])
            except OSError:
                # Exit/access failure ends this handle's sampling; no PID lookup/reuse.
                self._close_probe(role, probe)
                del self.probes[role]
                if not self.session['metrics']['processes'][role]['samples']:
                    self.session['metrics']['processes'][role]['availability'] = 'unavailable'

    def close(self):
        if self.closed:
            return
        self.sample(force=True)
        for role, probe in self.probes.items():
            self._close_probe(role, probe)
        self.probes.clear()
        self.closed = True


class OwnedJob:
    """Kill-on-close job for this launcher's own preparation commands and descendants."""
    def __init__(self):
        self.handle = None
        self.close_state = 'open'
        self.cleanup_confirmed = False
        self.processes_confirmed = False
        self._teardown_failed = False
        if sys.platform != 'win32':
            return
        self.api = ctypes.WinDLL('kernel32', use_last_error=True)
        class Limits(ctypes.Structure):
            _fields_ = [('process_time', ctypes.c_int64), ('job_time', ctypes.c_int64),
                        ('flags', wintypes.DWORD), ('min', ctypes.c_size_t), ('max', ctypes.c_size_t),
                        ('active', wintypes.DWORD), ('affinity', ctypes.c_size_t),
                        ('priority', wintypes.DWORD), ('scheduling', wintypes.DWORD)]
        class Io(ctypes.Structure):
            _fields_ = [(name, ctypes.c_uint64) for name in ('read', 'write', 'other', 'read_bytes', 'write_bytes', 'other_bytes')]
        class Extended(ctypes.Structure):
            _fields_ = [('basic', Limits), ('io', Io)] + [(name, ctypes.c_size_t) for name in ('process_memory', 'job_memory', 'peak_process', 'peak_job')]
        self.api.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        self.api.CreateJobObjectW.restype = wintypes.HANDLE
        self.api.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        self.api.SetInformationJobObject.restype = wintypes.BOOL
        self.api.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        self.api.AssignProcessToJobObject.restype = wintypes.BOOL
        declare_close_handle(self.api)
        self.api.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        self.api.TerminateJobObject.restype = wintypes.BOOL
        self.api.QueryInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                                      wintypes.DWORD, ctypes.c_void_p]
        self.api.QueryInformationJobObject.restype = wintypes.BOOL
        self.handle = self.api.CreateJobObjectW(None, None)
        value = Extended()
        value.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.handle or not self.api.SetInformationJobObject(self.handle, 9, ctypes.byref(value), ctypes.sizeof(value)):
            try:
                self.close()
            except OSError as error:
                error.resource = self  # Caller retains a failed constructor's owner too.
                raise
            raise OSError('owned_job_unavailable')

    def assign(self, process):
        if self.close_state != 'open':
            raise OSError('cleanup_unconfirmed')
        if self.handle and not self.api.AssignProcessToJobObject(self.handle, int(process._handle)):
            raise OSError('owned_job_unavailable')

    def _confirm_empty(self):
        class Accounting(ctypes.Structure):
            _fields_ = [(name, ctypes.c_int64) for name in ('user', 'kernel', 'period_user', 'period_kernel')] + [
                (name, wintypes.DWORD) for name in ('faults', 'total', 'active', 'terminated')]
        deadline = time.monotonic() + 2
        while True:
            value = Accounting()
            if not self.api.QueryInformationJobObject(self.handle, 1, ctypes.byref(value), ctypes.sizeof(value), None):
                raise OSError('cleanup_unconfirmed')
            if value.active == 0:
                self.processes_confirmed = True
                return
            if time.monotonic() >= deadline:
                raise OSError('cleanup_unconfirmed')
            time.sleep(.01)

    def close(self):
        if self._teardown_failed:
            raise OSError('cleanup_unconfirmed')
        if self.close_state == 'closed':
            return
        problem = False
        if self.handle is not None:
            try:
                # Do not infer descendant exit from closing the last job handle.
                if not self.api.TerminateJobObject(self.handle, 1):
                    raise OSError('cleanup_unconfirmed')
                self._confirm_empty()
            except OSError:
                problem = True
            try:
                close_handle_once(self, self.api)
            except OSError:
                problem = True
        else:
            self.close_state = 'closed'
            self.processes_confirmed = True
        self.cleanup_confirmed = not problem and self.processes_confirmed and self.close_state == 'closed'
        self._teardown_failed = not self.cleanup_confirmed
        if self._teardown_failed:
            raise OSError('cleanup_unconfirmed')
