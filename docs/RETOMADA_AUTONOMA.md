# Retomada atual — Issue33 / experimento de supervisão sintética

Base exata PR32/f1fb334bc4b9048c6a604610923e028ecd3ef658, branch filha
codex/synthetic-process-supervision. Issue33 e SYNTHETIC_PROCESS_SUPERVISION.md
são obrigatórios. CI base42006356534 verde e revisão do contrato registradas.
PR34/códigoe2a8655/CI42014095213 passou5/5. Windows3.11/3.12:280 descobertos,
278 executados/2 skips browser por Python; foco novo27/0 sem contagem dupla.
Linux218/62 por Python; Chromium2/0.16 novos portáveis +11 Windows executados.
Root responsivo/deadline sticky/fim físico provados, mas extras desconhecidos
mantêm cleanup_unconfirmed: bulk recusado e Job desarmado. Crash pós-start usa
recuperação por handle da raiz externa, NÃO automático do Job desarmado; nested
externo aberto confirmou zero. Pré-start conhecido provou kill-on-last-close.
Publicação imutável corrigiu desenho que substituía arquivos abertos; sharing
sozinho foi refutado. Ver logs/histórico falho e matriz em PROGRESS.
Último commit somente documental: conferir CI própria do HEAD final no PR34.
Root pode bloquear em API/FS/driver; dupla morte após disarm e Job armado retido
continuam limites. Flags só em memória, sem ledger durável/UI ou isolamento de extras.
Não alterar runtime/launchers/canais/adapter, PRs anteriores ou PR6; sem merge,
rebase, instalação, dados reais, coleta ou piloto. Próximo gate é revisão por SHA
com CI completa. Histórico anterior abaixo, não o estado atual da entrega.

# Retomada atual — Issue #30 / contrato de liveness (2026-11-05)

Branch `codex/cleanup-liveness-contract-issue30` criada sobre o SHA exato PR31/8fd16bcd00183eb04d3ac759fa91d57978260b56; PR31
segue draft, sem merge. Issue29 concluída exclusivamente como experimento isolado.
Ler Issue30 e `docs/CLEANUP_LIVENESS_DESIGN.md` antes de propor integração.

A etapa atual adiciona 11 testes em `tests/test_cleanup_liveness_design.py`:
contratos negativos de deadline/cancelamento/owner/handles/UI, dois casos adicionais
(salida tardia que preserva deadline e ACK sem pedido), e um processo real
sintético que prova que join(timeout) não elimina thread não-daemon bloqueada.
Teste inicial Linux Python3.13 9/9; CI do SHA inicial 457734be/42003106492
5/5 (9 novos casos). Depois da revisão de contrato, aguardar nova CI do HEAD
com 11 novos casos antes de concluir. Não houve alteração de src/, launchers,
WindowsObserver, adapter, IPC, runtime ou dados. Manifesto atualizado.

A arquitetura favorita **para investigação futura** é subprocesso supervisionado,
Job na criação e protocolo fechado, mas ainda SEM implementação ou deadline global.
Não iniciar migração nem piloto; originadores de Job adicionais desconhecidos no
PR31 e os gates Issue22/AI04/revisão humana continuam abertos.

---

# Retomada atual — Issue29 / Job List isolado

Base obrigatória PR28/508c38ad0996e7854c788cf08f655c8b65225707.
Branch filha codex/job-at-creation-study; ler Issue29, Issue22/atualizações,
parecer28 e docs/JOB_AT_CREATION_STUDY.md. Somente harness em tests/: não migrar
launchers/canais/NativeSession/C# nem habilitar adapter. Issue30 NÃO iniciada;
esperar revisão independente da Issue29 antes de discutir outra etapa.
PR31 / código518678a / CI41959802089 passou5/5. Windows3.11/3.12:240 executados/
2 skips browser por Python; foco novo17/0, antigo11/0. Linux191/51 por Python;
Chromium2/0. Dez casos Windows +sete portáveis novos executados nos dois Windows.
Membros adicionais não identificados: lista completa do Job contém os conhecidos;
positivo e nested externo aberto confirmaram zero de todos. Não inferir identidade
nem abrir PIDs extras. Rodadas falhas de contagem e barreira CLI preservadas em
PROGRESS. Último commit só documental: conferir CI do HEAD final no PR31.
Conferir resultados reais, skips, crash com raiz sem Job alvo e prova nested
externo aberto. Não inferir suporte humano10/11 de runner Server. PR6/anteriores
preservados; sem merge/rebase/instalação/coleta/piloto. Histórico abaixo.

