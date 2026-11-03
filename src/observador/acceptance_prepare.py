"""Local dependency/build/test orchestration. No install, elevation, network restore or raw logs."""
from collections import deque
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading

from .acceptance_metrics import OwnedJob

PROJECTS = {'fixture': ('SyntheticWpfTaskApp', 'SyntheticWpfTaskApp'),
            'provider': ('WindowsObserver', 'WindowsObserver')}
SUFFIXES = {'exe_sha256': '.exe', 'assembly_sha256': '.dll',
            'deps_sha256': '.deps.json', 'runtimeconfig_sha256': '.runtimeconfig.json'}


def binaries(root):
    return {role: Path(root) / 'tools' / directory / 'bin/Release/net8.0-windows' / (name + '.exe')
            for role, (directory, name) in PROJECTS.items()}


def artifact_hashes(root):
    result = {}
    for role, binary in binaries(root).items():
        result[role] = {}
        for key, suffix in SUFFIXES.items():
            path = binary.with_name(binary.stem + suffix)
            if path.is_symlink() or not path.is_file():
                raise OSError('artifacts_unavailable')
            digest = hashlib.sha256()
            with path.open('rb') as source:
                for block in iter(lambda: source.read(65536), b''):
                    digest.update(block)
            result[role][key] = digest.hexdigest()
    return result


def source_state(root):
    # Git is optional; absent metadata is a gap, never invented provenance.
    try:
        commit = subprocess.run(['git', 'rev-parse', '--verify', 'HEAD'], cwd=root,
                                text=True, capture_output=True, timeout=5)
        dirty = subprocess.run(['git', 'status', '--porcelain'], cwd=root,
                               text=True, capture_output=True, timeout=5)
        sha = commit.stdout.strip()
        return {'commit': sha if commit.returncode == 0 and re.fullmatch('[a-f0-9]{40}', sha) else None,
                'modified': bool(dirty.stdout) if dirty.returncode == 0 else None}
    except (OSError, subprocess.TimeoutExpired):
        return {'commit': None, 'modified': None}


def windows_profile():
    result = {'os_family': 'unsupported', 'os_edition': 'unknown', 'os_build': None,
              'python': '.'.join(map(str, sys.version_info[:3])), 'tk': None, 'dotnet_sdk': None}
    if sys.platform != 'win32':
        return result
    version = sys.getwindowsversion()
    result['os_build'] = version.build
    result['os_family'] = ('windows_server' if version.product_type != 1 else
                           'windows11' if version.build >= 22000 else
                           'windows10' if version.major == 10 else 'unsupported')
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows NT\CurrentVersion') as key:
            edition = winreg.QueryValueEx(key, 'EditionID')[0]
        result['os_edition'] = {'Core': 'Home', 'CoreSingleLanguage': 'HomeSingleLanguage',
                               'Professional': 'Pro', 'Enterprise': 'Enterprise', 'Education': 'Education',
                               'EnterpriseS': 'EnterpriseLTSC', 'ServerStandard': 'Server',
                               'ServerDatacenter': 'Server'}.get(edition, 'unknown')
    except OSError:
        pass
    return result


class PreparationError(RuntimeError):
    pass


