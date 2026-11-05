# Issue #30 — liveness de cleanup sob API bloqueante (estudo isolado)

**Status:** proposta de arquitetura e negativos sintéticos, **não** implementação de watchdog. Base congelada: PR #31, commit `8fd16bcd00183eb04d3ac759fa91d57978260b56`. Este estudo não altera `src/`, nenhum launcher, adaptador, IPC ou coleta. A Issue #29 foi concluída **apenas como experimento isolado**.

## 1. Falha de progresso que continua aberta

`LaboratoryWindow.stop()` usa worker `threading.Thread(daemon=False)`; `run()` chama `join(timeout=20)`. Segundo a documentação Python, timeout de `join` não mata a thread, e uma thread não-daemon viva pode impedir a saída do interpretador. `CleanupStatus` registra falhas e tentativas; não é uma prova de deadline global. Uma chamada nativa que não retorne pode manter a execução presa e ainda deter um lock de cleanup. Não alterar o worker para daemon nem adicionar `os._exit`/`TerminateThread` para fabricar conclusão.

A prova do PR #31 associa um processo sintético a Job **no momento da criação**, mas está em `tests/` e **não** elimina a janela `Popen -> assign` dos launchers operacionais. A presença de membros adicionais de origem desconhecida nos Jobs torna especialmente necessário revisar membership e o limite de propriedade antes de qualquer integração.

## 2. Contrato de evidência separado

Não misturar **liveness** (progresso do supervisor/worker), **teardown** (recursos realmente encerrados), **UI** (disponibilidade do controle de pausa/encerramento) e **ownership** (identidade de processos/handles). Para cada tentativa, manter apenas estados e contagens fechados; não emitir PID, endereço, título de janela, argumento, segredo, stack, texto de exceção ou caminho pessoal.

| Dimensão | Evidência necessária | O que não basta |
| --- | --- | --- |
| Worker | término observado por handle do **processo próprio** ou join + `is_alive` | retorno de `join(timeout)` sozinho |
| Cancelamento | pedido registrado, retorno da API e confirmação posterior da operação | retorno de `CancelSynchronousIo` sozinho |
| Filhos | handles próprios sinalizados **e**, quando aplicável, Job com contagem zero | último PID, envio de kill, ou Job criado mas sem prova |
| Handles | retorno verificado de cada `CloseHandle` e sem retentar slot incerto | chamar close sem examinar BOOL |
| UI | responsiva, indisponível ou desconhecida; fato separado da limpeza | janela fechada = backend encerrado |
| Prazo | deadline vencido com status `deadline_expired`, sem promoção a concluído | timeout do controlador ou da CI |

A modelagem em `tests/test_cleanup_liveness_design.py` é **somente de contrato e injeções**. O campo `cleanup_error` deve ser sticky: mesmo havendo provas posteriores de recursos, não apagar a falha já registrada. Uma expiração pode coexistir com término posterior; `deadline_elapsed=True` prevalece no estado de liveness (`deadline_expired`), enquanto `worker_exit_confirmed=True` registra a saída tardia. O encerramento comprovado dos recursos pode ser classificado separadamente como `cleanup_state=confirmed`, sem apagar a violação do prazo. Um ACK de cancelamento sem solicitação é evidência inválida.

**Limite adicional do classificador:** `Evidence` é um snapshot imutável, não um histórico/ledger. Não impede que uma origem não confiável envie outro snapshot com `deadline_elapsed=False` ou `cleanup_error=False`. Uma implementação futura precisará manter flags monotônicas de prazo/falha e atestar a proveniência dos handles/Job; os testes atuais **não** demonstram essa persistência nem autenticidade.

## 3. Alternativas técnicas comparadas

| Alternativa | Vantagem | Falha residual | Decisão nesta fase |
| --- | --- | --- | --- |
| A. Thread não-daemon + `join(timeout)` e `CancelSynchronousIo` | menor mudança; pode cancelar algumas chamadas síncronas de E/S | drivers e funções sem cancelamento; lock preso; Python continua com thread viva | insuficiente como garantia global |
| B. Processo de cleanup **isolado**, supervisionado por raiz com Job próprio desde `CreateProcess`, protocolo fechado e morte por Job | separa travamentos do espaço de execução do controlador; permite observar processo próprio e Job | supervisor também pode falhar; nested Jobs, herança de IPC e membros extras precisam ser comprovados; kill/espera não são deadline absoluto | **candidato prioritário para experimento futuro**, não integração |
| C. Watchdog externo independente do controlador e do worker | sobrevive à falha do controlador se também possuir capacidade de encerramento | novos processos, serviço/conta/privilegio, disputa de último handle do Job e risco de falha compartilhada | não implementar sem modelo de autoridade e revisão humana |

**Escolha provisória:** estudar B em processo **sintético**, não executar cleanup real em um subprocesso sem redesenhar posse de handles. Antes de transportar funções para outro processo, confirmar quais handles são duplicáveis com direitos mínimos, quais recursos são encerráveis somente no processo pai, e quais operações de Tk precisam ocorrer no thread de UI. A `CancelSynchronousIo` é ferramenta localizada, não plano de contingência genérico: solicita cancelamento de E/S síncrona do thread indicado e pode não interromper outras APIs. A documentação Microsoft também alerta que algumas operações não são canceláveis e que há corridas quando threads são compartilhados.

