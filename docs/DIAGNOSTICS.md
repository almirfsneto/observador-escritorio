# Diagnósticos fechados v1 — Issue 11, prioridade 1

Base PR10 (502d6d3), sem alterar branch PR6 nem contrato de aceite humano v1.
Schema fechado: DIAGNOSTICS_SCHEMA.json; implementação observador.diagnostics.
Somente estados enumerados, contagens, gauges e durações; nenhum evento, caminho,
PID, UUID, host/usuário, título, campo ou observação livre. Não é um sanitizador
para textos externos. Valores desconhecidos são null/lacunas, não zeros inventados.

`DiagnosticRecorder.sample(stream=...,writer=...)` coleta cada componente sob
seu lock; não faz SQL/disco na thread da UI. O writer publica cache numérico sob
um lock breve, sem segurar esse lock durante SQLite. `LaboratoryWindow` oferece
`diagnostics_snapshot()` sem mudar o fluxo de aceite. CLI `python -m
observador.diagnostics --out /pasta/fora-do-git/saude.json` exporta estado
**desativado**, sem abrir fixture/provider. Escrita exclusiva fora de Git, sem
upload; reader <=64 KiB rejeita campos/chaves duplicadas/NaN/estados impossíveis.
DiagnosticHistory recusa replay, regressão de contadores ou reinício de componente
dentro de uma vida; iniciar outra história para outro processo. Isso não autentica
origem nem é assinatura/registro forense. Não exporta identificador de máquina.

## Reconciliação e janelas

Python (lifetime de LabStream):
- received = accepted + rejected + coalesced + overflow;
- accepted = drained + buffered + discarded.
received conta mensagens event processadas na janela viva; mensagens após fim
não entram nessa janela. invalid_messages inclui erros de controle também.
Pausa/stop/expiração contabilizam descarte de eventos antes aceitos e ainda não
drenados. Focus coalescido é separado de overflow e rejeição de geração/replay.

Writer (lifetime de AsyncLabQueue):
- received = enqueued + ingress_rejected;
- enqueued = buffered + inflight + written + duplicates + write_rejected + uncertain.
Submissão após shutdown, batch >100 ou fila cheia = ingresso rejeitado; erro do
writer fecha a admissão e rejeita pendências sem gravá-las. Registro já commitado
não vira perda quando um erro ocorre depois. Payload diferente com mesmo UUID é
conflito, não duplicata silenciosa. Falha de rollback/outcome ambíguo fica uncertain,
fecha writer e exige reabertura/revisão, sem retry oculto ou exactly-once.

Purge inclui linhas que já existiam antes deste processo: rows_at_open + written
- purged pode reconciliar rows_current, porém outros writers e outcome incerto
impedem prova global. row_balance é balanced/unreconciled/unavailable, com lacuna
quando não demonstrado. Não comparar purge diretamente com escritos nesta vida.
Native callback/dropped/depth pertencem à amostra de outro processo, não à mesma
fase de aceitação Python; não somar para deduzir perda de usuário. Health antigo
sem gauges é compatível, mas registra native_queue_unavailable. Amostra >2s é
stale. Nenhuma ordenação/atomicidade global é prometida entre componentes.

## Falhas e medições

LabFaultPlan só existe na API do armazenamento sintético, sem CLI/configuração de
produção, acesso de rede, elevação ou alteração de disco externo. Injeta BUSY,
FULL, IO antes da transação/depois de insert/antes/depois do commit e rollback,
ou purge. Testes usam diretórios descartáveis, lock real SQLite, FULL de quota,
filesystem livre simulado, encerramento real os._exit e reabertura/integridade.
Gauges observam diretório durante journal vivo e após commit, não continuamente.
Orçamento continua admissão lógica, não quota física do SO/SSD/backups; SQLite
ativo continua em claro. Contadores são voláteis: morte abrupta perde diagnósticos
em RAM e batches pendentes; o arquivo SQLite reaberto é uma janela nova.

Controle mantém pause/fim fail-closed e ACK nativo. Teste Windows do controlador
injeta estado de storage indisponível e exige pausa confirmada, depois retomada
explícita; não é aceite humano nem teste de falha física de energia/SSD. Tests de
faults transacionais separam commit conhecido de rollback/outcome incerto.

Written conta INSERTs de uma transação commitada; se a cota de linhas expurga
registros nessa mesma transação, eles entram também em purged e podem nunca ter
ficado visíveis fora dela. Não interpretar written como retenção indefinida.
Exemplo local medido com um evento fictício: principal atual 16.384 bytes, pico
agregado amostrado com journal 29.208, reserva 4.390.920 e limite 13.631.488 bytes,
9 observações. Valores dependem da plataforma/rodada, não são teto físico ou SLA.
