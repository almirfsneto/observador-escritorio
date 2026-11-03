"""Visible synthetic laboratory, owning exactly one fixture and one UIA provider."""
from datetime import datetime
import subprocess
import sys
import threading

from .lab_session import fixture_path, make_lab_policy
from .native_session import NativeSession, observer_path


class LaboratoryWindow:
    def __init__(self, tk):
        self.tk = tk
        self.root = tk.Tk()
        self.root.title('Observador | Laboratorio sintetico')
        self.root.geometry('760x460')
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.fixture = None
        self.session = None
        self.cleanup = None
        self.finished = False
        self.event_count = 0
        tk.Label(self.root, text='LABORATORIO FICTICIO - INICIALMENTE DESATIVADO',
                 font=('Segoe UI', 12, 'bold')).pack(pady=12)
        tk.Label(self.root, text='Somente a instancia ficticia aberta aqui. Sem texto, prints ou rede.\n'
                 'Eventos UIA na memoria, por ate 15 minutos. Fechar encerra os processos do ensaio.').pack()
        controls = tk.Frame(self.root)
        controls.pack(pady=12)
        self.launch_btn = tk.Button(controls, text='1. Abrir aplicativo ficticio', command=self.launch_fixture)
        self.launch_btn.grid(row=0, column=0, padx=5)
        self.start_btn = tk.Button(controls, text='2. Iniciar ensaio', command=self.start, state=tk.DISABLED)
        self.start_btn.grid(row=0, column=1, padx=5)
        self.pause_btn = tk.Button(controls, text='Pausar', command=self.toggle_pause, state=tk.DISABLED)
        self.pause_btn.grid(row=0, column=2, padx=5)
        self.stop_btn = tk.Button(controls, text='Encerrar', command=self.stop, state=tk.DISABLED)
        self.stop_btn.grid(row=0, column=3, padx=5)
        self.status_var = tk.StringVar(value='Estado: DESATIVADO')
        tk.Label(self.root, textvariable=self.status_var, wraplength=720).pack(pady=8)
        self.events_var = tk.StringVar(value='Eventos: 0 | perdas: 0')
        tk.Label(self.root, textvariable=self.events_var).pack()
        self.log = tk.Text(self.root, height=14, width=93, state=tk.DISABLED)
        self.log.pack(pady=10)
        self.root.after(100, self.tick)

    def append(self, text):
        self.log.config(state=self.tk.NORMAL)
        self.log.insert(self.tk.END, text + '\n')
        # The display, not just the transport queue, must have a memory bound.
        if int(self.log.index('end-1c').split('.')[0]) > 200:
            self.log.delete('1.0', '2.0')
        self.log.see(self.tk.END)
        self.log.config(state=self.tk.DISABLED)

    def launch_fixture(self):
        target = fixture_path()
        if not target.is_file() or target.is_symlink() or not observer_path().is_file():
            self.status_var.set('ERRO: compile SyntheticTaskApp e WindowsObserver em Release.')
            return
        try:
            self.fixture = subprocess.Popen([str(target)], cwd=str(target.parent))
        except OSError:
            self.status_var.set('ERRO: nao foi possivel abrir o aplicativo ficticio.')
            return
        self.launch_btn.config(state=self.tk.DISABLED)
        self.start_btn.config(state=self.tk.NORMAL)
        self.stop_btn.config(state=self.tk.NORMAL)
        self.status_var.set('Estado: PRONTO E PAUSADO | nenhum observador iniciado')

    def start(self):
        if self.finished or self.fixture is None or self.fixture.poll() is not None or self.session:
            return
        policy = make_lab_policy(str(fixture_path()), datetime.now().astimezone())
        try:
            self.session = NativeSession(self.fixture, fixture_path(), policy.expires_at)
            self.session.set_active(True)
        except (OSError, ValueError):
            self.status_var.set('ERRO: nao foi possivel vincular o observador ao aplicativo ficticio.')
            self.stop()
            return
        self.start_btn.config(state=self.tk.DISABLED)
        self.pause_btn.config(state=self.tk.NORMAL)
        self.append('Ensaio iniciado. Fim automatico: ' + policy.expires_at.isoformat(timespec='seconds'))

    def toggle_pause(self):
        if self.session and not self.finished:
            self.session.set_active(not self.session.stream.enabled)
            self.pause_btn.config(text='Pausar' if self.session.stream.enabled else 'Retomar')

    def stop(self):
        if self.finished:
            return
        self.finished = True
        if self.session:
            self.session.stream.stop()
        for button in (self.launch_btn, self.start_btn, self.pause_btn, self.stop_btn):
            button.config(state=self.tk.DISABLED)
        self.status_var.set('Estado: ENCERRADO | reinicie para outro ensaio')
        self.cleanup = threading.Thread(target=self._cleanup, daemon=True)
        self.cleanup.start()

    def _cleanup(self):
        try:
            if self.session:
                self.session.close()
        finally:
            if self.fixture and self.fixture.poll() is None:
                self.fixture.terminate()
                try:
                    self.fixture.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.fixture.kill()
                    self.fixture.wait(timeout=2)

    def tick(self):
        if self.fixture and self.fixture.poll() is not None and not self.finished:
            self.append('Aplicativo ficticio fechado; fim do ensaio.')
            self.stop()
        if self.session and not self.finished:
            stream = self.session.stream
            if not self.session.check():
                self.append('Fim do ensaio: ' + stream.health)
                self.stop()
            else:
                for event in stream.drain():
                    self.event_count += 1
                    self.append(f'{event.timestamp_utc} | {event.action} | {event.target}')
                self.status_var.set('Estado: ' + stream.health.upper() +
                                    ' | expira: ' + stream.expires_at.isoformat(timespec='seconds'))
                self.events_var.set(f'Eventos: {self.event_count} | perdas de fila: '
                                    f'{stream.dropped + stream.native_dropped} | lacunas: {stream.sequence_gaps}')
        self.root.after(100, self.tick)

    def close(self):
        self.stop()
        self.root.destroy()

    def run(self):
        try:
            self.root.mainloop()
        finally:
            self.stop()
            if self.cleanup:
                self.cleanup.join(timeout=6)


def main():
    if sys.platform != 'win32':
        raise SystemExit('Este laboratorio exige Windows com desktop interativo.')
    import tkinter as tk
    LaboratoryWindow(tk).run()


if __name__ == '__main__':
    main()