# Retomada atual — Issue27 / diagnóstico Windows e stop pré-worker

Branch codex/suspended-cleanup-diagnostics, base exata PR25/d820396. Ler Issue27,
atualizações22 e pareceres23–25. A CI voltou a executar após ação do responsável;
base falha em dois testes SuspendedProbe em ambos os Windows. Não reutilizar a
hipótese antiga de falha pré-step nem declarar causa antes do snapshot fechado.

Diagnóstico ed7c50d/CI41929775944 comprovou fallback TerminateProcess prematuro:
AccessDenied após Job confirmado, espera posterior sinalizada e handles fechados.
Correção640bb36 espera saída pós-Job no orçamento original2s e só recupera
corrida com provas; testes focados passaram nos dois Windows. P2 já implementa
isolamento de stream/Tk/observação, startup com fallback e guard de execução única.
PR28/código6e0cf86, CI41931710044: cinco jobs aprovados; suíte225, Windows
223 executados/2 skips por Python, Linux184/41, Chromium2/0; foco suspenso11/0.
TclError real de controles destruídos não impediu filhos/queue/sampler e manteve
relatório false. Conferir checks do HEAD documental final no PR28 antes de aceitar.
Ler docs/ISSUE27_CLEANUP.md para evidência, limites e distinção real/injetado.
Rodar Windows3.11/3.12, Linux3.11/3.12 e Chromium; skips não são casos aprovados.
Nenhuma integração do launcher suspenso/adapter, merge/rebase ou dado real.
Histórico anterior abaixo descreve evidência por SHA, não o estado atual da CI.

# Retomada atual — complemento AI02 após estudo AI03

Continuar de codex/cleanup-worker-lifetime, filha de PR24/b974356 e PR23/5c37576.
AI01/02: binding retido e cleanup independente; complemento impede abandono do
worker daemon após main retornar. AI03 permanece SOMENTE em tests/ e design.
Suíte local211:173 executados/38 skips. Regressão real de intérprete com atraso
artificial falhou antes e passou após correção; não é teste de kernel Windows.

CI GitHub Actions falha antes das etapas nos cinco jobs, causa não exposta nesta
sessão. Os SETE casos Windows novos desta tarefa NÃO executaram. Não usar CIs
do PR21 ou nomes REAL dos testes como evidência desta revisão. Restaurar Actions
e reexecutar CI completa dos três PRs antes de aceitar as provas nativas.
A política Chromium local bloqueia extensão, sem workaround. Revisor técnico
IA nesta conversa deve fixar os três SHAs e conferir diffs/evidências por base.
Assinatura humana, AI04, isolamento mesmo token/admin e piloto seguem abertos.
Worker não daemon pode manter processo aguardando API travada; não há deadline
global comprovado. PR6 e anteriores preservados, adapter OFF, sem merge/rebase,
deploy, instalação ou dados reais. Histórico anterior abaixo.

# Retomada atual — estudo AI03, filha de PR23

Continuar de codex/suspended-launch-study, base codex/legacy-binding-cleanup
(PR23/5c37576). Ler Issue22, LEGACY_BINDING_CLEANUP e SUSPENDED_LAUNCH_STUDY.
AI01/02 implementados na base; AI03 é apenas arquitetura + harness em tests/.
Nenhum launcher em uso foi convertido. Suspenso→assign→resume mantém gap de
morte pré-assign; não declarar resolvido. Quatro casos nativos novos pendentes.

Prioridade: restaurar execução do GitHub Actions (jobs falham antes das etapas,
sem causa exposta; retry controlado não resolveu), reexecutar CI completa nas
duas branches, corrigir eventuais falhas e apresentar SHAs para revisão técnica
IA nesta conversa. Linux/skips não comprovam Windows; Chromium local bloqueia
extensões por política. Não alterar cobrança/permissões/política como workaround.

PR6/anteriores intactos, schema v1/CMD preservados, adapter OFF; sem merge/rebase,
instalação, deploy, dados reais ou piloto. AI04 e assinatura humana continuam
abertos. Não usar main isoladamente. Histórico e evidências anteriores abaixo.

# Retomada atual — Issue22 / AI01 e AI02

