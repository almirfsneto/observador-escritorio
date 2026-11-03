"""Portuguese operator wizard. Preparation, automated checks and human observations stay separate."""
from copy import deepcopy
from datetime import datetime, timezone
import os
from pathlib import Path
import queue
import sys
import tempfile
import threading
from uuid import uuid4

from .acceptance_prepare import Preparation, PreparationError
from .acceptance_report import (MANUAL_STEPS, OBSERVATIONS, STATUSES, ReportError,
                                new_report, safe_output_directory, write_report)
from .acceptance_session import AcceptanceLaboratory

ERRORS = {
    'dotnet8_required': 'SDK .NET 8 não encontrado. Peça ao TI para instalar previamente; nada será instalado aqui.',
    'python_tk_required': 'É necessário Python 3.11 ou superior com Tk. Peça ao TI para corrigir a dependência.',
    'offline_build_failed': 'Compilação local falhou. SDK/packs precisam estar disponíveis offline. Nada foi baixado.',
    'artifacts_unavailable': 'Arquivos compilados incompletos. Prepare novamente ou solicite revisão técnica.',
    'owned_job_unavailable': 'O Windows não permitiu controlar os processos próprios. Nenhum teste será iniciado.',
    'command_unavailable': 'Não foi possível executar a ferramenta local necessária.',
    'command_timeout': 'A ferramenta excedeu o prazo e seus processos próprios foram encerrados.',
    'preparation_cancelled': 'Preparação cancelada; processos próprios encerrados.',
    'preparation_required': 'Conclua a preparação antes dos testes.',
}
OBS_LABELS = {
    'NAO_AVALIADO': 'Não avaliado', 'SEM_ANOMALIA': 'Sem anomalia percebida',
    'LENTIDAO_PERCEBIDA': 'Lentidão percebida', 'TRAVAMENTO': 'Travamento',
    'CONTADOR_INESPERADO': 'Contador inesperado', 'SENHA_NAO_EXCLUIDA': 'Senha não excluída',
    'RETOMADA_FALHOU': 'Retomada falhou', 'PROCESSO_PERMANECEU': 'Processo permaneceu aberto',
    'DEPENDENCIA_AUSENTE': 'Dependência ausente', 'OUTRO_REQUER_REVISAO': 'Outro problema: requer revisão',
}
STATUS_LABELS = {'PASSOU': 'PASSOU', 'FALHOU': 'FALHOU', 'NAO_EXECUTADO': 'NÃO EXECUTADO'}


def default_destination(repository):
    base = os.environ.get('LOCALAPPDATA') if sys.platform == 'win32' else None
    directory = Path(base or tempfile.gettempdir()) / 'ObservadorEscritorio' / 'aceites' / uuid4().hex
    return safe_output_directory(repository, directory)


