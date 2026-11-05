"""AI03B: test-only Job-at-CreateProcess experiment. Never imported by runtime."""
import ctypes
from ctypes import wintypes as W
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from isolated_suspended_spawn import (Startup, ProcessInfo, SuspendedProbe,
                                      kernel_api, minimal_environment)
from isolated_cleanup_diagnostic import CleanupDiagnostic
from observador.acceptance_metrics import OwnedJob
from observador.cleanup import CleanupStatus

JOB_LIST = 0x0002000D  # ProcThreadAttributeValue(13, FALSE, TRUE, FALSE).
CREATION_FLAGS = 0x4 | 0x8000000 | 0x400 | 0x80000
PHASES = ('job_setup', 'attribute_size', 'attribute_init', 'attribute_update',
          'create', 'membership', 'resume', 'attribute_delete')
STATES = ('not_attempted', 'passed', 'failed')
ERRORS = {5: 'access_denied', 6: 'invalid_handle', 87: 'invalid_parameter',
          50: 'not_supported', 122: 'insufficient_buffer', 2: 'missing_image'}
# Exactly one inert descendant; only its retained handle slot is written privately.
SCRIPT = ('import subprocess,sys,time;'
          'p=subprocess.Popen([sys.executable,"-I","-S","-B","-c",'
          '"import time;time.sleep(40)"],close_fds=True);'
          'f=open(sys.argv[1],"xb");f.write(str(int(p._handle)).encode("ascii"));'
          'f.close();time.sleep(40)')


class StartupEx(ctypes.Structure):
    _fields_ = [('startup', Startup), ('attributes', ctypes.c_void_p)]


def extended_api():
    api = kernel_api()
    declarations = (
        ('InitializeProcThreadAttributeList', [ctypes.c_void_p, W.DWORD, W.DWORD,
                                               ctypes.POINTER(ctypes.c_size_t)], W.BOOL),
        ('UpdateProcThreadAttribute', [ctypes.c_void_p, W.DWORD, ctypes.c_size_t,
                                      ctypes.c_void_p, ctypes.c_size_t,
                                      ctypes.c_void_p, ctypes.c_void_p], W.BOOL),
        ('DeleteProcThreadAttributeList', [ctypes.c_void_p], None),
        ('GetHandleInformation', [W.HANDLE, ctypes.POINTER(W.DWORD)], W.BOOL),
    )
    for name, args, result in declarations:
        function = getattr(api, name)
        function.argtypes, function.restype = args, result
    api.CreateProcessW.argtypes = [W.LPCWSTR, W.LPWSTR, ctypes.c_void_p, ctypes.c_void_p,
                                   W.BOOL, W.DWORD, ctypes.c_void_p, W.LPCWSTR,
                                   ctypes.POINTER(StartupEx), ctypes.POINTER(ProcessInfo)]
    return api


