# RETOMADA AUTÔNOMA — após Issue 11

## Base correta e preservação do aceite

Repositório almirfsneto/observador-escritorio. Não usar main isoladamente.
PRs #1→#2→#3→#4→#6→#7→#8→#9→#10→#12→#13 permanecem drafts, sem merge.
PR12: codex/closed-lab-diagnostics sobre codex/task-discovery (PR10).
PR13: codex/offline-source-bridge sobre codex/closed-lab-diagnostics.

**Não modificar codex/guided-windows-acceptance (PR6), head 3d4a77052b3dc9cf77805dd73f0bfd6d5dae674c.**
O responsável usará aquela versão para aceite humano Windows. Não confundir CI
de versões posteriores com aceite dessa versão. Demais PRs anteriores preservados.

Retomada integrada:
```
git fetch origin codex/offline-source-bridge
git switch -c codex/inbox-retention FETCH_HEAD
PYTHONPATH=src python -m unittest discover -s tests -v
```
Ler integralmente AGENTS/SPEC/SECURITY/ROADMAP/PROGRESS/DECISIONS, DIAGNOSTICS.md,
OFFLINE_BRIDGE.md, STORAGE_HARDENING.md, WEB_EXTENSION.md, TASK_DISCOVERY.md e
QUESTOES_ARQUITETURA_PRO.md. Conferir CI atual do HEAD antes de declarar sucesso.

## Estado e evidências

P1 código b9cb6ec / CI 41752385456: diagnóstico fechado v1 separado do aceite v1,
contadores reconciliados, gauges/cache sem SQL na UI, faults/rollback e timeout
explícito de shutdown. 109 descobertos; Windows108/1 skip browser separado,
Linux98/11 skips; job Chromium anterior um teste real.
P2 código integrado 633d3ec / CI 41752388247: 121 descobertos, Windows119/2 skips
de browser separado, Linux109/12 skips; job Chromium dois testes reais aprovados.
Mudanças documentais posteriores registram evidência; consultar PR/CI atuais.

Native .NET8/SQLite/ACL/DPAPI e controlador fictício executados em Windows CI,
que é Server2025, não teste humano Windows10/11. WPF30/30 não implica WinForms:
continua 0/30 no caminho comparado até evidência contrária. Skips não são êxito.

Browser usa Playwright1.62.0 apenas em teste + Chromium descartável no job
web-synthetic. OBS_BROWSER_TEST=1 habilita testes reais; núcleo não depende dele.
Política unpacked do executor local bloqueia extensão: não alterar/contornar.
No CI, teste força StopWorker via Target.closeTarget, observa Inspector.targetCrashed
(WorkerStopped) e nova timeOrigin. Host DevTools pode persistir; wrapper.close/
targetDestroyed não são prova correta. Retry do mesmo batch e ACK arquivo após
restart foram comprovados. Idle/sono/energia naturais ainda precisam de testes.

## Reproduzir sem coleta

`python -m observador.diagnostics --out /pasta/fora-do-git/saude.json` salva só
estado desativado, sem abrir fixture/provider. Diagnóstico não contém eventos,
paths, IDs/UUIDs, hostname, usuário, títulos ou texto livre. Não alterar contrato
de aceite humano v1. DiagnosticHistory é por vida de processo; não é assinatura.

`python -m observador.task_discovery --out /pasta/fora-do-git/candidatos.json`
usa só corpus artificial e arquivo exclusivo. `observador.mining_evaluation.evaluate_synthetic_mining()` retorna TP17 FP0 FN0 TN28 em 45 pares/10 traces/42
eventos construídos; precisão/recall1 não são acurácia de mundo real.

Bridge: API OfflineBridge(path fora de Git) começa disabled; authorize fontes
fictícias, control(start), ticket; popup importa Ticket local, exporta batch,
Python read_batch/ingest, write_bridge_document(ACK), popup importa ACK. Não há
socket/upload/NativeMessaging nem permissões extras; instruções completas em
OFFLINE_BRIDGE.md. ACK é inbox commitado histórico, não admissão atual, resultado
de negócio ou pausa de todos os produtores. Ordens são por fonte, não globais.

## Limites a preservar

SQLite ativo e inbox estão em claro; arquivo DPAPI não cifra origem/pagefile/backups.
Budget mede arquivos lógicos com reserva de journal, não quota física/admin-proof.
Erros depois de commit conhecido não são perda; rollback/outcome incerto fecha
writer e aparece uncertain. Purge pode incluir DB anterior e inserts da mesma
transação; não somar fases como exatamente-uma-vez. Contadores em RAM não sobrevivem
à morte do processo. Pipeline não faz retry oculto de ações.

Arquivos só DECLARAM proveniência: hash não autentica ACK contra outro processo
local. Mesmo batch idêntico recupera receipt sem regravar; novo dono revoga tickets
não commitados. Inbox tem limites de espaço/linhas/receipts, mas ainda não TTL por
tempo; expiração encerra admissão, não apaga receipts. Não ligar export/import
automático ou coleta real para resolver essas pendências.

## Próxima entrega autônoma

Implementar retenção e expurgo do inbox preservando high-water marks/receipts
necessários para ACK recuperável e anti-replay; testar expiração, quota, crash,
reabertura e janela de idempotência. Especificar quando um receipt antigo deixa
de ser recuperável sem apresentá-lo como inexistência de commit. Depois avaliar
IPC autenticado com permissões mínimas e adaptador opt-in do controlador fictício,
com ACK de produtores distintos e diagnóstico fechado, sem presumir ordem global.
Ampliar dataset rotulado independente e negativos; não transformar proximidade
em causalidade nem span em ganho real.

Nenhum monitoramento de pessoas, dado real, instalação na equipe, autostart,
screenshot real, telemetria, recurso pago, deploy, merge ou piloto autorizado.
Aceite humano Windows10/11, Chrome/Edge e gates LGPD permanecem pendentes.

## Atualização Issue 14 / P1

Entrega em codex/inbox-retention sobre PR13/cf90de6; ler INBOX_RETENTION.md.
Não usar PR13 isolado para novas alterações de retenção. Payload 1h/receipt24h,
markers sem TTL/caps bloqueantes, migração v1 conservadora. Após receipt vencer,
receipt_expired_or_unknown não significa ausência de commit. Não resetar inbox
para contornar limite. CI nova ainda precisa ser conferida no PR/head; baseline
121 e 14 testes novos locais. Próximo estágio: P2 em branch filha distinta,
ameaças/autenticação com testes negativos; nenhum IPC inseguro será habilitado.

## Atualização Issue 14 / P2 — base mais recente

codex/synthetic-source-auth-model é filha de codex/inbox-retention. Usar a filha
para continuar, mantendo os dois PRs separados/draft. Ler SOURCE_AUTHENTICATION.md
e INBOX_RETENTION.md antes de implementar canal. Modelo HMAC não autentica peer;
probe de filho Windows não associa peer ao canal. IPC/controller adapter continuam
desligados conforme P2.6. Não passar resultado do modelo a OfflineBridge.authorize.
Implementar primeiro canal herdado de filho próprio + vínculo kernel, entrega de
chave/herança mínima e EOF/cancelamento/negativos Windows; só depois opt-in fixture.
Nada de host NativeMessaging instalado. Tests novos de modelo+probe: nove rodados
Linux/um Windows skip; evidências CI serão registradas após conclusão.
