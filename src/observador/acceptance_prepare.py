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
    root=Path(root).resolve()
    if not (root/'.git').exists() or (root/'.git').is_symlink():
        return {'commit': None, 'modified': None}
    try:
        top=subprocess.run(['git','rev-parse','--show-toplevel'],cwd=root,text=True,capture_output=True,timeout=5)
        if top.returncode or Path(top.stdout.strip()).resolve()!=root:
            return {'commit': None, 'modified': None}
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
        self.cleanup_confirmed = True
        self.cleanup_errors = 0
        self.last_error = 'none'

    def run(self, arguments, *, cwd, timeout=180):
        if not self.cleanup_confirmed:
            raise PreparationError('cleanup_unconfirmed')
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
            try:
                self.job = OwnedJob()
            except OSError as error:
                self.job = getattr(error, 'resource', None)
                if self.job is not None:
                    self._cleanup_problem()
                    raise PreparationError('cleanup_unconfirmed') from None
                raise PreparationError('owned_job_unavailable') from None
            try:
                self.current = subprocess.Popen(arguments, cwd=cwd, env=environment,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace',
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                self.job.assign(self.current)
            except OSError:
                if self.current is not None:
                    self._cleanup_problem()  # Assignment failed: descendant containment is unproved.
                self._cleanup(self.current, None)
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
        except subprocess.TimeoutExpired:
            raise PreparationError('command_timeout') from None
        finally:
            self._cleanup(process, reader)
        return process.returncode, ''.join(chunks)

    def _cleanup_problem(self):
        self.cleanup_confirmed = False
        self.cleanup_errors += 1
        self.last_error = 'cleanup_unconfirmed'

    def _cleanup(self, process, reader):
        with self.lock:
            self._terminate()
            if process is not None:
                try:
                    process.wait(timeout=3)
                except (OSError, subprocess.TimeoutExpired):
                    self._cleanup_problem()
            if reader is not None:
                reader.join(timeout=2)
                if reader.is_alive():
                    self._cleanup_problem()
            if process is not None and process.stdout is not None and (reader is None or not reader.is_alive()):
                try:
                    process.stdout.close()
                except OSError:
                    self._cleanup_problem()
            if self.cleanup_confirmed:
                self.current = self.job = None
            # On failure retain resource references; run() refuses another launch.
            if not self.cleanup_confirmed:
                raise PreparationError('cleanup_unconfirmed') from None

    def cancel(self):
        self.cancelled.set()
        self._terminate()

    def _terminate(self):
        with self.lock:
            if self.job:
                try:
                    self.job.close()
                except OSError:
                    self._cleanup_problem()
            if self.current and self.current.poll() is None:
                try:
                    self.current.kill()
                except OSError:
                    self._cleanup_problem()


def parse_tests(code, output):
    """Unittest process success describes EXECUTED tests; skips remain coverage gaps."""
    matches=list(re.finditer(r'^Ran (\d+) tests? in [^\r\n]+\r?$',output,re.MULTILINE))
    if not matches:
        return dict(status='FALHOU',discovered=None,skipped=None,failures=None,errors=None)
    digits=matches[-1].group(1)
    if len(digits)>19 or int(digits)>2**63-1:
        return dict(status='FALHOU',discovered=None,skipped=None,failures=None,errors=None)
    discovered=int(digits)
    tail=output[matches[-1].end():]
    summaries=list(re.finditer(r'^(OK(?: \([^\r\n]+\))?|FAILED \([^\r\n]+\))\s*$',tail,re.MULTILINE))
    if not summaries:
        return dict(status='FALHOU',discovered=discovered,skipped=None,failures=None,errors=None)
    summary=summaries[-1].group(1)
    fields={}
    if '(' in summary:
        for item in summary[summary.index('(')+1:summary.rindex(')')].split(', '):
            pair=re.fullmatch(r'(skipped|failures|errors)=(\d{1,19})',item)
            if not pair or pair.group(1) in fields:
                return dict(status='FALHOU',discovered=discovered,skipped=None,failures=None,errors=None)
            fields[pair.group(1)]=int(pair.group(2))
    skipped,failed,errors=(fields.get(k,0) for k in ('skipped','failures','errors'))
    if skipped>discovered or any(n>2**63-1 for n in (skipped,failed,errors)):
        return dict(status='FALHOU',discovered=discovered,skipped=None,failures=None,errors=None)
    proven=(code==0 and summary.startswith('OK') and 0<=skipped<discovered and not failed and not errors)
    return dict(status='PASSOU' if proven else 'FALHOU',discovered=discovered,
                skipped=skipped,failures=failed,errors=errors)


class Preparation:
    def __init__(self, root, report, *, runner=None, tk_version=None):
        self.root, self.report = Path(root).resolve(), report
        self.runner = runner or CommandRunner()
        self.ready = False
        self.tk_version = tk_version
        self.test_diagnostics=None

    def prepare(self, notify=lambda _: None):
        report = self.report
        self.ready = False
        self.test_diagnostics=None
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
            # Comparative automated checks also need the legacy synthetic fixture.
            # The manual lab still opens WPF; report v1 retains its two required hashes.
            for directory, name in (*PROJECTS.values(), ('SyntheticTaskApp', 'SyntheticTaskApp')):
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
        self.test_diagnostics=None
        notify('Testes automáticos: podem abrir apenas as fixtures e o observador fictício. Não são aceite humano.')
        environment_source = str(self.root / 'src')
        # -c sets only the source import directory, without pip or dependency installation.
        script = ("import sys;sys.path.insert(0,sys.argv[1]);"
                  "from observador.acceptance_test_runner import main;sys.exit(main())")
        code, output = self.runner.run([sys.executable, '-c', script, environment_source], cwd=self.root, timeout=300)
        self.report['automated_tests'] = parse_tests(code, output)
        from .acceptance_test_runner import read_summary
        self.test_diagnostics=read_summary(output,self.report['automated_tests'])
        return self.report['automated_tests']

    def verify_artifacts(self):
        try:
            return self.ready and artifact_hashes(self.root) == self.report['artifacts']
        except OSError:
            return False
