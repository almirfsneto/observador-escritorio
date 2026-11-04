"""One owned native observer, asynchronous stdio, bounded shutdown; Windows lab only."""
import json
import queue
from pathlib import Path
import subprocess
import sys
import threading
import time

from .stream import LabStream
from .owned_identity import creation_ticks
from .cleanup import CleanupStatus


def observer_path():
    return (Path(__file__).resolve().parents[2] / 'tools' / 'WindowsObserver' / 'bin'
            / 'Release' / 'net8.0-windows' / 'WindowsObserver.exe')


class NativeSession:
    def __init__(self, fixture, target, expires_at, *, executable=None, protocol_test=False):
        self.fixture = fixture
        self.stream = LabStream(expires_at)
        self.expected_ticks = creation_ticks(fixture)
        self.process = subprocess.Popen(
            [str(executable or observer_path()), '--protocol-test' if protocol_test else '--laboratory',
             str(fixture.pid), str(target), str(self.expected_ticks), expires_at.isoformat()],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding='utf-8', bufsize=1,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
        self.cleanup_status = CleanupStatus()
        self.closed = False
        self.lock = threading.RLock()
        self.commands = queue.Queue(maxsize=1)
        self.writer = threading.Thread(target=self._write, daemon=True)
        self.reader = threading.Thread(target=self._read, daemon=True)
        try:
            self.writer.start()
            self.reader.start()
        except Exception:
            self.close()
            error=OSError('native_start_unconfirmed');error.resource=self
            raise error from None

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
            def stop_provider():
                if self.process.poll() is None:self.process.terminate()
            self.cleanup_status.attempt('provider',stop_provider)

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

    @property
    def cleanup_confirmed(self):return self.cleanup_status.confirmed

    def close(self):
        status=self.cleanup_status
        with self.lock:
            if self.closed:return
            self.closed=True
            status.attempt('stream',self.stream.stop)
            status.attempt('stop_command',lambda:self._enqueue({'command':'stop'}))
        try:self.process.wait(timeout=1)
        except subprocess.TimeoutExpired:status.stop_process('provider',self.process,force=True)
        except Exception:
            status.fail('provider');status.stop_process('provider',self.process,force=True)
        status.check('provider',lambda:self.process.poll() is not None)
        for resource,thread,pipe in (('reader',self.reader,self.process.stdout),('writer',self.writer,self.process.stdin)):
            status.attempt(resource,lambda t=thread:t.join(timeout=1))
            # Closing a TextIOWrapper while another thread reads/writes can block.
            if status.check(resource,lambda t=thread:not t.is_alive()):
                status.attempt('stdout' if resource=='reader' else 'stdin',pipe.close)
        status.finish()