class AcceptanceWizard:
    def __init__(self, tk, repository, *, destination=None, origin=None):
        from tkinter import ttk
        self.tk, self.ttk = tk, ttk
        self.root = tk.Tk()
        self.root.title('Observador | Validação guiada — somente dados fictícios')
        self.root.geometry('1040x740')
        self.root.minsize(900, 650)
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.root.report_callback_exception = lambda *_: self.status.set('Erro do assistente; encerre e registre NÃO EXECUTADO. Nenhum detalhe bruto foi salvo.')
        self.repository = Path(repository).resolve()
        self.destination = safe_output_directory(self.repository, destination) if destination else default_destination(self.repository)
        self.report = new_report(origin or ('automated_test' if os.environ.get('GITHUB_ACTIONS') == 'true' else 'operator_guided'))
        self.preparation = Preparation(self.repository, self.report,
                                       tk_version=str(self.root.tk.call('package', 'provide', 'Tk')))
        self.messages = queue.Queue(maxsize=20)
        self.worker = None
        self.labs = []
        self.export_count = 0
        self.closing = False
        self.status = tk.StringVar(master=self.root, value='DESATIVADO. Nenhum observador ou aplicativo iniciado.')
        tk.Label(self.root, text='APENAS VM/COMPUTADOR DE TESTE DEDICADO — SEM DADOS REAIS',
                 font=('Segoe UI', 12, 'bold')).pack(pady=10)
        tk.Label(self.root, text='Não instala dependências, não pede administrador e não envia relatórios. '
                 'CI e testes automáticos não substituem o aceite humano.', wraplength=980).pack()
        self.tabs = ttk.Notebook(self.root)
        self.tabs.pack(fill='both', expand=True, padx=12, pady=12)
        self.pages = [ttk.Frame(self.tabs, padding=15) for _ in range(4)]
        for page, title in zip(self.pages, ('1. Preparação', '2. Ensaio', '3. Avaliação humana', '4. Relatório')):
            self.tabs.add(page, text=title)
        self._preparation_page()
        self._session_page()
        self._manual_page()
        self._report_page()
        tk.Label(self.root, textvariable=self.status, wraplength=1000).pack(padx=10, pady=10)
        self.root.after(100, self.poll)

    def _text(self, parent, text):
        self.ttk.Label(parent, text=text, wraplength=940, justify='left').pack(anchor='w', pady=8)

    def _preparation_page(self):
        page = self.pages[0]
        self._text(page, 'Dependências previamente instaladas: Python 3.11+ com Tk e SDK .NET 8. '
                   '1) Verifique/compile. 2) Acione os testes automáticos. As ferramentas ficam locais; '
                   'restauração pela rede e telemetria do SDK são desativadas.')
        self.prepare_btn = self.ttk.Button(page, text='1. Verificar e compilar (não inicia coleta)',
                                           command=lambda: self.task('prepare'))
        self.prepare_btn.pack(anchor='w', pady=10)
        self.tests_btn = self.ttk.Button(page, text='2. Executar testes automáticos fictícios',
                                         command=lambda: self.task('tests'), state='disabled')
        self.tests_btn.pack(anchor='w', pady=10)
        self._text(page, 'Os testes automáticos podem abrir fixtures e observadores por conta própria: '
                   'só começam ao clicar no botão 2. Eles não marcam os itens humanos como PASSOU.')
        self.prep_status = self.tk.StringVar(master=self.root, value='Preparação: NÃO EXECUTADO')
        self.ttk.Label(page, textvariable=self.prep_status, wraplength=940).pack(anchor='w', pady=15)

    def _session_page(self):
        page = self.pages[1]
        self._text(page, 'Após preparação e testes aprovados, abra o laboratório. Ele continua DESATIVADO '
                   'até você abrir a fixture e clicar em Iniciar ensaio. Use somente os campos fictícios '
                   'já preenchidos; nunca copie dados do escritório.')
        self.lab_btn = self.ttk.Button(page, text='3. Abrir laboratório visível (inicialmente desativado)',
                                      command=self.open_lab, state='disabled')
        self.lab_btn.pack(anchor='w', pady=12)
        self._text(page, 'No laboratório: alterne Salvar/Revisar, selecione o campo normal e o de senha fictícia. '
                   'Abra a segunda instância pelo botão próprio e confirme que só a primeira aumenta o contador. '
                   'Pause, interaja, retome e encerre. A confirmação PAUSADO exige ACK; pendências anteriores são descartadas.')
        self._text(page, 'Para testar fechamento de fixture, fechamento do controlador ou expiração de 15 minutos, '
                   'use um novo ensaio após encerrar o anterior (até seis). Feche a janela do laboratório para voltar. '
                   'CPU/RAM são amostradas apenas nos processos próprios; outras aplicações não são enumeradas.')
        self.lab_status = self.tk.StringVar(master=self.root, value='Nenhum ensaio iniciado. Nenhuma medida coletada.')
        self.ttk.Label(page, textvariable=self.lab_status, wraplength=940).pack(anchor='w', pady=12)

    def _manual_page(self):
        page = self.pages[2]
        self._text(page, 'Preencha somente o que você realmente verificou. NÃO EXECUTADO é um resultado válido. '
                   'Não há campo livre: observações padronizadas evitam nomes, senhas, caminhos ou texto de telas.')
        self.manual_variables = {}
        grid = self.ttk.Frame(page)
        grid.pack(fill='x')
        for row, (key, title) in enumerate(MANUAL_STEPS.items()):
            status = self.tk.StringVar(master=self.root, value='NÃO EXECUTADO')
            note = self.tk.StringVar(master=self.root, value=OBS_LABELS['NAO_AVALIADO'])
            self.manual_variables[key] = (status, note)
            self.ttk.Label(grid, text=title, wraplength=420).grid(row=row, column=0, sticky='w', pady=8)
            self.ttk.Combobox(grid, state='readonly', width=17, values=list(STATUS_LABELS.values()),
                              textvariable=status).grid(row=row, column=1, padx=8)
            self.ttk.Combobox(grid, state='readonly', width=28, values=list(OBS_LABELS.values()),
                              textvariable=note).grid(row=row, column=2, padx=8)
        self._text(page, 'Marcar PASSOU é uma declaração do operador, não aprovação jurídica ou liberação de piloto. '
                   'Cada versão do Windows exige seu próprio ensaio; preencha novamente em Windows 10 e Windows 11.')

    def _report_page(self):
        page = self.pages[3]
        self._text(page, 'O JSON contém somente versões/edição/build do Windows, commit, hashes, resultados '
                   'padronizados e medidas agregadas. Não inclui usuário, hostname, IP, títulos, caminhos, '
                   'campos, senhas ou screenshots. Nenhum evento individual entra neste relatório.')
        self._text(page, 'Medidas instrumentadas: CPU por deltas de tempo (percentual de um núcleo, amostrado), '
                   'RAM observada e pico de RAM do processo, início→ACK ativo e pausa→ACK percebido pelo controlador. '
                   'Amostras a cada 500 ms podem perder picos; o pico do OS cobre toda a vida do processo. '
                   'Responsividade e latência percebida continuam sendo observações humanas.')
        self.export_btn = self.ttk.Button(page, text='Salvar relatório sanitizado local', command=self.export)
        self.export_btn.pack(anchor='w', pady=15)
        self.output_status = self.tk.StringVar(master=self.root, value='Nenhum relatório salvo.')
        self.ttk.Label(page, textvariable=self.output_status, wraplength=940).pack(anchor='w', pady=10)
        self._text(page, 'Local padrão: %LOCALAPPDATA%\\ObservadorEscritorio\\aceites. '
                   'O caminho completo aparece apenas nesta tela após salvar, nunca dentro do JSON. '
                   'Compartilhe o JSON somente após revisão e por iniciativa própria; o assistente não faz upload.')
        self._text(page, 'Lacunas permanecem explícitas: aceite humano, Windows 10/11, métricas indisponíveis, '
                   'commit ausente, ausência de testes e falta de verificação instrumentada de rede. '
                   'Nenhum resultado libera piloto, instalação na equipe, deploy ou merge.')

    def active_lab(self):
        return any(not lab.finished or (lab.cleanup and lab.cleanup.is_alive()) for lab in self.labs)

    def task(self, kind):
        if (self.worker and self.worker.is_alive()) or self.active_lab():
            return
        if kind == 'prepare' and self.labs:
            self.status.set('Há ensaios registrados. Abra um novo assistente para recompilar sem misturar versões.')
            return
        self.prepare_btn.config(state='disabled')
        self.tests_btn.config(state='disabled')
        self.lab_btn.config(state='disabled')
        self.export_btn.config(state='disabled')
        def notify(message):
            try:
                self.messages.put_nowait(('progress', message))
            except queue.Full:
                pass
        def run():
            try:
                if kind == 'prepare':
                    self.preparation.prepare(notify)
                else:
                    self.preparation.run_tests(notify)
                self.messages.put(('done', kind))
            except Exception as error:
                code = str(error) if isinstance(error, PreparationError) else 'preparation_failed'
                self.messages.put(('error', code if code in ERRORS else 'preparation_failed'))
        self.worker = threading.Thread(target=run, daemon=True)
        self.worker.start()

    def open_lab(self):
        if self.active_lab() or len(self.labs) >= 6 or not self.preparation.verify_artifacts():
            self.status.set('Encerre o ensaio anterior e confirme a preparação/hashes; limite de seis ensaios.')
            return
        if self.report['automated_tests']['status'] != 'PASSOU':
            self.status.set('Execute e aprove os testes automáticos antes do ensaio manual.')
            return
        if self.report['environment']['os_family'] not in ('windows10', 'windows11') and self.report['origin'] != 'automated_test':
            self.status.set('Aceite exige Windows 10 ou 11 de teste. O relatório pode registrar esta lacuna.')
            return
        top = self.tk.Toplevel(self.root)
        lab = AcceptanceLaboratory(self.tk, root=top, preparation=self.preparation,
                                   data_target=self.destination / ('ensaio-' + str(len(self.labs) + 1)) / 'events.sqlite3')
        self.labs.append(lab)
        self.status.set('Laboratório aberto, DESATIVADO. O operador precisa iniciar o ensaio naquela janela.')

    def snapshot(self):
        report = deepcopy(self.report)
        reverse_status = {value: key for key, value in STATUS_LABELS.items()}
        reverse_notes = {value: key for key, value in OBS_LABELS.items()}
        for key, (status, note) in self.manual_variables.items():
            code = reverse_status.get(status.get())
            report['manual_checks'][key] = {'status': code,
                'observation': 'NAO_AVALIADO' if code == 'NAO_EXECUTADO' else reverse_notes.get(note.get())}
        report['sessions'] = [deepcopy(lab.recorder.data) for lab in self.labs]
        report['report_id'] = uuid4().hex
        report['created_utc'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        return report

    def export(self):
        if self.active_lab() or (self.worker and self.worker.is_alive()):
            self.status.set('Encerre o laboratório e aguarde a preparação/limpeza antes de salvar.')
            return
        if self.export_count >= 20:
            self.status.set('Limite de 20 exportações. Abra um novo assistente se precisar de outro registro.')
            return
        try:
            path = write_report(self.snapshot(), self.repository, self.destination)
        except (ReportError, ValueError, OSError):
            self.status.set('Relatório não salvo: confira os resultados padronizados e uma pasta local fora de Git.')
            return
        self.export_count += 1
        self.output_status.set('Salvo apenas neste computador: ' + str(path))
        self.status.set('Relatório sanitizado salvo. Aceite humano e revisão continuam obrigatórios; piloto não autorizado.')

    def poll(self):
        while True:
            try:
                kind, value = self.messages.get_nowait()
            except queue.Empty:
                break
            if kind == 'progress':
                self.status.set(value)
            elif kind == 'error':
                self.status.set(ERRORS.get(value, 'Falha de preparação; nenhum detalhe bruto foi salvo. Solicite revisão técnica.'))
            elif kind == 'done':
                self.status.set('Preparação concluída; testes e avaliação humana são etapas separadas.' if value == 'prepare'
                                else 'Testes automáticos: ' + self.report['automated_tests']['status'] + '. Itens humanos continuam não executados.')
        busy = self.worker is not None and self.worker.is_alive()
        active = self.active_lab()
        if not busy and not self.closing:
            self.prepare_btn.config(state='normal' if not active and not self.labs else 'disabled')
            self.tests_btn.config(state='normal' if self.preparation.ready and not active else 'disabled')
            self.lab_btn.config(state='normal' if self.preparation.ready and self.report['automated_tests']['status'] == 'PASSOU'
                                and not active and len(self.labs) < 6 else 'disabled')
            self.export_btn.config(state='normal' if not active else 'disabled')
        self.prep_status.set(' / '.join(key + ': ' + status for key, status in self.report['checks'].items()) +
                             '\nTestes automáticos: ' + self.report['automated_tests']['status'])
        if self.labs:
            data = self.labs[-1].recorder.data
            self.lab_status.set(f'Ensaios: {len(self.labs)} | eventos aceitos: {data["counters"]["events_accepted"]} | '
                                f'métricas por processos próprios | limpeza confirmada: {data["children_stopped"]}')
        if self.closing and not busy and not active:
            self.root.destroy()
            return
        self.root.after(100, self.poll)

    def close(self):
        if self.closing:
            return
        self.closing = True
        self.preparation.runner.cancel()
        for lab in self.labs:
            if lab.root.winfo_exists():
                lab.close()
            else:
                lab.stop()
        self.status.set('Encerrando somente processos próprios; aguarde a limpeza.')

    def run(self):
        self.root.mainloop()


def main(repository=None):
    if sys.platform != 'win32' or sys.version_info < (3, 11):
        raise SystemExit('Este assistente exige Windows 10/11 e Python 3.11+ com Tk. Nada foi instalado.')
    try:
        import tkinter as tk
        AcceptanceWizard(tk, repository or Path(__file__).resolve().parents[2]).run()
    except Exception:
        raise SystemExit('Não foi possível abrir o assistente. Confirme Python com Tk e use uma pasta local de teste.') from None
