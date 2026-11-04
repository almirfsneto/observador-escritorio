# Issue 22 — AI-01 e AI-02

Base exata PR21/8abbb5b0635f2505c30d4cf055d563f0a1811d59.
Filha codex/legacy-binding-cleanup; PR6 e relatórios históricos não são alterados.
A auditoria IA da Issue22 corrobora tecnicamente A1–A4 da Issue20, mas não é
assinatura humana nem aprovação de coleta, adapter, piloto ou implantação.

## AI-01 — capacidade retida em vez de PID

creation_ticks exige Popen vivo e retido. OwnedProcessIdentity duplica o handle
com QUERY_LIMITED_INFORMATION/SYNCHRONIZE e herança falsa, confere PID/criação
entre origem e duplicata e recusa processo sinalizado. Não usa OpenProcess nem
aceita PID isolado. O deslocamento FILETIME→DateTime do protocolo C# é preservado.
CloseHandle tem BOOL verificado por close_handle_once. Falha mantém dono/handle
em failed sem retry e impede iniciar provider; o erro contém referência interna
de recurso para retenção pelo caller, nunca serializada. Isso não autentica o
emissor C#, não prova reuso real de PID nem protege contra código malicioso local.

## AI-02 — continuidade de cleanup por recurso

CleanupStatus tenta cada recurso de forma independente, registra somente enums
fixos e contagens limitadas (snapshot owned_cleanup), sem mensagens/objetos de
exceção. Captura Exception, não interrupções BaseException. Término/wait/kill
usam somente objetos próprios retidos, sem lookup de PID. Timeouts de graça podem
escalar para kill; confirmação exige processo encerrado. Erros inesperados ficam
registrados mesmo se um fallback funcionar. Repetir cleanup completo não repete
fechamentos de propriedade incerta.

Controlador tenta sessão/provider, sink e fixture independentemente. Aceite tenta
ainda segunda fixture, sampler e observações; erro em um não impede os seguintes.
children_stopped só recebe true depois de todos os recursos confirmados. Schema
v1/CMD são preservados; snapshots de cleanup são diagnóstico separado em memória,
não novos campos no JSON v1. A UI indica limpeza não confirmada quando aplicável.

NativeSession tenta stop, espera limitada, kill se preciso, ambos os joins e pipes.
Não fecha TextIOWrapper enquanto a thread ainda está viva: poderia bloquear sob
lock de IO. Nesse caso conserva o recurso e registra cleanup_unconfirmed. Erro
na partida de threads tenta teardown e retorna erro estático com dono retido.
Nenhum ACK de pausa/autenticação é inferido da confirmação de cleanup.

## Verificação e revisão

Oito testes portáveis novos: troca inicial/close injetados sem provider, PID
isolado negado, falhas de sessão/sink/fixture/secondary/sampler/IO/thread, startup
parcial e controle positivo. Não são falhas espontâneas nem reuso real de PID.
Três testes Windows: binding de mesmo objeto/criação/herança, CloseHandle protegido
recusado realmente sem provider, e filhos/IO/métricas reais com falha de sink
INJETADA (caso híbrido). Consultar PROGRESS/PR para execuções e skips concretos.

AI-03 continua separado: nenhum lançamento existente foi convertido a suspenso
ou declarado contido antes do assign. AI-04 e assinatura humana seguem abertos.
Para nova revisão técnica IA nesta conversa: fixar SHA, comparar contra PR21,
verificar os testes de callers e conferir as duas versões Windows e Chromium.

## Estado efetivo desta execução

Código a332be4: oito casos novos portáveis passaram em Linux. Os três testes
Windows novos estão SOMENTE PREPARADOS; nenhum executou nesta tarefa. CI
41900708978 e41900750727 falharam antes de iniciar etapas; attempt2 repetiu
a falha. Não usar nomes REAL dos testes como evidência de execução. Revisor deve
aguardar CI Windows restaurada. Não existe aprovação de segurança por esta nota.
