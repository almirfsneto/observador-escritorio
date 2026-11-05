# Issue33 / AI02L2 — supervisão isolada de processo sintético

Base exata PR32/f1fb334bc4b9048c6a604610923e028ecd3ef658, branch filha
codex/synthetic-process-supervision. Pré-requisitos conferidos: CI42006356534
success5/5 no SHA base, parecer do contrato32 registrado como COMMENT, sem
assinatura humana/independência de autoria. Ler Issue33 e CLEANUP_LIVENESS_DESIGN.

## Fronteira do experimento

Somente tests/: raiz supervisora + Python próprio -I -S -B com thread não-daemon
bloqueada indefinidamente em Lock. Worker join(.05) retorna e is_alive prova
insuficiência. Seu main atende comandos sintéticos; raiz continua ticks e observa
pong. Isso prova progresso dessa raiz, NÃO UI Tk, API/driver arbitrário ou SLA.
Worker normal libera lock e termina; atraso pós-deadline é dimensão independente.
Nenhum runtime, launcher operacional, C#, IPC ativo, extensão ou coleta alterado.
Uma costura de SCRIPT exclusivamente na classe de testes PR31 permite fixture
fixa por subclass, preservando seu default e todos os testes anteriores.

NativeWorker reaproveita apenas CreateProcess de testes: STARTUPINFOEXW/JOB_LIST,
Job anônimo próprio não herdável/KILL_ON_JOB_CLOSE, filho suspenso, herança FALSE,
ambiente mínimo e stdio NULL. Membership no handle retido antes de resume, sem
assign/breakaway/fallback. Não cria descendant adicional. Atributos/lpValue vivos
até Delete VOID; retorno normal cumpre contrato de API, não prova externa de heap.

## Comunicação, fatos e proveniência

Arquivos temporários exclusivos com replace atômico e tamanho256, não pipes nem
IPC operacional. Campos v/nonce/seq/state ou command; comandos ping/cancel/release,
seq limitada64, estados enumerados, nonce PÚBLICO synthetic-supervision-v1. Não é
autenticação/isolamento de outro código do mesmo token. Nenhum payload profissional,
PID, handle, caminho pessoal, argumento ou exceção livre no snapshot. Slot de
capacidade só no controle privado launcher→raiz para DuplicateHandle, nunca no log.
Arquivos sintéticos são apagados após saída observada, antes de declarar limpeza.

Ledger mantém expiração e erros sticky. deadline_expired é registrado ANTES da
tentativa de teardown; saída tardia nunca apaga o fato. ACK de cancelamento sem
pedido é erro; pedido sem ACK não vira prova de saída e mantém unconfirmed mesmo
se recursos depois fecharem. physical_cleanup_confirmed distingue fatos físicos
do estado final com erro histórico. Nenhum estado enviado pelo worker confirma
exit/job_zero/handles: esses fatos provêm das APIs da raiz. UI é sempre unknown.

Raiz espera startup8s, observa deadline local200ms após sinal de início e faz
polls5ms; são budgets DE TESTE. Wait de término2s e confirmação de zero2s são
esperas distintas; não são promessa de término global. Teste positivo normal usa
budget2s. Cancelamento explícito registra pedido sem inventar ACK. Caso de saída
tardia libera o lock da própria fixture após expiração, exige sinal nativo e
mantém worker_state=deadline_expired. Não invoca CancelSynchronousIo/TerminateThread
nem os._exit como mecanismo operacional; não alega testar driver travado.

## Ownership e membros desconhecidos: regra nova deste experimento

QueryInformationJobObject(ProcessIdList), lista completa limitada16, compara IDs
somente com GetProcessId dos handles já retidos. Nenhum OpenProcess/PID recebido
como autoridade. Não exige cardinalidade global fixa nem atribui identidade a
membros extras. Confere membership do subordinado vivo e recusa lista ausente,
truncada, duplicada ou contendo membro desconhecido ANTES de TerminateJobObject.

Se ownership é inequívoco, tentar término do Job, exigir sinal do processo e zero
por QueryInformationJobObject; TRUE no término não prova saída. Recusa de API é
erro sticky e fallback usa SOMENTE TerminateProcess no handle próprio conhecido.
Se ownership é incerto, NÃO invocar término coletivo. Consultar limites do Job,
remover APENAS KILL_ON_JOB_CLOSE, SetInformationJobObject e consultar novamente
para confirmar desativação. Só então pode liberar Job sem matar extras ao fechar.
Limpeza emergencial termina apenas processo próprio retido. Job não zerado mantém
unconfirmed. Disarm negado preserva Job em quarentena, sem retry/close; teste
portável prova essa política. Se o SO depois destruir a raiz, o fechamento de
handles pelo SO pode ainda aplicar kill-on-close. Essa limitação NÃO está resolvida
nem autoriza Job operacional compartilhado/saída segura nessa situação.

Cleanup tenta independentemente atributos, processo, zero do Job e todos os
handles. Recusa de CloseHandle mantém failed e não repete slot. Estado incerto não
recebe confirmação, ainda que outros recursos fechem. Quarentena é diagnóstico,
não promessa de recuperação sem autoridade adicional. Membros adicionais do PR31
continuam de origem desconhecida; o novo harness interrompe a prova se os observar.
Não altera o comportamento nem as evidências históricas dos outros experimentos.

