# Issue27 — evidência causal, cleanup suspenso e stop pré-worker

Base exata: PR25/d820396176f64323c578f481132856aa484b58f0.
Entrega filha: codex/suspended-cleanup-diagnostics, PR28. Nenhum PR anterior
alterado, launcher suspenso continua exclusivamente em tests/, adaptador OFF.

## Diagnóstico antes de corrigir

Pareceres23–25/Issue22 e Issue27 lidos integralmente. Os runs da base, attempt2,
confirmaram dois erros reais Windows3.11/3.12; o antigo bloqueio pré-step não
explica essas falhas. Código diagnóstico ed7c50d, CI41929775944: dois erros em
quatro testes focados de cada Windows, sem skips. Linux/Chromium passaram.
Snapshots emitidos pelos dois Windows, nos dois casos:

- job_terminate, job_zero, job_handle_close: passed; processes_confirmed=true.
- Primeira falha: process_fallback; classe Win32 access_denied.
- process_wait inicial: timeout; after_failure_wait: passed.
- thread_handle_close e process_handle_close: passed; ambos closed.

Logo, o código classificava o TerminateProcess de fallback prematuro como fatal
antes de executar a espera que confirmava saída. Não foi CloseHandle recusado,
Job sem confirmação ou leak comprovado. Job chegar a zero não implica que o
handle de processo já esteja sinalizado naquele instante.

Diagnóstico só no harness: enums/contagens/origem, sem PID, números de handle,
path pessoal, chave/frame ou texto livre de exceção. Origem win32, injected ou
win32_with_injected_wait distingue retornos reais de callbacks simulados.

## Correção com o mesmo orçamento

Após assign ter retornado sucesso e Job terminar/zerar/fechar, aguardar sinalização
antes do fallback. Filho não atribuído continua recebendo término direto. O
orçamento de espera de processo continua2s; fallback usa somente o remanescente.
Não ampliar timeout para conseguir passe. Uma falha de TerminateProcess só pode
ser recuperada para AccessDenied + processo sinalizado + Job confirmado. O erro
permanece nas fases/native_errors e exit_race_confirmed marca a classificação.
Esperas falhas/sem sinal, outros erros Win32 e quaisquer CloseHandle falhos
continuam cleanup_unconfirmed. Tentar ambos os handles independentemente e não
repetir fechamento de slot incerto. Confirmação exige também todos os closes.

Cinco testes portáveis injetam ordem de espera, erros5/6/outros, Job incerto,
wait/close falhos, limite do orçamento e sanitização. Windows acrescenta handle
próprio protegido (erro REAL de close, jamais aprovado) e TerminateProcess real
em processo já saído com primeira espera INJETADA (caso híbrido). Casos existentes
mantêm filho suspenso, atribuído, com descendente, assign/callback injetados,
crash da raiz pré/pós-assign e decoy não herdado. CI executa foco antes da suíte.

## Prioridade2 — iniciar cleanup apesar de exceções

LaboratoryWindow.stop e o pré-hook de AcceptanceLaboratory isolam stream,
controles, status e observações. Erro fica nas categorias controls/stream/
observation; finished=True já não impede a primeira tentativa de cleanup.
Falha ao construir/startar worker aciona fallback síncrono sob o mesmo guard.
Uma barreira de startup registra erro antes de publicar resultado, inclusive
quando start lança após iniciar. Lock de entrada impede duplicar cleanup entre
worker e fallback. Todos os recursos próprios seguem pela rotina independente.
Join de thread que não iniciou não escapa do finally nem transforma erro em passe.

Seis casos portáveis invocam stop/run, não só _cleanup: stream/cada controle/Tk,
observação, construtor/start, erro pós-launch, join não iniciado e positivo.
Um caso Windows usa controles Tk realmente destruídos (TclError controlado),
processos/IO/fila/amostradores próprios reais, sem registrar UIA de apps. Exigir
fim dos filhos/queue/joins e métricas, mas children_stopped=false pela falha da UI.
Skips não contam como aceitação. Snapshots v1/CMD permanecem compatíveis.

## Limites e próxima revisão

A sincronização não é watchdog global. API bloqueada sem lançar ainda pode
reter o worker não daemon; join standalone20s não é prova de deadline global.
Falha no worker fica registrada, sem retry infinito nem traceback livre. O estudo
suspenso não fecha morte pré-assign; Job na criação não foi integrado. AI04,
revisão humana e Windows10/11 interativo continuam abertos. Resultados/SHAs e
skips concretos em PROGRESS.md e checks do PR28, separados por revisão.

## Resultado integrado verificado

Código6e0cf86/CI41931710044 passou5/5. Em cada Windows: foco11/0 skips e suíte
225 descobertos/223 executados/2 skips browser. Linux184/41 por Python; Chromium
dedicado2/0. O teste de controles Tk destruídos foi executado nos dois Windows e
confirmou fechamento real de filhos/IO/fila/amostradores sem aprovar o relatório
com erro. As negativas de startup/UI/API são injetadas; o caso de TerminateProcess
real com espera inicial injetada é híbrido. Conferir CI do HEAD documental no PR.
