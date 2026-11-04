# Retomada autônoma — Issue 14 / retenção e modelo de autenticação

## Base e branches preservadas

P2 PR16: codex/synthetic-source-auth-model sobre P1/PR15 (usar P2 para continuar).
P1 PR15: codex/inbox-retention sobre codex/offline-source-bridge (PR13/cf90de6).
Não usar main/PR13 isolados para continuar retenção. Todos os anteriores são drafts,
sem merge. Não modificar codex/guided-windows-acceptance (PR6), congelada em
3d4a77052b3dc9cf77805dd73f0bfd6d5dae674c para o aceite humano.

Ler AGENTS/SPEC/SECURITY/ROADMAP/DECISIONS/PROGRESS e INBOX_RETENTION.md,
OFFLINE_BRIDGE.md, DIAGNOSTICS.md, STORAGE_HARDENING.md, WEB_EXTENSION.md,
TASK_DISCOVERY.md, QUESTOES_ARQUITETURA_PRO.md. Consultar Issue14 e PR15/CI atuais.

```
git fetch origin codex/synthetic-source-auth-model
git switch -c codex/verified-owned-channel FETCH_HEAD
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Evidência e semântica atual

Baseline cf90de6:121 descobertos/Linux109 executados/12 skips. P1 código448c3aa,
CI41757902728:5/5 jobs;136 descobertos/Linux124 executados/12 skips,
Windows134/2 skips browser separado; Chromium2 reais sem skips. Revisão final
acrescenta observação do DB recuperado antes da retenção do construtor. Conferir
CI do HEAD, não inferir que código posterior já foi testado remotamente.

Payload1h/receipt24h desde admissão local, NÃO desde relógio da fonte. IDs globais
batch/event + high-water por fonte sem TTL; caps bloqueiam admissão sem eviction.
Retry vivo recupera mesmo ACK por leitura, até com quota sem espaço de escrita.
Após janela: receipt_expired_or_unknown não significa ausência de commit.
Migração v1→v2 atômica concede janela a partir da migração; colisão recusa sem
apagar histórico. Clock regressivo fecha admissão/congela purge; fonte conhecida
pode vincular para ACK read-only. Sessão15min e purge são fenômenos separados.
Não resetar banco/fontes para contornar markers. Manutenção só quando executada,
nenhum daemon. Snapshot de retenção usa SQL na thread dona, não chamar na UI.

## Próxima prioridade

P2 precisa análise de ameaças, peer autenticado e adapter Windows só fictício
opt-in. Sem prova de origem forte, entregar especificação/simulador/negativos e
NÃO ligar IPC inseguro, conforme Issue14/P2.6. Preferir canal herdado de filho
próprio; named pipes exigem ACL/peer kernel bidirecional, chave privada efêmera,
EOF/cancelamento/timeout e testes de outra sessão/colisão. Nenhum host instalado.
ACK de inbox/admissão não é confirmação de pausa dos produtores nem resultado de
negócio. Sem ordenação/causalidade global entre fontes.

## Limites que não podem ser promovidos a sucesso

SQLite ativo/inbox em claro, DPAPI só arquivo. Budget lógico observado com reserva,
não quota física do OS/admin/SSD/backups. Contadores RAM se perdem no kill;
commit incerto precisa receipt, não inferência de perda. Fonte/ACK em arquivo não
são autenticados. WPF30/30 não implica WinForms (0/30) ou aplicações reais.
Windows CI Server2025 e Chromium descartável não são aceite humano Win10/11 ou
Chrome/Edge. Modelo/fixture/fault injection não substitui desktop/usuário real.

Job web usa Playwright1.62.0 apenas teste. Não contornar política unpacked local.
Restart real observa Inspector.targetCrashed/WorkerStopped + nova timeOrigin;
host DevTools/wrapper pode persistir. Não substituir por mutação de variável.

Humano: usar exclusivamente PR6 e docs/VALIDACAO_MANUAL_WINDOWS.md em Windows10/11
dedicados, marcar só etapas feitas e salvar JSON fora de Git. Nenhum piloto,
coleta de pessoas/dado jurídico, instalação na equipe, captura oculta, autostart,
deploy, transmissão externa ou merge autorizado. Nenhum processo observa após
estes testes; não existe desenvolvimento contínuo depois da execução.

## P2 implementada sob gate seguro

PR16 contém docs/SOURCE_AUTHENTICATION.md, SyntheticAuthModel fechado em memória,
negativos/fuzz100 mutações/benchmark64 frames e inspect_owned_child desconectado,
com consulta nativa Windows em teste. Modelo assume identidade/entrega de chave:
NÃO autentica peer, NÃO chamar OfflineBridge.authorize com seu resultado. Sem
IPC novo/controller adapter/NativeMessaging instalado. Aplicado P2.6.

146 descobertos, Linux133 executados/13 skips; Windows144 executados/2 skips
browser separado no código ef8ca60 / CI41758466029 (5/5 jobs). Chromium2 reais.
Probe nativo passou nos dois Pythons Windows. Confirmar CI do HEAD final.
Probe kernel Windows testa somente filho próprio da fixture; não confundir com
peer do canal. Antes de opt-in: handle/peer bidirecional, entrega de chave privada,
herança mínima, DACLs adversariais/EOF/truncamento/timeout/cancelamento/colisão.
Confirmar resultados/head no PR e atualizar evidências após qualquer mudança.

Revisão adicional P1: rollback falho/exceção no retorno de commit fecham a conexão,
reopen_required=true e counts=null. Nunca recuperar ACK de leitura local que pode
conter receipt não commitado. Reabrir e consultar SQLite. Erro posterior a commit
retornado com sucesso é caso diferente/recuperável por leitura. 18 testes de
retenção/139 totais (Linux127/12 skips) após essa revisão; conferir CI atual.

Integração da correção de conexão incerta de P1: agora149 descobertos, Linux136
executados/13 skips; Windows esperado147/2 browsers separados, somente declarar
após CI do head. Modelo/probe continuam isolados. Não promover CI antiga às novas
regressões; consultar PR15/PR16 e commits finais.
