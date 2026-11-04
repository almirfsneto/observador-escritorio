# Retenção do inbox sintético — Issue 14 / P1

Formato SQLite v2, sobre PR13/cf90de6. Não modifica Event v1, ACK v1 nem aceite
humano v1. Apenas dados fictícios, diretório privado fora de Git, DELETE/FULL,
secure_delete, cache sem spill. Não é armazenamento cifrado ou prova forense.

## Contrato temporal e recuperação

| Estado persistido | Prazo / limite | Após prazo |
| --- | --- | --- |
| Payload Event | 1 hora desde admissão local do lote | DELETE transacional |
| Receipt detalhado / ACK | 24 horas desde a mesma admissão | DELETE transacional |
| batch ID + digest + fonte | Vida inteira desse inbox, até 1024 IDs | Nunca expurgado automaticamente |
| event ID + fonte | Vida inteira desse inbox, até 10000 IDs | Nunca expurgado automaticamente |
| Fontes e high-water de batch/source_sequence | Até 32 fontes persistidas | Nunca regressam nem são removidos |

Fronteira inclusiva: age >= TTL está expirado. Não usar UTC do produtor para
retenção; uma fonte com relógio adiantado não prolonga a guarda. A sessão de
admissão expira em 15 minutos (UTC/monotônico), independentemente desses prazos.
Não há serviço de limpeza desligado: purge() ocorre ao abrir, em nova ingestão,
source_events() ou manutenção explícita, inclusive em pausa/expiração/stop.
Retry histórico é leitura e não dispara manutenção nem exige espaço de escrita.

Dentro da janela, batch canônico idêntico devolve o **mesmo ACK persistido**, sem
inserir; funciona após pausa, sessão expirada, erro pós-commit ou reabertura com
fonte autorizada. Digest diferente com receipt vivo = bridge_batch_id_conflict.
Após 24h, marker conhecido ou sequência antiga produz erro fechado
receipt_expired_or_unknown: não inventar ACK nem concluir que o commit não ocorreu.
Payload pode já ter expirado apesar de ACK histórico válido: written_count é o
INSERT histórico, não número de eventos ainda presentes nem conclusão de negócio.

IDs de batch/event são exclusivos no inbox inteiro; high-water é por fonte.
IDs nunca voltam a ser inéditos após purge. Não renovar banco/fonte para contornar
esgotamento: eliminar o banco elimina também a proteção histórica desse banco.
Não há exactly-once distribuído nem ordem global entre fontes.

## Relógios, migração e concorrência

O maior relógio local observado em manutenção é persistido atomicamente. UTC
regressivo (inclusive após restart) ou monotônico regressivo encerra admissão e
congela expurgo no último limite seguro, preservando ACKs. Reabertura expirada
permite vincular somente fonte já conhecida para recuperação read-only; não start. UTC congelado pode
atrasar limpeza; monotônico continua limitando a sessão. Salto UTC para frente
pode antecipar expurgo irreversível: não existe relógio confiável persistente nem
proteção contra administrador. Reabrir com relógio corrigido, nunca resetar markers.
Timestamp de admissão é tomado antes do commit, não um relógio de durabilidade.

v1 não tinha tempo de admissão: migração atômica concede janela completa a partir
da migração, conserva ACK byte a byte e constrói markers de todos os registros
existentes. Colisão entre fontes ou excesso de markers recusa/rollback da migração;
não apaga nem reescreve silenciosamente o histórico. Outros application_id/versões,
WAL/SHM, links/reparse/hardlinks e Git são recusados. Novo dono revoga dono anterior,
inclusive purge/histórico; BEGIN IMMEDIATE + epoch impede dois escritores válidos.
Não é fronteira contra escritor SQL não cooperante com o mesmo privilégio.

## Atomicidade, quota e diagnósticos

INSERTs, receipt, IDs e high-water pertencem ao mesmo commit. Purge remove somente
payloads/receipts numa transação separada e preserva markers. Fault pré-commit é
rollback; falha/kill pós-commit exige conferir receipt, não reenviar como lote novo.
Qualquer falha de manutenção/escrita fecha admissão com código estático. Depois de
falha pode-se recuperar receipt vivo por leitura; reabertura é requerida para nova
admissão. Abertura em disco sem espaço pode falhar antes de permitir leitura.

Principal 4 MiB; agregado padrão 13631488 bytes, reserva 4390920 bytes para rollback,
1 MiB de espaço livre mínimo, até 64 arquivos, 128 receipts vivos/10000 payloads.
Markers podem esgotar antes/depois da cota de bytes: erro explícito, sem eviction.
Budget esgotado também pode impedir purge: liberar somente espaço externo ao banco
com procedimento revisado; nunca apagar marcadores para liberar capacidade.
Freelist reutiliza páginas; não há VACUUM automático. Budget é lógico/amostrado,
não quota física OS, não inclui SSD/snapshots/backups/pagefile. ACL não protege
contra mesmo usuário/admin. SQLite ativo/inbox continuam em claro.

retention_snapshot() é síncrono da thread dona, **não chamar na UI**: contagens
persistidas e counters voláteis events_purged/receipts_purged/ack_recovered/
receipt_unavailable/capacity_rejected/storage_errors/clock_regressions + budget.
Purge conhecido conta após commit; falha pós-commit não desfaz contagem. Após kill,
RAM desaparece: consultar estado SQLite, não inferir perda pelos counters.

## Evidências reproduzíveis

`PYTHONPATH=src python -m unittest discover -s tests -p test_inbox_retention.py -v`
Testa fronteiras exatas, IDs/sequências após purge, regressões de relógio/restart,
ACK com budget cheio, duas instâncias, lock SQLite real, FULL via max_page_count,
BUSY/FULL/IO injetados, migração, invariant fuzz com seed fixa e os._exit real antes/
depois de commits de ingestão e purge. integrity_check na recuperação. Dados e
artefatos descartáveis. Não simula perda de energia física/SSD nem aceite humano.
EOF de processo dono perde RAM e libera handles; journal é recuperado na reabertura.
Chromium dedicado continua exercitando ACK/retry e stop/restart real do worker.
