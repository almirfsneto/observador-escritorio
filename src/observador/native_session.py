"""One owned native observer, asynchronous stdio, bounded shutdown; Windows lab only."""
import ctypes
from ctypes import wintypes
import json
import queue
from pathlib import Path
import subprocess
import sys
import threading
import time

from .stream import LabStream


def observer_path():
    return (Path(__file__).resolve().parents[2] / 'tools' / 'WindowsObserver' / 'bin'
            / 'Release' / 'net8.0-windows' / 'WindowsObserver.exe')


def creation_ticks(pid):
    if sys.platform != 'win32':
        raise OSError('Windows required')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    kernel.GetProcessTimes.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        raise OSError('Cannot bind laboratory process')
    try:
        created, exited, kernel_time, user_time = (wintypes.FILETIME() for _ in range(4))
        if not kernel.GetProcessTimes(handle, ctypes.byref(created), ctypes.byref(exited),
                                      ctypes.byref(kernel_time), ctypes.byref(user_time)):
            raise OSError('Cannot bind laboratory process')
        # FILETIME: 1601 epoch, DateTime ticks: year 1 epoch; both in 100 ns.
        return (created.dwHighDateTime << 32 | created.dwLowDateTime) + 504911232000000000
    finally:
        kernel.CloseHandle(handle)


class NativeSession:
    def __init__(self, fixture, target, expires_at, *, executable=None, protocol_test=False):
        self.fixture = fixture
        self.stream = LabStream(expires_at)
        self.expected_ticks = creation_ticks(fixture.pid)
        self.process = subprocess.Popen(
            [str(executable or observer_path()), '--protocol-test' if protocol_test else '--laboratory',
             str(fixture.pid), str(target), str(self.expected_ticks), expires_at.isoformat()],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding='utf-8', bufsize=1,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
        self.closed = False
        self.lock = threading.RLock()
        self.commands = queue.Queue(maxsize=1)
        self.writer = threading.Thread(target=self._write, daemon=True)
        self.writer.start()
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def _write(self):
        try:
            while True:
                command = self.commands.get()
                self.process.stdin.write(json.dumps(command) + '\n')
                self.process.stdin.flush()
                if command['command'] == 'stop':
                    self.process.stdin.close()
                    return
        except (OSError, ValueError):
            self.stream.stop('backend_exit')

    def _enqueue(self, command):
        try:
            self.commands.get_nowait()
        except queue.Empty:
            pass
        self.commands.put_nowait(command)

    def _read(self):
        try:
            while True:
                line = self.process.stdout.readline(4097)
                if not line:
                    break
                if len(line) > 4096 or not line.endswith('\n'):
                    self.stream.stop('protocol_error')
                    break
                data = json.loads(line)
                if isinstance(data, dict) and data.get('kind') == 'ready':
                    if (data.get('pid') != self.fixture.pid or data.get('start_ticks') != self.expected_ticks
                            or self.fixture.poll() is not None):
                        self.stream.stop('identity_error')
                        break
                self.stream.receive(line)
                if self.stream.stopped:
                    break
        except (OSError, ValueError, TypeError, UnicodeError):
            self.stream.stop('protocol_error')
        finally:
            if not self.stream.stopped:
                self.stream.stop('backend_exit')
            # EOF/error cannot leave a provider collecting until expiry.
            if self.process.poll() is None:
                try:
                    self.process.terminate()
                except OSError:
                    pass

    def set_active(self, active):
        with self.lock:
            if self.closed:
                return
            command = self.stream.command(active)
            if command is None:
                return
            self._enqueue(command)

    def check(self):
        if self.fixture.poll() is not None:
            self.stream.stop('fixture_exit')
        return self.stream.check_health()

    def close(self):
        with self.lock:
            if self.closed:
                return
            self.closed = True
            self.stream.stop()
            self._enqueue({'command': 'stop'})
        try:
            self.process.wait(timeout=1)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            if self.process.poll() is None:
                self.process.kill()
            self.process.wait(timeout=2)
        self.reader.join(timeout=1)
        self.writer.join(timeout=1)
        if not self.process.stdin.closed:
            try:
                self.process.stdin.close()
            except OSError:
                pass  # Windows can report EINVAL while flushing a pipe whose child exited.
        try:
            self.process.stdout.close()
        except OSError:
            pass
