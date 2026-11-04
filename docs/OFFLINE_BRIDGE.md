# Ponte offline exclusivamente sintética — Issue 11, prioridade 2

Implementação de laboratório em observador.offline_bridge. **Não é integração
contínua de produção**. Nenhum socket/servidor, nativeMessaging, serviço, upload,
autostart ou permissão adicional MV3. Operador transfere arquivos locais revisados.
Windows e web têm fontes independentes; nenhum arquivo autoriza observar pessoas.

## Proveniência e limites de confiança

Fonte fechada: kind web/windows, version 1, instance UUID fictício, origin fixo
http://127.0.0.1:8765 ou owned_synthetic_process, tab_slot 1/2 para web e null para
Windows. Sessão de cada Event precisa corresponder à instância autorizada. Browser
valida sender e origem/caminho antes de exportar; arquivos só declaram proveniência.
**Uma origem escrita em JSON não autentica navegador/processo.** Chamador confiável
faz authorize explícito e deve conhecer instância/slot; não é barreira contra
outro processo do mesmo usuário. SHA-256 detecta alteração do lote, não autentica
ACK contra falsificador local. IPC autenticado/NativeMessaging revisado fica futuro.

Inicialmente disabled. authorize só nessa fase; máximo três fontes ativas (duas
abas e uma fixture Windows). control(start) admite por até 15 min (UTC/monotônico,
clock backwards encerra); pause/resume/stop retornam ACK de **admissão no bridge**,
não confirmação de produtores. Pausar também os produtores exige seus próprios
ACKs; não existe comando global implícito nem promessa de atomicidade multi-fonte.
O controlador humano PR6 não foi alterado.

## Fluxo de arquivos e ACK explícito

1. Em perfil descartável permitido, iniciar fixture web pelo popup e exportar o
   JSON sintético anterior. Usar session_id fictício dos eventos para autorizar
   a fonte; uma única aba de teste usa tab_slot 1.
2. Criar OfflineBridge com arquivo novo fora de Git, authorize(source),
   control('start'), ticket(source['instance']). Salvar ticket com
   write_bridge_document(ticket, repository, destino_novo). Se o JSON anterior
   veio de outra sessão, popup rejeita o ticket.
3. Popup: selecionar arquivo Ticket. Clique em Exportar lote da ponte. Isso não
   transmite nada: baixa arquivo local com até 100 eventos, sequência por fonte,
   epoch/generation e batch UUID. Sem ACK, exportações repetem exatamente o lote
   pendente, inclusive após reinício do worker/encerramento da captura.
4. Python: read_batch(arquivo); ack = bridge.ingest(batch). Salvar ACK com
   write_bridge_document. No popup, selecionar arquivo ACK. Cursor avança apenas
   se epoch/generation/source/batch/contagens e digest correspondem ao pendente.
5. Novo ticket após pausa/retomada descarta envio pendente não confirmado do canal
   da ponte e começa após cursor atual, sem replay através da pausa. Sequências
   puladas ficam source_gap_count. Eventos originais continuam na exportação local
   anterior da extensão até início de nova sessão/fechamento da aba.

Receipt + eventos + high-water marks são commitados na mesma transação SQLite
FULL; ACK só depois do retorno do commit. Retry de batch idêntico devolve receipt
histórico, sem regravar, inclusive após reabertura/pausa/expiração. **Esse ACK não
prova admissão atual nem conclusão de negócio.** Mesmo batch UUID com conteúdo
alterado, sequência regressiva ou batch fora de ordem são rejeitados. Se erro
pode ter ocorrido no commit, fechar admissão e verificar receipt antes de retry;
nunca inventar exactly-once ou descarte definitivo. Novo processo/epoch revoga
tickets não commitados do anterior e inicia disabled; receipts antigos persistem.

Proveniência Windows usa make_batch(ticket, eventos do stream autorizado), sem
ler apps ou arquivos genéricos; adaptador automático controlador→bridge não foi
ligado nesta entrega. Testes unificam duas fontes sanitizadas em inbox próprio,
não atribuem rotina causal entre desktop e web.

## Persistência, ordem e testes

Inbox separado: formato próprio app-id/version 2 (migração v1 transacional), DACL/diretório privado, cap 4 MiB
no principal, orçamento agregado/reserva, máximo 32 fontes persistidas, 128 receipts
e 10 mil eventos. Recusa WAL/SHM, links, outros formatos e Git. Retenção v2:
payload 1h/receipt 24h, markers permanentes limitados e high-water preservados;
contrato completo em INBOX_RETENTION.md. Expiração de sessão não implica purge. SQLite ativo fica **em claro**.
Mesmo orçamento lógico não é quota física, proteção contra admin ou auditoria.

source_events retorna listas separadas ordenadas por source_sequence. Não impõe
ordem global por relógio ou ordem de chegada; gaps, relógios não sincronizados e
proveniência declarada são explícitos. Contagens não permitem inferir causalidade.
Testes Python cobrem replay/duplicatas/conflitos, origem/aba negadas, gates,
retomada/TTL, rollback sem ACK, novo dono/reabertura. Job Chromium dedicado usa
CDP Target.closeTarget na própria extensão descartável: exige close real,
novo worker/timeOrigin e captura encerrada, pending batch preservado, retry e ACK
local funcionando. Não é substituído por alteração de variáveis; se bloqueado,
registrar lacuna/falha sem contornar política. Chrome/Edge Windows humanos continuam
pendentes; Chromium CI não os representa. Política unpacked local permanece intacta.