## 4. Esboço de supervisão, **não implementado**

1. Raiz identifica e cria Job anônimo, não herdável, com `KILL_ON_JOB_CLOSE`, e um processo de trabalho sintético **associado na criação**, de acordo com o contrato validado em `tests/` no PR #31. Não usar `Popen -> assign` como fallback silencioso.
2. O Job é propriedade inequívoca da raiz. O processo de trabalho recebe somente descritores/capacidades explicitamente autorizados. Provar ausência de herança extra; não copiar diretamente o esquema de quatro handles do IPC legado sem rever sua autenticação.
3. O protocolo de estado carrega somente enums, sessão/geração e contador limitado; não carrega dados de tela, senha ou argumentos livres. A raiz observa handle do filho e estado de Job; uma resposta `done` **não é** prova suficiente de fechamento.
4. Em deadline, registrar `deadline_expired`; solicitar cancelamento cooperativo, se houver; aguardar retorno observável. Se não houver, **tentar** terminar exclusivamente Job/filhos próprios, conferir processo e Job zerados e fechar handles com retorno verificado. Um erro preserva `cleanup_unconfirmed`.
5. Se a raiz morrer, o contrato kill-on-last-close **só** se aplica se ninguém conservar outro handle do Job e se o Job efetivamente contém os processos. Crash antes de criar Job, membro fora do Job, serviço externo e bloqueio do kernel não são resolvidos automaticamente.
6. Nenhuma promessa de limite máximo absoluto quando o SO ou driver não retorna. Distinguir tempo de reação da UI, tempo para lançar tentativa de término e confirmação de término efetivo.

## 5. Matriz de negativos e provas que faltam

| Caso | Tipo de prova | Aceite limitado |
| --- | --- | --- |
| `join(timeout)` com lock retido e thread não-daemon | **processo real sintético**, em `tests/test_cleanup_liveness_design.py` | timeout não encerra thread; processo **de teste** é morto e reaproveitado com handle próprio; não valida produção |
| cancelamento requisitado e não atendido | injeção/controle sintético | não declarar worker encerrado nem limpeza confirmada |
| ACK sem solicitação prévia | contrato sintético | rejeitar o snapshot, não inventar cancelamento |
| worker termina após deadline | contrato sintético | `deadline_expired` permanece, com saída tardia reportada separadamente; cleanup requer prova independente |
| UI indisponível enquanto recursos fecham | modelo sintético | relatar UI separadamente; não inferir falha/sucesso de backend por UI |
| morte da raiz sem prova sobre filhos | modelo sintético | `unconfirmed`, nunca declarar kill-on-close sem Job próprio comprovado |
| worker sai mas Job/handles ainda não confirmados | modelo sintético | cleanup fica `pending` ou `unconfirmed`, nunca `confirmed` |
| erro de cleanup observado, fechamento posterior de outros recursos | modelo sintético | falha sticky, não promover a sucesso |
| API Win32 bloqueante não cancelável e falha do supervisor | **pendente, não executar sem desenho detalhado** | teste contido em processo sintético com watchdog da CI e saída garantida; nenhuma API de cliente |

**Executar** o módulo de testes por `python -m unittest discover -s tests -p test_cleanup_liveness_design.py -v` em Windows 3.11/3.12 e Linux 3.11/3.12. A suíte geral deve continuar verde e Chromium não pode ser desabilitado. O caso de subprocesso prova apenas que o processo **sintético** pode ser terminado pelo seu supervisor; não prova que o processo operacional esteja isolado por Job.

## 6. Riscos residuais, limites e gates

- Mesmo token/admin, elevação, processos de terceiros, outra conta/sessão e injeção continuam fora do isolamento demonstrado.
- `TerminateJobObject` age sobre **todos** os membros do Job; membros adicionais de origem não identificada no PR #31 exigem delimitação antes de qualquer Job operacional.
- `CancelSynchronousIo` cobre pedidos síncronos pendentes do thread informado, não cancelamento universal; falhas de drivers e corridas devem ser esperadas.
- Não abrir processos por PID não validado; não duplicar ou encerrar handles de processos alheios.
- Relatório de `liveness` e resultado de `CleanupStatus` não são a mesma máquina de estados. `children_stopped` só recebe prova positiva no fluxo existente, nunca por timeout do supervisor.
- Revisão humana e ensaio interativo Windows 10/11, AI04, hardening de dados/IPC e piloto permanecem abertos na Issue #22. Nenhum merge/rebase, ativação do adapter, coleta real, instalação, rede ou serviço nesta etapa.

## Referências técnicas

- Python 3.12 `threading.join` / `daemon`: https://docs.python.org/3.12/library/threading.html
- Microsoft `CancelSynchronousIo`: https://learn.microsoft.com/en-us/windows/win32/api/ioapiset/nf-ioapiset-cancelsynchronousio
- Microsoft cancelamento e funções não canceláveis: https://learn.microsoft.com/en-us/windows/win32/fileio/canceling-pending-i-o-operations
- Microsoft Job Objects e kill-on-last-close: https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects
- Microsoft `TerminateJobObject`: https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-terminatejobobject

**Decisão solicitada para etapa seguinte:** somente após revisão deste desenho e dos negativos, autorizar um novo estudo de supervisão por processo isolado, sem migração do runtime e sem alegar deadline global.