## Matriz de testes e revisão

14 testes portáveis: ledger/controlador, expiração/saída tardia, ACK, cancelamento,
comunicação, bounds de protocolo/lista, criação/atributos/membership, erros de
teardown/handles e quarentena quando disarm negado. APIs são INJETADAS.

Dez testes Windows preparados: normal; lock/deadline/responsividade; cancelamento
sem ACK; saída tardia; ownership extra INJETADO com disarm e fim conhecido reais;
falhas de membership/terminate/query/wait/comunicação/Delete INJETADAS em recursos
reais; CloseHandle protegido REAL; morte REAL do launcher antes/depois do início
do worker; nested com Job externo mantido aberto e zero. Nenhum caso obrigatório
Windows pode ser promovido de skip a aprovado. Foco separado precede suíte geral;
são os mesmos casos, não somar duas vezes. CI completa inclui ambos Linux e Chromium.
Até consultar a CI desta revisão, negativos portáveis não são prova de Win32.

No crash, raiz duplica apenas handle do processo próprio de launcher retido,
confere imagem/tempo/sessão, sem guardar Job alvo. Launcher checa ownership antes
da barreira e morte; raiz mata somente esse launcher sintético e exige sinal do
worker ANTES de emergency cleanup. Nested mantém Job externo aberto, verifica
seus membros conhecidos antes do crash e confirma zero após saída, antes do close.
Finally tenta IO/reader/handles independentemente. Emergency cleanup não satisfaz
asserções de sucesso; falha sempre fica explícita.

Próxima revisão: conferir SHA/base/diff, logs reais Win3.11/3.12, ausência de bulk
termination no negativo de unknown members, disarm verificado/quarentena, deadline
sticky e provas físicas distintas. Win Server CI x64 não é humano Win10/11, ARM64,
x86, outras contas, admin, injeção ou garantia global de API/driver. Raiz também
pode bloquear em suas próprias APIs/FS. Nada de watchdog operacional, piloto,
merge/rebase, instalação ou dados reais. Próximo passo depende de nova revisão,
não migração automática de cleanup ou canais para processos.

Comandos (PowerShell: definir $env:PYTHONPATH='src'):

    PYTHONPATH=src python -m unittest discover -s tests -p 'test_process_supervision*.py' -v
    PYTHONPATH=src python -m unittest discover -s tests -v

Fontes: contrato e referências Python/Microsoft em CLEANUP_LIVENESS_DESIGN.md;
contratos STARTUPINFOEX/Job List/Delete em JOB_AT_CREATION_STUDY.md. Não foram
importados componentes externos nem dependências runtime.

## Primeira observação Windows e ajuste do ensaio de crash

470cc6a/CI42010080293 falhou com quatro expectativas erradas por Windows. A origem
adicional continuou desconhecida mesmo sem descendant explícito. Root teve ticks,
pong, join insuficiente, deadline_expired e prova física de fim/zero/closes; erro
ownership continuou sticky, por isso cleanup_unconfirmed era o resultado correto.
Não converter essa recusa real em aprovação irrestrita. Positivo agora exige fim
físico, disarm confirmado e NÃO chamada de TerminateJobObject se houver extras;
classificação continua unconfirmed. Sem extras, permanece confirmação completa.

No crash com Job incerto, launcher primeiro confirma disarm e só então transmite
capacidade própria para raiz e espera sua morte. Raiz mata somente launcher,
observa sua saída e tenta terminar worker pelo handle retido; exige sinalização,
não abandona órfão. termination_mode=root_retained_process_handle é recuperação
externa real, NÃO prova de kill-on-last-close. Se ownership for conhecido e Job
armado, termination_mode=kill_on_last_close é provado por saída sem kill da raiz.
Nested pode desarmar seu próprio Job externo incerto antes do crash; mantém aberto
para observar zero, sem bulk stop de desconhecidos. Snapshot preserva as duas
incertezas de ownership. Nenhum teste abre ou mata processo extra por PID.

Se Wait não confirma saída, conservar o handle de processo conhecido aberto, mesmo
após tentar os demais recursos: não descartar a última capacidade de emergency
cleanup de worker possivelmente vivo. Snapshot marca retenção após a tentativa e
permanece unconfirmed. Negativo Windows conserva duplicata independente e usa
Wait real para comprovar fim antes do PRIMEIRO close da referência retida; isso é
recuperação explícita de teste, não retry de CloseHandle falho nem apagamento de
erro. Ausência de prova/autoridade do SO continua impedindo confirmação.

O pedido cancel tem janela cooperativa local50ms com polls da raiz, sem join/lock
compartilhado. cancel_refusal_observed exige resposta explícita da fixture;
ausência de resposta é caso distinto, também unconfirmed. Exit anterior ao ACK
não apaga pedido sem confirmação; não enviar ping depois de cancel para evitar
sobrescrever o único comando pendente. Um novo negativo portável cobre essa
corrida:15 portáveis +10 Windows=25 novos focados, sem soma dupla na suíte.
A janela não amplia deadline local200ms nem afirma cancelamento de I/O/driver.