Branch codex/legacy-binding-cleanup, filha de PR21/8abbb5b. Ver PR/HEAD/CI em
PROGRESS e checks da entrega. Ler Issue22 e LEGACY_BINDING_CLEANUP.md. Binding
legado agora duplica referência retida; cleanup é independente por recurso.
AI03 fica em análise/teste isolado separado, sem mudança no launcher em uso.
PR23, código a332be4:206 descobertos,172 executados/34 skips localmente.
CI41900708978/41900750727 falhou antes das etapas (attempt2 também), sem logs;
Windows novo NÃO executado. Restaurar execução do Actions e reexecutar CI
completa antes de aceitar as regressões nativas. Causa administrativa não exposta.
Chromium local bloqueia a extensão por política; não contornar.
Revisor IA deve conferir SHAs finais nesta conversa; não simular assinatura
humana. PR6/anteriores intactos, schema v1/CMD preservados, adapter OFF, sem
merge/rebase/deploy/coleta real/piloto. Histórico anterior abaixo.

# Retomada atual — Issue 20 / fechamento verificado

Continuar de **codex/verified-handle-cleanup**, filha de PR19/bee7d1c. Consultar
PR21 e CI do HEAD em PROGRESS e nos checks do PR.
Código7740254/CI41857555311: cinco jobs aprovados;195 descobertos, Linux164/31
skips; Windows3.11 193/2 skips,3.12 192/3 (foreground guiado); Chromium2/0.
Push do mesmo código executou guiado3.12 (193/2). Quatro provas novas Win32 reais
passaram nos dois Pythons, nove negativos são injetados, não reuso real de PID. Não usar main isoladamente.
Ler docs/HANDLE_LIFETIME_REVIEW.md e Issue20 além dos documentos obrigatórios.
CloseHandle falho mantém referência em failed sem retry; Job exige processos
zerados e fechamento efetivo; métricas duplicam handle Popen retido, sem PID.

```
git fetch origin codex/verified-handle-cleanup
git switch -c codex/handle-cleanup-independent-review FETCH_HEAD
PYTHONPATH=src python -m unittest discover -s tests -v
```

Inventário residual: NativeSession.creation_ticks ainda tem fechamento sem
verificação e lookup PID; revisar separadamente, sem presumir cobertura por A3
das métricas. Nenhuma falha de campo alegada.

Prioridade seguinte: revisor distinto do implementador conferir diff/ownership/
callers (critério6 da Issue), usando SHAs e evidências finais. Não há sign-off
independente final nesta entrega. Separar falhas Win32 reais protegidas, falhas
injetadas e aceite humano. PR6 continua congelado3d4a770; v1 inalterado, adapter
OFF, sem merge/rebase/deploy/instalação na equipe/dados reais/piloto. As seções
abaixo descrevem o histórico; o ponto de continuação atual é esta branch.

# Retomada autônoma — estabilização após PR18

## Ponto atual obrigatório

Continuar da branch **codex/acceptance-stabilization**, filha de
PR18/233b3011cba6a9647bcf5e98d0a18e551b29fe3c. PR19: códigoed6099c, CI41844547231 cinco jobs aprovados
(Linux155/27 skips; Windows3.12 180/2 skips; Windows3.11 179/3 skips;
Chromium2/0;182 descobertos). O terceiro skip3.11 é foreground no ensaio guiado,
não aprovado nessa rodada; teste executado no3.12. Não inferir causa do skip humano. Consultar HEAD final em
PROGRESS.md; não usar main isoladamente. PR6 permanece congelado no SHA abaixo.
Leia também ACCEPTANCE_STABILIZATION.md, ACCEPTANCE_MATRIX.md e
SECURITY_REVIEW_PR18.md. Prioridade: estabilização/revisão, não adapter novo.
Auditar retornos CloseHandle dos wrappers compartilhados OwnedJob/ProcessProbe;
correção filha já trata CancelSynchronousIo,1168 normal e demais erros explícitos.

Relato humano sintético Win11 usando versão declarada PR6: 3 ensaios, 2 expirações,
3 cleanups, persistência opcional e avaliações positivas. Commit ZIP desconhecido,
um skip e um descarte não atribuídos; não solicitar JSON local para Git. Esse
relato é evidência positiva com ressalvas, não validação humana de PR18/filha.

Próximo passo: confirmar CI do HEAD da estabilização e revisão independente do
pacote de segurança. Executar testes/casos humanos faltantes só em laboratório
autorizado. Separar falhas injetadas, CI Win32 real e aceite humano Win10/11.
Retomada em branch nova a partir desta entrega, sem tocar PR6:

```
git fetch origin codex/acceptance-stabilization
git switch -c codex/acceptance-independent-review FETCH_HEAD
PYTHONPATH=src python -m unittest discover -s tests -v
```

