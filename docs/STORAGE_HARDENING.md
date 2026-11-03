# Armazenamento sintético endurecido

A fila existente continua opt-in; `VALIDAR_LABORATORIO.cmd` e o JSON de aceite v1
permanecem compatíveis. Não há coleta real nem migração do schema de eventos.

## Limites efetivos

Banco principal: 4 MiB; diretório dedicado: orçamento padrão 13 MiB. Antes de
abrir/purgar/escrever, contabiliza todos os arquivos do diretório, inclusive
journal/WAL/SHM/arquivos inesperados. Rejeita subdiretórios, links, reparse points,
hardlinks e mais de 64 entradas. Não apaga arquivos desconhecidos. Reserva
conservadora de rollback: tamanho máximo do banco + overhead por página +
128 KiB para cabeçalho/setor/margem; exige também 1 MiB livre no filesystem.

DELETE journal, synchronous FULL, temp_store MEMORY, cache_spill OFF, batch <=100,
max_page_count e cache nominal de 2 MiB limitam o caminho do escritor. Cache sem
spill evita múltiplos segmentos de journal. Admissão e verificações antes do
commit podem rejeitar operações; o orçamento **não é uma cota imposta pelo OS**
nem mede continuamente picos. Outro programa/admin pode escrever fora do modelo;
o diretório precisa ser exclusivo. Metadados, clusters, snapshots, backups,
alocação física/compressão do volume e arquivos fora desse diretório não são
contados. Não há promessa de cota total do volume. Falta um VFS/volume com quota
para garantir limite físico contra escritores não cooperantes.

## Falhas e recuperação

Erros retornam códigos estáticos; perdas/rejeições são contadas. Falha de disco,
quota ou lock pausa a captura pelo controlador, sem bloquear a UI em SQLite.
Banco corrupto é preservado e a fila recusa continuar; não há reset silencioso.
SQLite recupera rollback journal na reabertura. Expurgo ocorre ao abrir/escrever
e na thread ativa; desligado não existe serviço de retenção. secure_delete não
garante apagamento forense. Lotes ainda em RAM podem se perder em encerramento
abrupto: não há confirmação de durabilidade por evento na captura nativa.

## ACL e DPAPI

Antes de escrever, aplica DACL protegida no diretório dedicado e arquivos
existentes: somente SID do usuário atual e SYSTEM, sem herança de grupos amplos.
Novos auxiliares herdam ACL do diretório. Erro de ACL impede abertura. Não altera
ACL de ancestrais nem solicita elevação. Unix usa 0700/0600. Não é uma defesa
contra outro processo do mesmo usuário ou administrador; revisão adversarial
com outra conta Windows ainda é necessária. Validação de links não elimina TOCTOU
contra ator local com acesso equivalente.

`observador.dpapi_archive.write_archive(store, destino)` é um **protótipo explícito**
de arquivo sintético DPAPI no escopo do usuário, com autenticação/integridade do
Windows, UI proibida e formato versionado. Só aceita LabEventQueue e projeção
fechada; saída exclusiva e diretório protegido. `read_archive` valida novamente.
Não foi ligado automaticamente à interface. **O banco SQLite ativo continua em
claro**, inclusive timestamps/IDs/payload; proteger um arquivo exportado não cifra
a fila original. Memória Python, pagefile, crash dumps e backups ficam fora da
proteção. A portabilidade depende do perfil/chaves Windows; não exportar chaves.
Antes de escolher cifragem da fila ativa, revisar alternativas no documento de
arquitetura. Nenhuma destas medidas libera piloto.

WAL/SHM preexistentes são recusados sem checkpoint/remoção, antes de abrir SQLite.
Não converter formatos de journal não suportados implicitamente: recuperação WAL
exige ferramenta/migração revisada em cópia sintética. Journal DELETE de rollback
continua recuperável na reabertura. Tests de symlink Windows tentam criá-lo;
somente erro efetivo de privilégio ausente gera skip, sem alterar privilégios.
