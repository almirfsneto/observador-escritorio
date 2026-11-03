# Revisao tecnica dos PRs 1 e 2 — 2026-11-03

Escopo: leitura dos seis documentos obrigatorios, codigo, testes e workflows dos
heads `15e1e6d` e `598e8e6`. Revisao do desenvolvedor nesta execucao; nao equivale a
revisao independente nem aprova merge. Correcoes estao empilhadas no PR seguinte,
sem reescrever branches em revisao nem integrar os PRs.

| Achado | Correcao nesta entrega | Evidencia / limite |
| --- | --- | --- |
| PR1: PowerShell por consulta perde acoes entre polls; foco por papel mistura botoes diferentes. | Novo processo .NET persistente assina foco, Invoke e Toggle; RuntimeId salgado por sessao diferencia controles. | Testes de 20 ms e repeticao sem deduplicacao de acoes; ensaio UIA automatizado acrescentado no Windows. Nao observa teclas nem valores. |
| PR2: caminho de executavel nao limita a instancia lancada. | Caminho + PID + criacao FILETIME/DateTime ticks; handle nativo mantido durante a sessao; handshake validado pelo controlador. | Teste nativo rejeita criacao diferente; instancia fechada para ensaio. Nao e assinatura/autenticacao contra administrador local malicioso. |
| PR2: pausa/retomada e thread compartilhada podiam liberar evento antigo ou exibir fila apos pausa. | Novo LabStream usa lock e geracoes; pausa limpa fila; mensagens em voo de geracoes anteriores sao descartadas. | Teste de pausa e retomada com mensagem atrasada. Collector legado nao e mais usado pelo controlador; permanece prototipo de consulta unica. |
| PR2: widget Text crescia sem limite; fila descartava dados sem contador; mensagens de stop podiam bloquear. | Timeline limitada a 200 linhas, filas nativa/Python com 512/256 itens, comandos coalescidos sem bloquear Tk; contadores de descarte e lacunas. | Testes de rajada e ciclo de vida; nenhuma mensagem nativa de erro crua exibida. |
| PR2: fechar controlador deixava fixture aberto e provider em consulta ate timeout. | Encerramento dos processos filhos possuidos, EOF encerra provider, heartbeat e watchdog monotono independente. | Testes Windows de EOF, expiracao e threads encerradas. API UIA pode travar: processo tem fallback de kill. |
| PR1: validacao permitia metadata com conteudo arbitrario, NaN e caminho de screenshot enraizado por barra invertida. | Dominios fechados nos valores de metadata, tipos numericos estritos e caminhos relativos sem barras invertidas/componentes vazios. | Regressao com payload aninhado, NaN e caminhos Windows/UNC. Strings gerais do contrato nao sao detector automatico de PII. |
| PR2: documento manual com fences escapados; evidencia CI ainda sem registro final. | Fences corrigidos e novo roteiro executavel em LAB_PERSISTENTE.md; evidencias desta entrega registradas em PROGRESS. | O roteiro antigo representa o estado historico; comandos atuais compilam dois projetos. |

Seguranca preservada: somente aplicativo ficticio, inicio explicito apos janela
visivel, periodo maximo de 15 minutos, nenhuma instalacao/autoarranque, screenshot,
texto de campo, senha, clipboard, rede ou upload de dados. O modo --protocol-test
produz eventos ficticios de memoria e nao registra UIA; seus resultados nao sao
apresentados como captura real.

Riscos pendentes: validacao humana em Windows 10/11, overhead/perda sob carga e
comportamento de provedores UIA; APIs nao garantem entrega de todos eventos. Foco
e Invoke nao demonstram conclusao de tarefa de negocio. Ainda nao ha fila em disco,
criptografia/ACL, screenshots ou gates de piloto completos. Nao autoriza uso com
pessoas nem recomenda integrar os PRs automaticamente.