Nenhum merge/rebase, adaptador OFF e piloto bloqueado. O histórico técnico abaixo
descreve a base PR18, não afirma que todas as lacunas humanas seguem sem relato.

# Histórico da base — Issue 17 / canal Windows isolado

## Branch correta e histórico preservado

Base anterior: **codex/verified-owned-channel (PR18)**, filha de
codex/synthetic-source-auth-model (PR16/294cb390a17b907ce31dbe3ddad3c32e55b43673).
Nunca main/PR16 isolados para continuar o novo canal. Não alterar/rebasear/integrar
PRs anteriores. Todos permanecem drafts. **PR6/codex/guided-windows-acceptance
continua3d4a77052b3dc9cf77805dd73f0bfd6d5dae674c**, reservado ao aceite humano.

```
git fetch origin codex/verified-owned-channel
git switch -c codex/owned-channel-independent-review FETCH_HEAD
PYTHONPATH=src python -m unittest discover -s tests -v
```

PowerShell em laboratório dedicado: `$env:PYTHONPATH='src'`, depois
`python -m unittest discover -s tests -v`. Não instalar na equipe nem coletar.
Ler AGENTS/SPEC/SECURITY/ROADMAP/PROGRESS/DECISIONS, OWNED_CHANNEL.md,
STACK_REVIEW_PLAN.md, SOURCE_AUTHENTICATION.md, INBOX_RETENTION.md,
OFFLINE_BRIDGE.md, DIAGNOSTICS.md, STORAGE_HARDENING.md e a Issue17.

## O que existe e o que não pode ser confundido

- **Real, isolado:** processo Python -I -S -B, pipes anônimos Win32, quatro handles
  na lista de herança, Popen retido/identidades kernel, chave32 somente bootstrap,
  HMAC com direção/epoch/sessão/geração/nonce/sequência, wire canônico16KiB e cap64.
  Código em owned_channel*.py; sem UIA/DOM/rede/serviço/host/autostart/instalação.
- **Real nos ensaios Windows:** identidade/handshake/pausa/reproof/cleanup e casos
  adversariais do peer. Afirmações ampliadas dependem da CI do respectivo HEAD.
  Não usar validade de número de handle como herança: comparar objetos kernel.
- **Simulado/injetado:** PR16 continua modelo em memória; ticks alterados não são
  PID reuse forçado. Clock24h/TTL de inbox são injetados, não espera real24h.
  TTL curto natural3s não substitui ensaio humano15min ou sono/energia.
- **Não implementado/ligado:** adapter WPF→canal→inbox e autenticação do
  WindowsObserver C# antigo. NativeSession/C#/lançador e schema JSON de aceite v1 estão
  intocados na base; a filha acrescenta diagnóstico separado. ACK da fixture IPC não confirma pausa UIA, commit ou negócio.

## Evidências a consultar por commit

Baseline149: Linux136/13 skips, Windows147/2 browsers separados; CIs de PR16
registradas em PROGRESS. Primeira Etapa A22f99e5/CI41809413254: cinco jobs
aprovados,155 descobertos, Windows153/2 skips, Linux139/16 skips, Chromium2 reais.

Ampliação928b301/CI41811218903: Linux/Chromium/Windows3.11 aprovados, Windows3.12
FALHOU em prontidão do harness parent-kill. Não promover essa rodada a sucesso.
Testes de capacidade e demais adversariais daquele job passaram, mas o job falhou.
Revisão260900d/CI41812922153: CINCO jobs aprovados,170 descobertos,
Windows3.11/3.12 168 executados/2 browsers skipped, Linux143/27 skips, Chromium2
reais sem skips. Todos os14 novos testes Windows executaram processos/handles
reais, incluindo kill do parent, WPF/descendente/decoy não herdados, lista alargada
recusada ANTES da geração da chave, replay, duas instâncias, cancelamento e inbox.
Causa interna da antiga prontidão vazia não foi provada; rodada revista passou.

Revisão0588d8a / CI41814049436 também teve CINCO jobs aprovados, mesmos170 testes
e contagens. Handle retido do worker/CancelSynchronousIo foi exercitado nos dois
Windows, com não herança e liberação após cancelar IO pendente. Não reabre thread
ID. Commit final documental registra essa prova; conferir CI do HEAD no PR18.


