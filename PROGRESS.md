# Registro de progresso

## Versao de reconstrução de pacote - 2026-11-03

**Concluido neste pacote:** estrutura de projeto, especificacao, instrucao para Codex, CLI, SQLite, eventos ficticios, algoritmo basico de padroes e testes locais.

**Nao implementado:** capturador real de Windows, extensao Chrome/Edge, servidor central, capturas de tela, instalador, criptografia de dados em repouso e painel de administracao. Nao considerar apto ao uso no escritorio.

**Proxima tarefa Codex:** auditar candidatos de codigo aberto; implementar captura Windows com mocks e testes; depois validacao interativa em computador de teste. Registrar cada entrega aqui.

## Entrega 1 — fundacao de laboratorio — 2026-11-03

**Feito:** leitura integral dos documentos obrigatorios; baseline de 8 testes e
CLI validado (36 eventos, 15 candidatos, 36 linhas exportadas). Matriz documental
de OpenAdapt, SmartRPA e candidato Deskmate com referencias fixadas, licencas,
datas e limites. Nenhum codigo externo adotado. Nova politica de coleta fechada,
allowlist por caminho absoluto, aliases, pausa, expediente com fuso e expiracao
irreversivel na sessao; rechecagem depois do backend. Ponte experimental
Win32/UIA sem nomes/titulos/valores. Formulario WinForms ficticio e workflow
Linux/Windows criados; workflow anunciado no scaffold estava ausente.

**Verificacao local:** Linux, Python 3.12: 19 testes aprovados, incluindo CLI por
subprocesso e idempotencia, politica/mocks, erros sem dados de excecao, round-trip
SQLite e contrato da ponte. Wheel construido e presenca do script PowerShell no
pacote confirmada. `git diff --check` aprovado. Execucao remota de CI sera
registrada abaixo quando houver evidencia; Windows interativo nao testado.

**Limites:** apenas eventos de foco, sem cliques/atalhos/erros semanticos reais;
sem tray/loop visivel/autoarranque, screenshot, instalador, retencao/cota,
criptografia, extensao ou centralizacao. Consulta PowerShell por polling e lenta;
deduplicacao por papel nao distingue controles iguais. O formulario ficticio
compartilha executavel PowerShell: nao permitir esse executavel genericamente.
Revisao independente do scaffold, auditoria completa dos motores e confirmacao
da identidade do DeskMate citado permanecem pendentes. Nenhuma maquina real,
base de cliente ou sistema excluido foi acessado. Nao apto a piloto.

**Proximo passo:** seguir `docs/WINDOWS_LAB.md`: executavel sintetico dedicado e
runner visivel inicialmente pausado; depois fila limitada/retencao e ensaio UIA
em Windows. Retomar com leitura de AGENTS/SPEC/SECURITY/ROADMAP/DECISIONS/PROGRESS,
rodar testes e conferir o PR/CI desta entrega. Nao ha trabalho continuo apos o
encerramento desta execucao.