class CreationProbe(SuspendedProbe):
    """Retain attribute storage and lpValue through Delete, even on failure."""
    def __init__(self, marker, *, api=None, job_factory=OwnedJob):
        try:
            self.api = api if api is not None else extended_api()
        except Exception:
            raise OSError('job_at_creation_unavailable') from None
        self.marker = Path(marker).absolute()
        self.status = CleanupStatus()
        self.process = SimpleNamespace(handle=None, close_state='open')
        self.thread = SimpleNamespace(handle=None, close_state='open')
        self.assigned = self.job_attached = self.resumed = False
        self.diagnostic = CleanupDiagnostic()
        self.diagnostic_origin = 'win32' if api is None else 'injected'
        self.phases = dict.fromkeys(PHASES, 'not_attempted')
        self.errors = dict.fromkeys(PHASES, 'none')
        self.first_failure = None
        self.attribute_buffer = self.job_values = None
        self.attribute_state = 'absent'
        self.created = self.job_noninheritable = False
        self.ambient_job = 'unknown'
        self.job = None
        try:
            try:
                self.job = job_factory()
            except Exception as error:
                self.job = getattr(error, 'resource', None)
                raise
            flags = W.DWORD()
            if (not self.api.GetHandleInformation(self.job.handle, ctypes.byref(flags))
                    or flags.value & 1):
                raise OSError('job_at_creation_unavailable')
            self.job_noninheritable = True
            if api is None:
                terminate = self.job.api.TerminateJobObject
                close = self.job.api.CloseHandle
                confirm = self.job._confirm_empty
                self.job.api.TerminateJobObject = lambda *a: self.diagnostic.boolean_call(
                    'job_terminate', lambda: terminate(*a))
                self.job.api.CloseHandle = lambda *a: self.diagnostic.boolean_call(
                    'job_handle_close', lambda: close(*a))
                def confirm_empty():
                    try:
                        confirm()
                    except Exception:
                        self.diagnostic.note('job_zero', 'failed')
                        raise
                    self.diagnostic.note('job_zero', 'passed')
                self.job._confirm_empty = confirm_empty
            ambient = W.BOOL()
            if not self.api.IsProcessInJob(self.api.GetCurrentProcess(), None, ctypes.byref(ambient)):
                raise OSError('job_at_creation_unavailable')
            self.ambient_job = 'present' if ambient.value else 'absent'
            self.note('job_setup', True)
        except Exception:
            self.note('job_setup', False)
            self.abort()

    def note(self, phase, success):
        if phase not in PHASES:
            raise ValueError('creation_diagnostic_rejected')
        self.phases[phase] = 'passed' if success else 'failed'
        if not success:
            if self.first_failure is None:
                self.first_failure = phase
            getter = getattr(ctypes, 'get_last_error', lambda: None)
            code = getter()
            self.errors[phase] = ERRORS.get(code, 'other' if code is not None else 'unavailable')

    def checked(self, phase, action):
        try:
            result = action()
        except Exception:
            self.note(phase, False)
            raise OSError('job_at_creation_unavailable') from None
        self.note(phase, bool(result))
        if not result:
            raise OSError('job_at_creation_unavailable')
        return result

    def abort(self):
        try:
            self.close()
        except Exception:
            pass  # State and error remain attached; no false cleanup confirmation.
        error = OSError('job_at_creation_unavailable')
        error.resource = self
        raise error from None

    def create(self, *, negative=None):
        if negative not in (None, 'invalid_job', 'invalid_attribute_size', 'missing_image'):
            raise ValueError('creation_negative_rejected')
        if self.status.finished or self.created or self.attribute_state != 'absent':
            raise OSError('job_at_creation_unavailable')
        try:
            size = ctypes.c_size_t()
            # The sizing call MUST fail with ERROR_INSUFFICIENT_BUFFER and size > 0.
            try:
                result = self.api.InitializeProcThreadAttributeList(None, 1, 0, ctypes.byref(size))
            except Exception:
                self.note('attribute_size', False)
                raise OSError('job_at_creation_unavailable') from None
            code = getattr(ctypes, 'get_last_error', lambda: None)()
            self.note('attribute_size', not result and code == 122 and 0 < size.value <= 65536)
            if self.phases['attribute_size'] != 'passed':
                raise OSError('job_at_creation_unavailable')
            self.attribute_buffer = ctypes.create_string_buffer(size.value)
            self.checked('attribute_init', lambda: self.api.InitializeProcThreadAttributeList(
                self.attribute_buffer, 1, 0, ctypes.byref(size)))
            self.attribute_state = 'initialized'
            self.job_values = (W.HANDLE * 1)(None if negative == 'invalid_job' else self.job.handle)
            self.checked('attribute_update', lambda: self.api.UpdateProcThreadAttribute(
                self.attribute_buffer, 0, JOB_LIST, self.job_values,
                0 if negative == 'invalid_attribute_size' else ctypes.sizeof(self.job_values), None, None))
            startup = StartupEx()
            startup.startup.cb = ctypes.sizeof(StartupEx)
            startup.startup.flags = 0x100  # STARTF_USESTDHANDLES, all three NULL.
            startup.attributes = ctypes.cast(self.attribute_buffer, ctypes.c_void_p)
            info = ProcessInfo()
            command = ctypes.create_unicode_buffer(subprocess.list2cmdline(
                [sys.executable, '-I', '-S', '-B', '-c', SCRIPT, str(self.marker)]))
            env = minimal_environment(self.marker.parent)
            block = ctypes.create_unicode_buffer('\0'.join(k + '=' + env[k] for k in sorted(env)) + '\0\0')
            executable = str(self.marker.parent / 'absent-synthetic.exe') if negative == 'missing_image' else sys.executable
            self.checked('create', lambda: self.api.CreateProcessW(
                executable, command, None, None, False, CREATION_FLAGS, block,
                str(Path(sys.executable).parent), ctypes.byref(startup), ctypes.byref(info)))
            # First statements after successful CreateProcess; no membership/resume/assign.
            self.process.handle, self.thread.handle = info.process, info.thread
            self.created = self.job_attached = True
        except Exception:
            self.abort()

    def verify(self):
        if not self.created or self.status.finished or self.resumed:
            raise OSError('job_at_creation_unavailable')
        member = W.BOOL()
        self.checked('membership', lambda: self.api.IsProcessInJob(
            self.process.handle, self.job.handle, ctypes.byref(member)))
        if not member.value:
            self.note('membership', False)
            raise OSError('job_at_creation_unavailable')
        self.assigned = True

    def resume(self):
        if not self.assigned or self.resumed or self.status.finished:
            raise OSError('creation_resume_refused')
        self.checked('resume', lambda: self.api.ResumeThread(self.thread.handle) == 1)
        self.resumed = True

    def delete_attributes(self):
        if self.attribute_state == 'failed':
            raise OSError('isolated_cleanup_unconfirmed')
        if self.attribute_state == 'initialized':
            self.attribute_state = 'failed'  # Never retry an uncertain delete.
            try:
                # Win32 VOID: normal return is the API contract, not a BOOL proof.
                self.api.DeleteProcThreadAttributeList(self.attribute_buffer)
            except Exception:
                self.note('attribute_delete', False)
                raise OSError('isolated_cleanup_unconfirmed') from None
            self.note('attribute_delete', True)
        self.attribute_state = 'deleted'
        self.attribute_buffer = self.job_values = None

    def close(self):
        if not self.status.finished:
            self.status.attempt('provider', self.delete_attributes)
        if self.job is None:
            self.job = SimpleNamespace(close=lambda: None, processes_confirmed=True,
                                       cleanup_confirmed=True, close_state='closed')
        super().close()

    def snapshot(self):
        return dict(kind='job_at_creation', origin=self.diagnostic_origin,
                    phases=dict(self.phases), native_errors=dict(self.errors),
                    first_failure=self.first_failure, created=self.created,
                    verified=self.assigned, resumed=self.resumed,
                    attribute_state=self.attribute_state,
                    attribute_storage_retained=self.attribute_buffer is not None,
                    value_storage_retained=self.job_values is not None,
                    job_noninheritable=self.job_noninheritable, ambient_job=self.ambient_job,
                    cleanup=self.diagnostic.snapshot(self))


def crash_launcher(stage, marker):
    if stage == 'nested_before_verify':
        print('prepare', flush=True)
        if sys.stdin.readline().strip() != 'create':
            raise OSError('creation_control_rejected')
        stage = 'before_verify'
    probe = CreationProbe(marker)
    try:
        probe.create()
        if stage != 'before_verify':
            probe.verify()
        if stage == 'after_resume':
            probe.resume()
        # PRIVATE control pipe only; never forwarded to CI or report.
        print(json.dumps(dict(slot=int(probe.process.handle), stage=stage,
                              verified=probe.assigned, resumed=probe.resumed,
                              job_noninheritable=probe.job_noninheritable, ambient_job=probe.ambient_job)), flush=True)
        if sys.stdin.readline().strip() != 'cleanup':
            raise OSError('creation_control_rejected')
    finally:
        probe.close()


if __name__ == '__main__':
    if len(sys.argv) != 3 or sys.argv[1] not in ('before_verify', 'after_verify', 'after_resume', 'nested_before_verify'):
        raise SystemExit('creation_arguments_rejected')
    try:
        crash_launcher(sys.argv[1], sys.argv[2])
    except Exception:
        raise SystemExit('creation_launcher_failed') from None