class CommandRunner:
    def __init__(self):
        self.cancelled = threading.Event()
        self.lock = threading.RLock()
        self.current = None
        self.job = None

    def run(self, arguments, *, cwd, timeout=180):
        if self.cancelled.is_set():
            raise PreparationError('preparation_cancelled')
        environment = dict(os.environ)
        environment.update(DOTNET_CLI_TELEMETRY_OPTOUT='1', DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1',
                           DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE='1', DOTNET_NOLOGO='1',
                           MSBUILDDISABLENODEREUSE='1', DOTNET_CLI_UI_LANGUAGE='en',
                           DOTNET_GENERATE_ASPNET_CERTIFICATE='false', NUGET_CERT_REVOCATION_MODE='offline',
                           PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1', NUGET_XMLDOC_MODE='skip')
        chunks = deque(maxlen=32)  # At most 128 KiB; never write command output to disk/report.
        with self.lock:
            if self.cancelled.is_set():
                raise PreparationError('preparation_cancelled')
            self.job = OwnedJob()
            try:
                self.current = subprocess.Popen(arguments, cwd=cwd, env=environment,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace',
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                self.job.assign(self.current)
            except OSError:
                if self.current and self.current.poll() is None:
                    self.current.kill()
                    self.current.wait(timeout=3)
                self.job.close()
                raise PreparationError('command_unavailable') from None
            process = self.current
        def read():
            try:
                while True:
                    block = process.stdout.read(4096)
                    if not block:
                        break
                    chunks.append(block)
            except (OSError, ValueError):
                pass
        reader = threading.Thread(target=read, daemon=True)
        reader.start()
        try:
            process.wait(timeout=timeout)
            return process.returncode, ''.join(chunks) if not reader.is_alive() else self._finish_output(reader, chunks)
        except subprocess.TimeoutExpired:
            self._terminate()
            raise PreparationError('command_timeout') from None
        finally:
            with self.lock:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=3)
                self.job.close()
                reader.join(timeout=2)
                process.stdout.close()
                self.current = self.job = None

    @staticmethod
    def _finish_output(reader, chunks):
        reader.join(timeout=2)
        return ''.join(chunks)

    def cancel(self):
        self.cancelled.set()
        self._terminate()

    def _terminate(self):
        with self.lock:
            if self.job:
                self.job.close()  # Only this command's owned job and descendants.
            if self.current and self.current.poll() is None:
                self.current.kill()


def parse_tests(code, output):
    matches = re.findall(r'Ran (\d+) tests? in ', output)
    failed = re.findall(r'failures=(\d+)', output)
    errors = re.findall(r'errors=(\d+)', output)
    skipped = re.findall(r'skipped=(\d+)', output)
    proven = (code == 0 and matches and int(matches[-1]) > 0
              and not any(int(count) for count in failed + errors))
    return {'status': 'PASSOU' if proven else 'FALHOU',
            'discovered': int(matches[-1]) if matches else None,
            'skipped': int(skipped[-1]) if skipped else 0,
            'failures': int(failed[-1]) if failed else 0,
            'errors': int(errors[-1]) if errors else 0}


class Preparation:
    def __init__(self, root, report, *, runner=None, tk_version=None):
        self.root, self.report = Path(root).resolve(), report
        self.runner = runner or CommandRunner()
        self.ready = False
        self.tk_version = tk_version

    def prepare(self, notify=lambda _: None):
        report = self.report
        self.ready = False
        report['checks'] = dict.fromkeys(report['checks'], 'NAO_EXECUTADO')
        report['artifacts'] = {role: dict.fromkeys(SUFFIXES) for role in PROJECTS}
        report['automated_tests'] = {'status': 'NAO_EXECUTADO', 'discovered': None, 'skipped': None, 'failures': None, 'errors': None}
        report['environment'] = windows_profile()
        report['source'] = source_state(self.root)
        report['checks']['python'] = 'PASSOU' if sys.version_info >= (3, 11) else 'FALHOU'
        notify('Verificando Python e Tk…')
        try:
            import tkinter
            version = self.tk_version or str(tkinter.TkVersion)
            report['environment']['tk'] = version if re.fullmatch(r'\d+\.\d+(?:\.\d+)?', version) else None
            report['checks']['tk'] = 'PASSOU' if report['environment']['tk'] else 'FALHOU'
        except Exception:
            report['checks']['tk'] = 'FALHOU'
        dotnet = shutil.which('dotnet')
        if not dotnet:
            report['checks']['dotnet_sdk'] = 'FALHOU'
            raise PreparationError('dotnet8_required')
        code, output = self.runner.run([dotnet, '--list-sdks'], cwd=self.root, timeout=20)
        versions = re.findall(r'^(8\.\d+\.\d+)\s+\[', output, re.MULTILINE)
        if code or not versions:
            report['checks']['dotnet_sdk'] = 'FALHOU'
            raise PreparationError('dotnet8_required')
        selected = max(versions, key=lambda value: tuple(map(int, value.split('.'))))
        report['environment']['dotnet_sdk'] = selected
        report['checks']['dotnet_sdk'] = 'PASSOU'
        if any(report['checks'][key] != 'PASSOU' for key in ('python', 'tk', 'dotnet_sdk')):
            raise PreparationError('python_tk_required')
        notify('Compilando localmente, sem instalar ou restaurar pela rede…')
        with tempfile.TemporaryDirectory(prefix='observador-build-') as temporary:
            folder = Path(temporary)
            (folder / 'global.json').write_text('{"sdk":{"version":"' + selected + '","rollForward":"disable"}}')
            config = folder / 'NuGet.Config'
            config.write_text('<configuration><packageSources><clear /></packageSources></configuration>')
            report['checks']['offline_build'] = 'FALHOU'
            for directory, name in PROJECTS.values():
                project = str(self.root / 'tools' / directory / (name + '.csproj'))
                commands = [
                    [dotnet, 'restore', project, '--configfile', str(config), '-p:NuGetAudit=false', '--disable-parallel'],
                    [dotnet, 'build', project, '-c', 'Release', '--no-restore', '--disable-build-servers',
                     '-p:UseSharedCompilation=false', '--nologo'],
                ]
                for command in commands:
                    code, _ = self.runner.run(command, cwd=folder)
                    if code:
                        raise PreparationError('offline_build_failed')
            report['checks']['offline_build'] = 'PASSOU'
        notify('Conferindo os hashes dos executáveis e assemblies…')
        report['checks']['artifact_hashes'] = 'FALHOU'
        try:
            report['artifacts'] = artifact_hashes(self.root)
        except OSError:
            raise PreparationError('artifacts_unavailable') from None
        report['checks']['artifact_hashes'] = 'PASSOU'
        self.ready = True
        return report

    def run_tests(self, notify=lambda _: None):
        if not self.ready:
            raise PreparationError('preparation_required')
        self.report['automated_tests'] = {'status': 'FALHOU', 'discovered': None,
                                        'skipped': None, 'failures': None, 'errors': None}
        notify('Testes automáticos: podem abrir apenas as fixtures e o observador fictício. Não são aceite humano.')
        environment_source = str(self.root / 'src')
        # -c sets only the source import directory, without pip or dependency installation.
        script = ("import sys,unittest;sys.path.insert(0,sys.argv[1]);"
                  "suite=unittest.defaultTestLoader.discover('tests');"
                  "result=unittest.TextTestRunner(verbosity=2).run(suite);sys.exit(not result.wasSuccessful())")
        code, output = self.runner.run([sys.executable, '-c', script, environment_source], cwd=self.root, timeout=300)
        self.report['automated_tests'] = parse_tests(code, output)
        return self.report['automated_tests']

    def verify_artifacts(self):
        try:
            return self.ready and artifact_hashes(self.root) == self.report['artifacts']
        except OSError:
            return False
