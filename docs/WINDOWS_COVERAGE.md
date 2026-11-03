# Cobertura comparativa Windows — diagnóstico experimental

O caminho padrão UIA permanece inalterado. `--coverage-probe` no provider é um
modo explícito e separado: mesmos argumentos PID/caminho/criação/prazo e somente
SyntheticTaskApp/SyntheticWpfTaskApp. Não integra eventos ao stream nem à fila.

Usa SetWinEventHook **restrito ao PID fictício**, dois intervalos unitários:
EVENT_OBJECT_INVOKED e EVENT_OBJECT_STATECHANGE, WINEVENT_OUTOFCONTEXT. Não existe
hook de teclado/mouse, injeção de DLL, clipboard ou hook indiscriminado de todos
os processos. Aceita somente objeto CLIENT/child 0, janela da instância autorizada
em foreground e classe Win32 Button/WindowsForms10.BUTTON. Lê somente classe,
não caption/Name/Value/Text; exclui editores/senhas e objetos filhos não resolvidos.
IDs/handles/classes/PIDs não saem no diagnóstico, somente contagens agregadas.

Prazo próprio máximo 20s, stop/EOF, máximo 128 handles e 10 mil notificações
aceitas. Reporta excluídos, descartes, tempo decorrido, CPU/RAM do próprio probe
e maior atraso de entrega WinEvent (clock DWORD do evento até callback). Isto
não mede intenção humana nem a latência completa do aplicativo.

STATECHANGE é **mudança de estado observada**, não clique/Invoke inferido. Mesmo
INVOKED é notificação de acessibilidade, não prova de intenção/resultado de
negócio. Nenhum deles é promovido automaticamente a ui_action. WPF pode não
expor HWND por botão e fica excluído conservadoramente. Ausência de callback é
incompatibilidade observada nesse caminho, não prova de ausência de trabalho.

`test_windows_coverage.py` estimula 30 ativações padrão por UIA em cada framework,
mede Invoke pelo provider atual, roda probe em paralelo, confirma pausa via ACK
e emite SYNTHETIC_COMPARATIVE_COVERAGE. Não altera fixtures para fabricar eventos.
Foco e notificações podem ser coalescidos. Teste com InvokePattern não equivale a
mouse/teclado humano nem valida cobertura de aplicativos profissionais. Quando
WinForms continua sem ação semântica suficiente, a estratégia recomendada é
adapter opt-in baseado em API de aplicação/DOM autorizado, com contrato específico
e teste de cobertura; não hooks globais nem leitura de conteúdo como fallback.

Referências técnicas: Microsoft Learn SetWinEventHook, Event Constants
(EVENT_OBJECT_INVOKED/STATECHANGE), UI Automation Events Overview. Implementação
original com APIs do OS, sem bibliotecas externas incorporadas. Aceite humano
Windows 10/11 e benchmark de custo em máquina dedicada continuam pendentes.

Evidência CI 41741819622: WPF 30 Invoke/30 estímulos, WinForms 0/30; probe
conservador não aceitou notificações em ambos (objetos não suportados excluídos).
Não há ganho de cobertura comprovado. Sem notificações aceitas,
`callback_delivery_peak_ms` agora é null: nenhuma amostra. A rodada original
mostrava zero; isso não demonstrava latência igual a zero.
