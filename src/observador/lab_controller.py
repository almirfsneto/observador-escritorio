"""Visible, manual Windows-only laboratory UI. No install, network, screenshots or disk writes.

Run from an editable source checkout: python -m observador.lab_controller
The *only* observed application is the fixture launched by this window.
"""
from datetime import datetime, timezone
import queue
import subprocess
import sys
import threading

from .collector import Collector
from .lab_session import fixture_path, make_lab_policy
from .windows import WindowsBackend


class LaboratoryWindow:
    def __init__(self, tk):
        self.tk = tk
        self.root = tk.Tk()
        self.root.title("Observador | Laboratorio sintetico")
        self.root.geometry("640x410")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.messages = queue.Queue(maxsize=100)
        self.shutdown = threading.Event()
        self.fixture = None
        self.collector = None
        self.worker = None
        self.event_count = 0

        tk.Label(
            self.root,
            text="LABORATORIO FICTICIO - COLETA INICIALMENTE DESATIVADA",
            font=("Segoe UI", 12, "bold"),
            wraplength=590,
        ).pack(pady=(14, 8))
        tk.Label(
            self.root,
            text=("Somente SyntheticTaskApp.exe, durante no maximo 15 minutos. "
                  "Sem prints, texto digitado, disco, rede ou inicializacao automatica."),
            wraplength=580,
        ).pack(pady=(0, 14))
        controls = tk.Frame(self.root)
        controls.pack(pady=5)
        self.launch_btn = tk.Button(
            controls, text="1. Abrir aplicativo ficticio",
            command=self.launch_fixture, width=24
        )
        self.launch_btn.grid(row=0, column=0, padx=5)
        self.start_btn = tk.Button(
            controls, text="2. Iniciar ensaio", command=self.start, width=19,
            state=tk.DISABLED
        )
        self.start_btn.grid(row=0, column=1, padx=5)
        self.pause_btn = tk.Button(
            controls, text="Pausar", command=self.toggle_pause, width=12,
            state=tk.DISABLED
        )
        self.pause_btn.grid(row=0, column=2, padx=5)
        self.stop_btn = tk.Button(
            controls, text="Encerrar", command=self.stop, width=12,
            state=tk.DISABLED
        )
        self.stop_btn.grid(row=0, column=3, padx=5)

        self.status_var = tk.StringVar(value="Estado: DESATIVADO | nenhum aplicativo observado")
        tk.Label(self.root, textvariable=self.status_var, wraplength=600).pack(pady=14)
        self.events_var = tk.StringVar(value="Eventos sinteticos na memoria: 0")
        tk.Label(self.root, textvariable=self.events_var).pack()
        self.log = tk.Text(self.root, height=11, width=77, state=tk.DISABLED)
        self.log.pack(pady=12)
        self.root.after(250, self.drain_messages)

    def append(self, text):
        self.log.config(state=self.tk.NORMAL)
        self.log.insert(self.tk.END, text + "\n")
        self.log.see(self.tk.END)
        self.log.config(state=self.tk.DISABLED)

    def launch_fixture(self):
        target = fixture_path()
        if not target.is_file() or target.is_symlink():
            self.status_var.set(
                "ERRO: compile primeiro o executavel ficticio (.NET 8, Release)."
            )
            return
        try:
            self.fixture = subprocess.Popen([str(target)], cwd=str(target.parent))
        except OSError:
            self.status_var.set("ERRO: nao foi possivel abrir o aplicativo ficticio.")
            return
        self.launch_btn.config(state=self.tk.DISABLED)
        self.start_btn.config(state=self.tk.NORMAL)
        self.status_var.set("Estado: PRONTO E PAUSADO | aplicativo ficticio aberto")
        self.append("Aplicativo ficticio aberto; nenhuma captura iniciada.")

    def start(self):
        if self.fixture is None or self.fixture.poll() is not None or self.collector is not None:
            return
        target = fixture_path()
        now = datetime.now().astimezone()
        policy = make_lab_policy(str(target), now)
        self.collector = Collector(policy, WindowsBackend(), "laboratorio-sintetico")
        self.collector.pause()
        self.shutdown.clear()
        self.start_btn.config(state=self.tk.DISABLED)
        self.pause_btn.config(state=self.tk.NORMAL)
        self.stop_btn.config(state=self.tk.NORMAL)
        self.collector.resume()
        self.worker = threading.Thread(target=self.poll_loop, daemon=True)
        self.worker.start()
        self.status_var.set("Estado: ATIVO | somente o aplicativo ficticio")
        self.append("Ensaio iniciado explicitamente; expira em 15 minutos.")

    def toggle_pause(self):
        if self.collector is None or self.collector.stopped:
            return
        if self.collector.paused:
            self.collector.resume()
            self.pause_btn.config(text="Pausar")
            self.status_var.set("Estado: ATIVO | somente o aplicativo ficticio")
        else:
            self.collector.pause()
            self.pause_btn.config(text="Retomar")
            self.status_var.set("Estado: PAUSADO | nenhuma coleta")

    def stop(self):
        if self.collector is not None:
            self.collector.stop()
        self.shutdown.set()
        self.start_btn.config(state=self.tk.DISABLED)
        self.pause_btn.config(state=self.tk.DISABLED)
        self.stop_btn.config(state=self.tk.DISABLED)
        self.status_var.set("Estado: ENCERRADO | reinicie o programa para outro ensaio")
        self.append("Ensaio encerrado; nenhum evento foi gravado em disco.")

    def poll_loop(self):
        while not self.shutdown.is_set() and self.collector is not None:
            if self.fixture is None or self.fixture.poll() is not None:
                self.messages.put(("stop", "Aplicativo ficticio foi fechado."))
                return
            event = self.collector.poll()
            if event is not None:
                try:
                    self.messages.put_nowait(("event", (
                        event.timestamp_utc, event.app, event.target
                    )))
                except queue.Full:
                    pass  # No buffer expansion and no sensitive exception text.
            if self.collector.stopped:
                self.messages.put(("stop", "Expiracao do periodo de laboratorio."))
                return
            self.shutdown.wait(0.5)

    def drain_messages(self):
        if self.collector is not None and not self.collector.stopped:
            if datetime.now(timezone.utc) >= self.collector.policy.expires_at.astimezone(timezone.utc):
                self.stop()
        for _ in range(100):
            try:
                kind, value = self.messages.get_nowait()
            except queue.Empty:
                break
            if kind == "event" and self.collector is not None and not self.collector.stopped:
                self.event_count += 1
                self.events_var.set(
                    f"Eventos sinteticos na memoria: {self.event_count}"
                )
                stamp, alias, role = value
                self.append(f"{stamp} | {alias} | foco: {role}")
            elif kind == "stop" and self.collector is not None and not self.collector.stopped:
                self.append(value)
                self.stop()
        self.root.after(250, self.drain_messages)

    def close(self):
        if self.collector is not None:
            self.collector.stop()
        self.shutdown.set()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    if sys.platform != "win32":
        raise SystemExit("Este laboratorio exige Windows com desktop interativo.")
    try:
        import tkinter as tk
    except ImportError as exc:
        raise SystemExit("Instale Python Windows com Tkinter para executar o laboratorio.") from exc
    LaboratoryWindow(tk).run()


if __name__ == "__main__":
    main()