**Entrega e evidencia remota:** implementacao no commit
`f48b31e3bff4506840357969186a9faad4d0ba24`, branch
`codex/windows-lab-foundation`, [PR #1 em rascunho](https://github.com/almirfsneto/observador-escritorio/pull/1).
[CI do commit de implementacao](https://github.com/almirfsneto/observador-escritorio/actions/runs/41699535298):
os quatro jobs Ubuntu/Windows x Python 3.11/3.12 concluiram com sucesso, incluindo
os 19 testes por job e parsing PowerShell nos jobs Windows. Sao testes de nucleo,
mocks e sintaxe; nao houve ensaio de captura UIA em desktop Windows interativo.
Commit posterior desta entrega registra apenas documentacao/evidencias e manifesto.

## Entrega 2 — laboratorio de interface visivel — 2026-11-03

**Implementado na branch `codex/visible-windows-laboratory`:** projeto WinForms .NET 8 com executavel de teste dedicado; janela Tkinter visivel e inicialmente desativada; fluxo manual abrir/iniciar/pausar/retomar/encerrar; apenas aplicacao ficticia na allowlist; expiracao de quinze minutos; contagem de foco na memoria, sem dados reais, arquivo, rede nem screenshot; CI passa a compilar o fixture nos jobs Windows; testes sinteticos de validacao da allowlist e validade temporal.

**Verificacao ainda necessaria:** executar novos jobs CI e registrar resultado; exercitar interface, foco e campo de senha em Windows interativo; medir latencia do PowerShell e cobertura de controles. Nao alegar testes interativos ou instalacao. A API de UIA segue experimental.

**Proximo passo:** acompanhar CI do PR e, em computador de teste, executar o roteiro `docs/LAB_ENTREGA_2.md`; manter proibida captura da equipe ate gates do piloto.

## Entrega 3 — revisao e captura persistente — 2026-11-03

**Revisado:** PR1 em 15e1e6d e PR2 em 598e8e6, documentos obrigatorios e codigo/testes.
Achados e correcoes em docs/REVIEW_PRS_1_2.md. Mudancas empilhadas sobre PR2, sem
merge, deploy ou alteracao de maquinas reais. Revisao independente ainda pendente.

**Implementado:** provider .NET UIA persistente, vinculo PID/caminho/criacao,
assinaturas foco/Invoke/Toggle, IDs efemeros de controles, pausa por geracoes,
filas e timeline limitadas, perdas visiveis, heartbeat/EOF/watchdog monotono e
limpeza dos filhos. Endurecimento de metadata e caminhos; roteiro manual corrigido.

**Validacao local:** 40 testes descobertos, 35 executados com sucesso no Linux e
5 testes Windows explicitamente skipped. Compilacao cruzada dos dois projetos
.NET 8 aprovada, zero warnings/erros. Acrescentados testes nativos de protocolo e
ensaio automatizado UIA de fixture para CI Windows. Resultados remotos pendentes.

**Proximo passo nesta execucao:** publicar PR empilhado e conferir CI, corrigir
falhas e registrar se o runner permite ensaio sintetico UIA; depois avancar fila
SQLite limitada/retencao sem habilitar coleta real. Teste humano Windows permanece
pendente; nenhuma alegacao de validacao manual ou de aptidao para piloto.

### Evidencia da entrega 3 e correcoes do laboratorio

[CI 41711041111](https://github.com/almirfsneto/observador-escritorio/actions/runs/41711041111),
commit `c4ca6cf8f81b8d6921e0a910829786d646fc4d26`: quatro jobs Ubuntu/Windows x
Python 3.11/3.12 aprovados. Windows executou os 42 testes, sem skips; ensaio UIA
real automatizado sobre fixture WPF recebeu 30 Invoke / dois controles / 60 eventos
(foco+acao), zero descartes nativos/Python, em ambos os Pythons. Campo de senha
excluido. Linux: 37 executados e cinco Windows skipped.

Falhas iniciais levaram a correcoes de pipes Windows no encerramento, leitura/
escrita/watchdog em threads dedicadas, cache minimo de eventos UIA, consulta de
foco permitida fora do callback e prontidao de janela. O WinForms foi mantido para
registrar limitacao de Invoke; WPF usa controles padrao. Timeouts de CI foram
limitados a 10 minutos. Nenhum dado real foi usado. Commit posterior melhora
probe de foreground, teardown e exige exatamente 30 acoes sem perda/duplicacao.

**Gate humano ainda aberto:** executar controlador visivel em Windows 10 e 11
com fixture, verificar pausa/fim/expiracao, acesso local e overhead. O ensaio
acima e automacao de desktop no runner, nao aceite manual de uma pessoa. Nao
instalar, coletar de pessoas, fazer deploy ou integrar PRs sem autorizacao.

## Entrega 4 — fila local limitada de laboratorio — 2026-11-03

**Implementado:** persistencia opt-in inicialmente desmarcada; SQLite em lab-data
ignorado pelo Git, limite 4 MiB no banco principal, 10 mil eventos e TTL 1h;
projecao restrita a eventos ficticios, expurgo/secure_delete, escritor dedicado,
buffer limitado e contagem de perdas/expurgos. Erro de armazenamento pausa o
ensaio. Sem rede, dados reais, instalacao, deploy ou merge.

**Validacao local:** 55 testes descobertos, 49 executados com sucesso no Linux,
6 especificos de Windows skipped. Testados quota cheia, integrity_check apos
rollback, lock externo/recuperacao, retencao/reinicio, idempotencia, buffer e
encerramento. Teste Windows agora integra UIA → projecao → SQLite → mineracao de
sequencias; resultado remoto ainda a conferir. Docs em LAB_QUEUE.md.

**Limites:** cota do banco nao cobre journal/filesystem; sem cifragem/ACL revisada;
expurgo nao roda com app fechado e nao garante apagamento forense. Captura UIA
nao garante entrega/ordem de todos eventos; horarios sao do callback. Nao apto a
piloto. PR4 sera empilhado sobre PR3 e permanecera em rascunho.

**Atualizacao final da entrega 3:** CI do head `59dc69aba64645c94ab25416ab80be7e9d30acf8` aprovada em Ubuntu/Windows e Python 3.11/3.12: [run 41712520509](https://github.com/almirfsneto/observador-escritorio/actions/runs/41712520509). Inclui 44 testes, confirmacao de pausa por ACK, timeout de comando e expiracao nativa testada sem fallback Python. PRs 1/2 revisados com correcoes no [PR3](https://github.com/almirfsneto/observador-escritorio/pull/3); fila no [PR4](https://github.com/almirfsneto/observador-escritorio/pull/4), todos em rascunho e sem merge.

### Evidencia final da entrega 4 e estado para retomada

[CI 41713966909](https://github.com/almirfsneto/observador-escritorio/actions/runs/41713966909),
commit `0142e9b2bf2c5cd824d2e1531d9bfe59d2b1d679`: quatro jobs aprovados
Ubuntu/Windows x Python 3.11/3.12. Windows executou 55 testes sem skips; Linux
executou 49 e pulou seis dependentes de Windows. O ensaio UIA WPF capturou
exatamente 30 Invoke em dois controles / 60 eventos, zero descartes de fila e
senha excluida. A projecao percorreu SQLite e detector de sequencias.

O controlador Tk visivel foi exercitado automaticamente: desativado por padrao,
inicio explicito, ACK de pausa, contador estavel durante interacoes pausadas,
retomada, buffer de texto limitado e encerramento dos filhos/escritor. Gravou
58 eventos em Python 3.11 e 60 em 3.12, zero descartes de fila; ambas as execucoes
confirmaram banco igual ao total gravado e filhos encerrados. Foco pode ser
coalescido pelo provedor: zero descarte de fila nao prova entrega de todo foco.
O teste final aguarda 30 Invoke visiveis e duraveis antes de pausar, e exige
exatamente essas 30 acoes em SQLite. Pausar antes da drenagem descartava pendencias
intencionalmente, conforme a politica de pausa; nao se deve confundir isso com
overflow nem usar contagem mista de foco+acao como sinal de conclusao da rajada.

Resolucao de dependencias preservou testes de desktop e manifestos; a falha do
harness que bloqueava o loop Tk durante ativacao de foreground foi corrigida.
Uma execucao antiga presa em cancelamento terminou cancelada; novas execucoes
ficaram limitadas a dez minutos. Fonte e wheel verificados localmente; nenhum
observador rodou em computadores reais da equipe. Nao ha trabalho continuo apos
esta execucao, nem merge/deploy/instalacao autorizados.

**Proxima tarefa que depende de intervencao humana:** executar
`docs/VALIDACAO_MANUAL_WINDOWS.md` em ambiente Windows 10 e 11 dedicado, registrar
somente versoes/hashes/contagens e verificar responsividade, isolamento de segunda
instancia, pausa, fim e custo. CI usa desktop sintetico automatizado e nao e esse
aceite. Depois do relatorio, revisar cobertura por aplicativo, cifragem/ACL,
cota total de disco e gates de piloto. Manter PRs 1/2/3/4 em rascunho ate revisao.

**Ajustes finais de ensaio:** preparacao de foreground usa Win32 apenas no PID
ficticio, mantendo o loop Tk ativo, para evitar bootstrap PowerShell no probe.
Expiracao nativa e testada com stdin aberto e sem NativeSession: exige termino
em ate 10s para prazo de 6s, por saida normal ou encerramento proprio do watchdog
(codigo Windows 4294967295). O fallback e intencional para teardown preso, nao um
comando Python de parada. Aceite humano continua pendente.

**Correcao de encerramento:** o fallback nativo de um segundo agora e armado antes do teardown COM, tambem em EOF/stop/erro e na saida de Main. Isso cobre o caso observado em que o runtime mantinha o processo vivo depois do fim logico. Os testes independentes de EOF e prazo aceitam apenas saida normal ou codigo do watchdog proprio, dentro do timeout; nenhum fallback Python satisfaz esses testes.

### Confirmacao final apos correcoes de EOF e foreground

- Provider: head `8c76fb9acce15fc25bf9b9ffe4c6ea134b9f8a6b`,
  [CI 41718058154](https://github.com/almirfsneto/observador-escritorio/actions/runs/41718058154),
  quatro combinacoes Ubuntu/Windows x Python 3.11/3.12 aprovadas.
- Integracao: head de codigo `9aaf67979d286220864a490ebfc3b87bee131326`,
  [CI 41718674684](https://github.com/almirfsneto/observador-escritorio/actions/runs/41718674684),
  quatro jobs aprovados; Windows executou 55 testes sem skips e Linux 49 com seis
  skips Windows. UIA WPF: 30/30 Invoke, dois controles, 60 eventos e zero descartes
  de fila. O controlador confirmou exatamente 30 Invoke atraves de UI/SQLite,
  pausa sem crescimento, retomada e encerramento dos filhos/escritor. Pipeline
  SQLite/mineracao aprovado. EOF e expiracao independentes tiveram saida nativa
  normal nesta rodada; o fallback proprio permanece testavel e limitado.
- Ultima alteracao somente documental registra esta evidencia. Fonte, manifesto,
  CLI e wheel verificaveis; working tree limpo ao encerrar. PRs 1/2 revisados com
  correcoes no PR3; PR4 empilhado sobre PR3. Nenhum PR integrado.

**Estado de parada:** desenvolvimento desta etapa concluido e recuperavel. O
proximo gate e o roteiro humano VALIDACAO_MANUAL_WINDOWS.md, em Windows 10 e 11
exclusivos de teste. Nao considerar validado em computadores da equipe ou apto
a producao. Nenhuma automacao permanecera trabalhando depois deste atendimento.

## Entrega Issue 5 — aceite guiado Windows — 2026-11-03

**Base:** PR4 em b06b624; PRs 1–4 preservados em rascunho, sem merge. Documentos
obrigatórios e roteiro de laboratório lidos integralmente. Baseline: 55 testes,
49 executados no Linux e seis Windows skipped.

**Implementado:** lançador CMD/Python com interface portuguesa; preparação local
sem instalação/elevação/bypass, fontes NuGet vazias e SDK 8 fixado; checagem de
Python/Tk/SDK, build e hashes SHA-256 dos dois exes e suas DLLs/configs; testes
automáticos explícitos; laboratório opt-in desativado, segunda instância fictícia,
pausa/stop/expiração preservados. Métricas Win32 só por handles de processos
próprios, CPU/RAM amostradas e tempos de início/pausa até ACK. Itens realmente
manuais não são aprovados por software. Schema fechado rejeita notas livres,
campos extras/PII, NaN e sucesso sem evidência. JSON exclusivo fora de Git, sem
upload; human_gate pendente e pilot_authorized falso por construção.

**Verificação local até aqui:** 71 testes descobertos, 63 executados no Linux e
oito Windows skipped. Incluem sanitização/schema/exportação, pré-requisitos,
restauração offline/hashes, saída limitada e métricas com relógio/probes sintéticos.
Acrescentados ensaios Windows de preparo offline real e wizard+fixture/provider+
métricas+relatório, para CI. Aguardando evidência remota; nenhum aceite humano.

**Limites:** sem tráfego de sistema auditado, sem garantia de pico contínuo de
CPU; pico OS RAM pode preceder janela amostrada. Commit/edição/métricas faltantes
são lacunas, não êxito. Hashes não autenticam código adulterado por administrador
local; é necessário checkout confiável. ACL/cota total/cifragem permanecem fora
esta Issue, não habilitados silenciosamente. Não houve dados reais, instalação
em colaboradores, deploy ou merge. Próximo passo: CI desta entrega e, depois,
operador dedicado executar o roteiro em Windows 10 e Windows 11.

### Revisão e correções da entrega guiada

- [PR #6](https://github.com/almirfsneto/observador-escritorio/pull/6), em rascunho,
  base `codex/bounded-laboratory-queue` do PR #4; PRs #1–#4 continuam rascunhos,
  não integrados. Nenhuma branch anterior foi alterada.
- Primeira CI identificou corrida na leitura do contador de ACK de pausa pelo
  teste: aguardar apenas o stream não aguardava a instrumentação do loop Tk.
  Corrigida a sincronização; não foi mascarada com aprovação/skips artificiais.
- Nova execução automática invalida sucesso anterior; timeout não preserva
  PASSOU e encerra apenas o comando próprio, permitindo tentativa posterior.
  Encerramento do assistente cancela permanentemente o runner.
- Motivos de fim são classificados antes de o controlador parar o stream:
  fixture fechada, backend com erro, expiração por relógio UTC ou monotônico,
  parada pelo operador e fechamento de janela não são confundidos.
- Teste do lançador a partir de outra pasta, inclusive com espaços; Python antigo
  para antes de preparar/abrir o laboratório. Cleanup do teste sai do diretório
  temporário antes de removê-lo, exigência específica observada no Windows.
- Schema publicado comparado ao contrato executável, inteiros excessivos/NaN
  rejeitados e wheel construído sem dependências. Linux: 76 descobertos,
  68 executados e oito Windows skipped. Evidência final da matriz abaixo.

### Evidência final automatizada da Issue 5

Código validado: `20a90db7aa5a48aa55d74db92994d210be09cdc3`.
[CI 41726436758](https://github.com/almirfsneto/observador-escritorio/actions/runs/41726436758):
quatro jobs aprovados, Python 3.11/3.12 em Ubuntu e Windows.

| Ambiente | Resultado |
| --- | --- |
| Ubuntu / Python 3.11 e 3.12 | 76 descobertos, 68 executados, oito testes Windows skipped |
| Windows CI / Python 3.11 e 3.12 | 76 executados, todos aprovados, nenhum skipped |
| Preparação Windows real | SDK 8 selecionado, restore com fontes vazias, build e hashes aprovados |
| Assistente Windows automatizado | Tk/Toplevel, fixture WPF, provider, segunda instância, métricas dos quatro papéis, ACK de pausa, encerramento e JSON fechado aprovados |
| Integração UIA anterior preservada | 30/30 Invoke em dois controles, 60 eventos, zero descartes nativos/Python |
| Controlador/fila anterior preservados | 60 eventos na timeline e gravados, zero descartes, filhos encerrados |
| EOF/expiração nativa | término normal (código 0) em ambas as versões Python |
| Artefatos locais | wheel sem dependências e compileall aprovados; manifesto atualizado |

O runner foi **Windows Server 2025, build 26100**, imagem
`windows-2025-vs2026`; isto é automação de desktop sintético no CI, **não** um
ensaio humano em Windows 10/11. Relatório de teste permaneceu com
`origin=automated_test`, `human_gate=PENDENTE_REVISAO_HUMANA` e piloto falso.
Nenhum relatório bruto/dado de captura foi anexado ou versionado.

**Próxima tarefa e bloqueio humano:** TI/operador executar os quatro passos de
`docs/VALIDACAO_MANUAL_WINDOWS.md` separadamente em Windows 10 e 11 dedicados,
com Python/Tk e SDK 8 previamente disponíveis. Marcar apenas verificações feitas,
aguardar também a expiração de 15 minutos, encerrar e salvar o JSON sanitizado
fora de Git. Revisão humana desses relatórios continua obrigatória; sem piloto,
dados reais, instalação na equipe, deploy ou integração dos PRs. As limitações
de amostragem, UIA, rede não auditada e ACL/cifragem/cota total permanecem.

## Execução intensiva — armazenamento — 2026-11-03

Base obrigatória PR6, head 3d4a770; baseline Linux reproduzido: 76 descobertos,
68 executados, oito Windows skipped. Branch nova codex/storage-reliability.
Implementados orçamento agregado/reserva para journal, free-space headroom,
cache sem spill, batch direto limitado, quick_check, DACL Windows e proteção de
links, contagem explícita de submissão após shutdown e corrupção preservada.
Protótipo DPAPI de arquivo sintético exportado, não de SQLite cifrado. Testes
novos cobrem auxiliares, disco indisponível, read-only, corrupção, queda com
rollback e permissões/DPAPI nativos no Windows. Evidência remota pendente.
Detalhes e limites: docs/STORAGE_HARDENING.md. Validador e schema de aceite v1
preservados; nenhum dado real, instalação na equipe, deploy ou merge.

## Execução intensiva — cobertura Windows experimental

Nova branch codex/windows-coverage-probe sobre codex/storage-reliability. Provider
padrão inalterado; probe WinEvent opcional restrito ao PID de fixture, botões
nativos e 20s. STATECHANGE não vira ação inferida. Comparação automatizada WPF e
WinForms, contagens UIA/WinEvent, custo próprio e atraso de callback, pause ACK.
Linux: 84 descobertos, 74 executados, dez Windows skipped. Compilação e desktop
Windows dependem da CI em acompanhamento; não equivalem ao aceite humano.

### Evidência do endurecimento do armazenamento

PR #7: CI 41741273177 no código 7bd09ff, quatro jobs aprovados Linux/Windows
Python 3.11/3.12. Windows: 83 descobertos/82 executados, um symlink ignorado;
Linux: 74 executados/nove Windows ignorados. DACL verificada por trustees numéricos
(não aliases SDDL), DPAPI real roundtrip/tamper, recuperação de rollback, filas e
validador anterior aprovados. Revisão adicional passa a tentar symlink Windows
em vez de presumir falta de privilégio e recusa WAL/SHM legado sem checkpoint ou
remoção. Testes dessa revisão serão confirmados na CI subsequente. O SQLite ativo
continua em claro; não há quota física de volume nem aceite humano.
