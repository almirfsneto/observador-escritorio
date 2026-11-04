# Retomada autônoma — Issue 14

## Base integrada e preservação do aceite

Entregas em draft, sem merge:
- PR15: codex/inbox-retention sobre PR13/codex/offline-source-bridge/cf90de6.
- PR16: codex/synthetic-source-auth-model sobre PR15. Usar esta filha para continuar.

**Não modificar codex/guided-windows-acceptance (PR6), commit
3d4a77052b3dc9cf77805dd73f0bfd6d5dae674c**, reservado ao aceite humano. PR13 e
anteriores preservados. Não usar main/PR13 isolados para retomar as alterações.

```
git fetch origin codex/synthetic-source-auth-model
git switch -c codex/verified-owned-channel FETCH_HEAD
PYTHONPATH=src python -m unittest discover -s tests -v
```

Depois do checkout, ler AGENTS.md, SPEC.md, SECURITY.md, ROADMAP.md, DECISIONS.md,
PROGRESS.md, docs/INBOX_RETENTION.md, docs/SOURCE_AUTHENTICATION.md,
OFFLINE_BRIDGE.md, DIAGNOSTICS.md, STORAGE_HARDENING.md, WEB_EXTENSION.md,
TASK_DISCOVERY.md e QUESTOES_ARQUITETURA_PRO.md. Consultar Issue14/PR15/PR16.
SOURCE_AUTHENTICATION.md e o modelo/probe pertencem à filha PR16.

## Evidência de código verificada

| Entrega | Código / CI (5 jobs aprovados) | Núcleo por Python 3.11/3.12 | Chromium dedicado |
| --- | --- | --- | --- |
| P1 | 6d521cf / [41759340778](https://github.com/almirfsneto/observador-escritorio/actions/runs/41759340778) | 139 descobertos; Linux127 executados/12 skips; Windows137/2 skips | 2 reais, sem skips |
| P2 integrada | bc23073 / [41759416977](https://github.com/almirfsneto/observador-escritorio/actions/runs/41759416977) | 149 descobertos; Linux136 executados/13 skips; Windows147/2 skips | 2 reais, sem skips |

Skips não são aprovação: Linux não executa APIs/desktop Windows; browser está
nos dois testes reais do job dedicado, não no núcleo. Windows CI Server2025 não
é aceite humano Windows10/11. Probe novo de filho próprio passou nos dois Pythons
Windows; não autentica peer de canal. WPF30/30 não implica WinForms (0/30) ou apps
reais. Baseline cf90de6 tinha121 testes, Linux109/12 skips.

Commits posteriores de documentação/manifesto registram essas provas; conferir
CI do HEAD final no PR antes de declarar nova alteração aprovada. Não atribuir
CI antiga a código novo. Nenhum observador permanece executando após os testes.

## Retenção e recuperação: invariantes

Payload1h/receipt24h desde admissão local, não desde UTC do produtor. IDs globais
batch/event + high-water por fonte sem TTL; capacidade esgotada bloqueia sem
eviction/reset. Retry vivo recupera mesmo ACK por leitura, até com quota sem
espaço para escrita. Após janela, receipt_expired_or_unknown NÃO nega commit.
ACK histórico não garante payload ainda retido, negócio concluído ou pausa atual.

Migração v1→v2 é atômica, concede janela a partir da migração e recusa colisão
sem apagar histórico. Clock regressivo fecha admissão/congela purge; fonte
conhecida pode vincular para recuperação read-only. Sessão15min e purge são
separados. Manutenção só quando executada; nenhum daemon. Não resetar banco/
fontes para contornar markers. Snapshot tem SQL na thread dona, nunca chamar na UI.

Rollback falho/exceção no retorno de commit FECHA a conexão. Snapshot sinaliza
reopen_required=true, counts.*=null e uncertain_transactions. Não recuperar ACK
possivelmente não commitado daquela conexão: reabrir e consultar SQLite. Erro
APÓS retorno bem-sucedido do commit é caso conhecido diferente/recuperável por
leitura. Tests distinguem ambos, kill pré/pós-commit e EOF de JSON truncado.

## P2 sob alternativa segura e próxima tarefa técnica

Aplicada Issue14/P2.6: threat model/protocolo, simulador HMAC/challenge e negativos,
mais probe separado de identidade do filho Windows. **Nenhum IPC novo/adapter
controlador→inbox habilitado**, nenhum host NativeMessaging instalado.
SyntheticAuthModel assume identidade e entrega de chave; NÃO autentica processo.
Não usar seu resultado para OfflineBridge.authorize. inspect_owned_child consulta
PID/criação/caminho/sessão no handle Popen próprio, mas não associa peer ao canal.

Implementar em nova filha de PR16 primeiro canal herdado do NativeSession:
1. Vínculo do peer do canal a handles/PID/criação/caminho/sessão verificados.
2. Herança mínima e chave efêmera por handle privado, nunca arquivo/CLI/env/log.
3. Testes nativos adversariais de outra sessão/conta, colisão, EOF/truncamento,
   timeout/cancelamento/restart/duplo escritor e recursos limitados.
4. Só após prova integrada, adapter opt-in inicialmente desligado, recebendo
   exclusivamente projeção já permitida da fixture/controlador fictícios.

Named pipes exigem verificação kernel bidirecional/DACL logon SID/recusa remota;
não basta PID recebido em JSON nem HMAC sem pareamento privado. Não alegar defesa
contra mesmo usuário/admin sem prova. ACK transporte/inbox/admissão não confirma
pausa do produtor: exigir ACK nativo da geração solicitada. Sem ordem global ou
causalidade entre fontes. Nenhuma escolha técnica rotineira precisa ser escalada.

## Limites e aceite humano

SQLite ativo/inbox em claro; DPAPI só arquivo. Budget lógico/amostrado com reserva,
não quota física OS/SSD/backups/admin. Counters RAM se perdem no kill. Fontes/ACK
em arquivos continuam não autenticados. Model benchmark64 frames é só Python em
memória, não IPC/overhead de UI/SLA. Sem prova de apagamento forense.

Job browser usa Playwright1.62.0 somente teste, Chromium descartável autorizado.
Política unpacked local permanece intacta. Restart real exige WorkerStopped/
Inspector.targetCrashed e nova timeOrigin; host/wrapper DevTools pode persistir.
Não substituir por mutação de variável. Idle/sono e Chrome/Edge humanos pendentes.

Operador humano deve usar PR6 e docs/VALIDACAO_MANUAL_WINDOWS.md em Windows10/11
dedicados, marcar só etapas feitas, aguardar15min e salvar JSON fora de Git.
Não usar CI/simulador como aceite. Sem dados reais, equipe, captura oculta,
autostart, deploy, merge, transmissão externa ou piloto autorizado. Gates humanos
e LGPD continuam pendentes. Nenhum trabalho contínuo é prometido após esta execução.
