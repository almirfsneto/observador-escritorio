# Issue 20 — fechamento e identidade de recursos próprios

Base obrigatória: PR19, codex/acceptance-stabilization,
bee7d1c29b3c61acbc2e8123c6b1682647dfeae7. Filha: codex/verified-handle-cleanup.
Sem alteração de PR6, schema de aceite v1, adaptador (OFF) ou processos observados.

## A1 / A2 — fechamento validado e estados de ownership

CloseHandle tem argtypes HANDLE/restype BOOL declarados. O helper compartilhado
faz uma única tentativa. Sucesso remove a referência; erro mantém handle e estado
failed, produz somente cleanup_unconfirmed. Repetir close não repete a chamada
Win32. Não há retry automático, reutilização do slot ou log de GetLastError,
handle, PID, path ou locals. Objetos em falha ficam retidos nos respectivos donos
até o fim do controlador; não são prova de liberação. Isso pode reter recursos,
mas evita fechar um objeto alheio após uma falha de propriedade incerta.

OwnedJob encerra explicitamente os processos associados com TerminateJobObject,
consulta JOBOBJECT_BASIC_ACCOUNTING_INFORMATION até ActiveProcesses=0 (prazo 2s)
e só então tenta CloseHandle. Falha de terminate/query/timeout não impede a
tentativa de fechamento, porém cleanup_confirmed fica falso mesmo se CloseHandle
suceder. CloseHandle falho também impede confirmação, mesmo com processos zerados.
KILL_ON_JOB_CLOSE continua como fallback de lifetime; não é usado como única prova
de término. A confirmação cobre os membros desse job, não referências duplicadas
por terceiros, processos fora do job ou uma fronteira contra mesmo token/admin.
A janela preexistente entre Popen e atribuição ao job não é resolvida aqui; o
ensaio de descendente libera sua criação somente depois da atribuição confirmada.

CommandRunner tenta job, kill/wait do comando, reader.join e fechamento de stdout
mesmo se outro recurso falhar. Não fecha stdout sob uma leitura ainda bloqueada;
registra incerteza e retém referências. Erro de cleanup invalida retorno de sucesso,
produz PreparationError estático e bloqueia outro lançamento naquele runner.
Timeout com limpeza comprovada ainda permite retry. Construtor de job que falhe
na própria limpeza entrega o dono ao caller, para não perder a referência.
O canal isolado continua drenando futures/fechando os demais handles em falha.

OwnedSampler tenta todos os probes, retém os que falharam e não os reabre. Erro
inicial não inventa amostra; fechamento falho marca disponibilidade unavailable.
Saída normal encerra amostragem e conserva amostras históricas válidas, sem alegar
medida final. cleanup_confirmed só é verdadeiro após close completo sem falhas.
Aceite v1 continua igual: children_stopped também exige limpeza das métricas.

## A3 — vínculo de identidade desde a primeira amostra

ProcessProbe recebe o objeto Popen retido, nunca um PID. Duplica seu handle com
QUERY_LIMITED_INFORMATION/VM_READ/SYNCHRONIZE e herança falsa. Controlador usa
seu pseudohandle atual, também duplicado. Não usa OpenProcess, varredura ou nome.
Creation ticks vêm do handle de origem antes da duplicação e são conferidos no
handle duplicado antes de qualquer leitura de memória. Handle sinalizado/encerrado
é recusado; o objeto do kernel retido elimina a troca inicial por reuso de PID.
Probes injetados são seam de teste, não fronteira contra código malicioso no parent.

## A4 — token de ACL

O fechamento do token próprio de user_sid também verifica BOOL. Falha retém o
dono na instância WindowsSecurity, bloqueia reutilização e impede retorno do SID /
continuidade da configuração de ACL. Gravidade secundária: retenção de recurso e
falha de disponibilidade; não há vazamento ou exploração observados. LocalFree
não é CloseHandle e não foi reclassificado nesta entrega.

## Evidências e critérios de revisão

- Injeção: false/erros/timeout de job, fechamento de probe/token, identidade inicial
  substituída antes da memória, múltiplos recursos, futures, reader.join, construtor
  falho e bloqueio de retry. Não são falhas reais de kernel nem reuso real de PID.
- Windows real: HANDLE_FLAG_PROTECT_FROM_CLOSE em handle próprio de job e probe,
  CloseHandle recusado de fato; job com pai/descendente e ActiveProcesses >=2 antes
  do teardown, depois zero; duplicação do mesmo objeto de Popen, herança falsa,
  criação correspondente e recusa após exit. Somente processos sintéticos próprios.
- Recuperação só no teste: retirar a proteção deliberada do handle ainda vivo e
  fechá-lo diretamente, com finally/addCleanup. Não é retry de produção incerto.
- Consultar PROGRESS/PR para quais testes realmente executaram por OS/Python;
  skips não aprovam casos. Nenhuma falha em campo/exploração foi demonstrada.
- Critério 6 da Issue: revisão do diff por pessoa distinta do implementador ainda
  PENDENTE. Triagem da Issue e esta autorrevisão não são sign-off final independente.
  Revisar ownership, consulta do job, referência em construtor falho e cleanup dos
  callers antes de qualquer autorização futura. CI não é aceite humano Win10/11.
