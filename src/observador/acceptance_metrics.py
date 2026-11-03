"""Sample only explicitly registered owned process handles, never enumerate processes."""
import ctypes
from ctypes import wintypes
import os
import sys
import time


class ProcessProbe:
    def __init__(self, pid):
        if sys.platform != 'win32':
            raise OSError('metrics_unavailable')
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        self.kernel.OpenProcess.restype = wintypes.HANDLE
        self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
        self.kernel.GetProcessTimes.restype = wintypes.BOOL
        self.kernel.K32GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
        self.kernel.K32GetProcessMemoryInfo.restype = wintypes.BOOL
        self.handle = self.kernel.OpenProcess(0x1000 | 0x10, False, pid)
        if not self.handle:
            raise OSError('metrics_unavailable')

    def read(self):
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
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None


class OwnedSampler:
    def __init__(self, session, *, probe_factory=ProcessProbe, clock=time.monotonic):
        self.session, self.factory, self.clock = session, probe_factory, clock
        self.probes = {}
        self.previous = {}
        self.closed = False
        self.last_sample = float('-inf')

    def register(self, role, process=None, *, current_controller=False):
        if self.closed:
            return
        if role not in self.session['metrics']['processes'] or role in self.probes:
            return
        if current_controller != (role == 'controller'):
            raise ValueError('owned_role_required')
        if not current_controller and (process is None or process.poll() is not None):
            return
        pid = os.getpid() if current_controller else process.pid
        try:
            probe = self.factory(pid)
            first = probe.read()
            self.probes[role] = probe
            self.previous[role] = (self.clock(), first[0], first[1])
            self._record(role, first, None)
        except OSError:
            if 'probe' in locals():
                probe.close()
            self.session['metrics']['processes'][role]['availability'] = 'unavailable'

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
                probe.close()
                del self.probes[role]
                if not self.session['metrics']['processes'][role]['samples']:
                    self.session['metrics']['processes'][role]['availability'] = 'unavailable'

    def close(self):
        if self.closed:
            return
        self.sample(force=True)
        for probe in self.probes.values():
            probe.close()
        self.probes.clear()
        self.closed = True


class OwnedJob:
    """Kill-on-close job for this launcher's own preparation commands and descendants."""
    def __init__(self):
        self.handle = None
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
        self.api.CloseHandle.argtypes = [wintypes.HANDLE]
        self.handle = self.api.CreateJobObjectW(None, None)
        value = Extended()
        value.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.handle or not self.api.SetInformationJobObject(self.handle, 9, ctypes.byref(value), ctypes.sizeof(value)):
            self.close()
            raise OSError('owned_job_unavailable')

    def assign(self, process):
        if self.handle and not self.api.AssignProcessToJobObject(self.handle, int(process._handle)):
            raise OSError('owned_job_unavailable')

    def close(self):
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle = None