Caminho git receive-pack apresentou500/commit_refs; publicação suportada pela API
criou commits fast-forward com blobs/árvore SHA idênticos ao snapshot local, lease
no HEAD esperado e force=false. Commits locais não publicados foram preservados
em branches de snapshot. Não houve merge/rebase/force em PR existente. Usar HEAD
remoto PR18, não snapshots locais antigos, ao retomar. API é fallback de publicação,
não autorização para mover outras branches ou ignorar política/rejeição explícita.

## Gates técnicos e revisão independente

1. Conferir matriz final Linux/Windows3.11/3.12 e Chromium real, nomes/counts/skips
   e árvore do commit. Reproduzir unit tests em checkout limpo e ambiente dedicado.
2. Revisor independente audita argumento de capacidade: quatro handles explícitos,
   chave gerada após spawn/identidade, só por bootstrap32+EOF; parentquery limitado,
   flags limpadas e bootstrap fechado antes de descendentes. Processo sonda é
   possuído e comparado por DuplicateHandle/CompareObjectHandles, sem lhe entregar
   objetos de referência. Negar lista de herança alargada antes de gerar chave.
3. Investigar qualquer falha de prontidão por fase/exitcode fixos, nunca dumping
   chave/frames/env/exception locals. Não afrouxar check de identidade/reparse
   nem trocar prova real por simulador. Kill do parent deve terminar descendente.
4. Executar revisão adversarial de outra conta/sessão em Windows autorizado e
   ensaio humano10/11. Não há prova contra mesmo token/admin/injeção. Criar contas,
   elevar ou contornar políticas não foi feito nesta execução. Essas provas são
   gates abertos, não uma alegação de impossibilidade do SO.
5. Só depois, projetar entrypoint C# autenticado dedicado e teste da projeção WPF
   já permitida, com captura default off e ACK real do provider separado. Não
   reutilizar ready.pid como autenticação do emissor. Adapter atual continua OFF.
6. Seguir STACK_REVIEW_PLAN.md: inventário/SHAs e unidades conceituais de revisão.
   Nada de merge/rebase/retarget agora. Convergência futura exige autorização e
   revisão humana; aceite PR6 não migra automaticamente ao snapshot novo.

## Retenção, capacidade e riscos que permanecem

Payload1h e receipt24h desde admissão; markers de1024 batches/10000 events/32 fontes
não expiram. Saturação por API normal, purge/restart e reabertura final são testados
sem patch de limite/reset. Batch stress usa oito sessões normais128, respeitando
cap de receipts vivos; dados/clocks todos fictícios. receipt_expired_or_unknown
não nega commit. Nunca resetar DB para contornar anti-replay. Futuro arquivamento/
rotação precisa fronteira persistente e autenticada de revogação; ainda não existe.

Rollback falho/retorno incerto de commit descarta conexão e exige reopen; snapshots
counts.*=null/reopen_required=true. Counters RAM se perdem no kill. SQLite ativo/
inbox em claro; DPAPI só arquivo. Budget é lógico/amostrado, não quota física do
SO/SSD/backups/admin. Sem promessa de apagamento forense/zeroização Python.

WPF30/30 não implica WinForms (0/30) ou apps reais. Chromium descartável/Server2025
não é aceite humano Chrome/Edge/Windows10/11. Não contornar política unpacked
local. Worker restart real é WorkerStopped/Inspector.targetCrashed+nova timeOrigin,
não mutação de variável. PR6 tem roteiro VALIDACAO_MANUAL_WINDOWS.md para operador,
relatório fora de Git e gates humanos/LGPD pendentes. Nenhum piloto está autorizado.

## Fechamento e próxima execução

Documentação final registra código0588d8a/CI41814049436: cinco jobs;14 novos casos
Windows reais, sete novos portáveis/capacidade, mais o baseline. Compileall,
wheel sem dependências runtime novas e manifesto124 arquivos verificados.
A próxima atividade é revisão independente do protocolo/ACL/herança e execução
entre contas/sessões autorizadas, seguindo STACK_REVIEW_PLAN.md. Não basta mais
código para aprovar piloto ou adapter. Se revisão permitir continuação técnica,
novo entrypoint C# deve provar origem pelo próprio canal antes de qualquer WPF
capturado entrar no inbox; UIA ACK e inbox ACK permanecem separados.

Nenhum processo de observação foi instalado ou permanece ativo; as execuções Windows desta tarefa foram sintéticas em CI. O responsável
relatou separadamente execução humana Win11/PR6, conforme a seção inicial. NativeSession/C#/aceite v1 e branchPR6 preservados.
