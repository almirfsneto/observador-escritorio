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

## Execução intensiva — extensão web sintética

Branch codex/synthetic-browser-extension sobre a entrega de cobertura Windows.
MV3 opt-in, loopback/origem/caminho exatos, sem permissões amplas, valores ou URLs
exportados. Popup de início/pausa/fim, prazo/limites, worker serial e exportação
local; importador Event v1 fechado. Site fictício com formulário/senha/menu/tabs/
tabela/navegação e teste real Playwright. Política Chromium deste executor impede
unpacked; não foi contornada nem reportada como teste aprovado. Job CI real
Chromium separado adicionado; resultado remoto ainda pendente. Testes unitários
não substituem carregamento real nem aceite Chrome/Edge Windows.

## Execução intensiva — descoberta de microtarefas

Branch codex/task-discovery sobre extensão experimental. Motor paralelo ao legado,
com segmentação/gaps, normalização sem IDs/alvos, variantes, contagem sem overlap,
confiança heurística e cenários explícitos de economia. Corpus administrativo
fictício: 36 eventos/oito rotinas/três variantes, família principal com oito
ocorrências; legado no mesmo corpus não ligava IDs entre sessões. Relatório fora
Git sem dados individuais. Comparadas licenças/capacidades PrefixSpan/PM4Py, sem
adotar dependências. Linux: 91 descobertos, 80 executados, 11 testes específicos
ignorados; testes de mineração aprovados. Evidência CI desta branch pendente.

### Evidência do endurecimento do armazenamento

PR #7: CI 41741273177 no código 7bd09ff, quatro jobs aprovados Linux/Windows
Python 3.11/3.12. Windows: 83 descobertos/82 executados, um symlink ignorado;
Linux: 74 executados/nove Windows ignorados. DACL verificada por trustees numéricos
(não aliases SDDL), DPAPI real roundtrip/tamper, recuperação de rollback, filas e
validador anterior aprovados. Revisão adicional passa a tentar symlink Windows
em vez de presumir falta de privilégio e recusa WAL/SHM legado sem checkpoint ou
remoção. Testes dessa revisão serão confirmados na CI subsequente. O SQLite ativo
continua em claro; não há quota física de volume nem aceite humano.

### Evidência da comparação Windows

PR #8, código b9361c3: CI 41741819622, quatro jobs aprovados. Windows 84
descobertos/83 executados, um symlink ignorado; Linux 74/dez ignorados. WPF:
30/30 Invoke em dois controles, sem descartes. WinForms: zero Invoke nesse
estímulo; probe WinEvent restrito aceitou zero notificações em ambos os caminhos.
Os filtros conservadores excluíram objetos não suportados (43 WPF/30 WinForms).
Isso NÃO demonstra cobertura melhor de cliques WinForms. Diagnóstico verificável
fundamenta adapter complementar, em vez de inferir ações. Probe durou ~2,2s,
consumiu ~109–141ms de CPU e ~29 MiB de working set pico em rodadas CI; valores
amostrais do processo próprio, não SLA. Latência reportada zero quando não houve
callback aceito é ausência de amostra, não atraso zero garantido.

### Evidência de extensão MV3 real

PR #9, código 5dcf7d5: CI 41742054304, cinco jobs aprovados (matriz núcleo
Linux/Windows 3.11/3.12 + Chromium real). Núcleo: 87 descobertos; Linux 76
executados/11 ignorados; Windows 85 executados/dois ignorados (symlink presumido
naquela revisão e browser separado). Job web executou um teste real aprovado,
Chromium 151.0.7922.34: 27 eventos sanitizados, carregamento MV3/popup/guardas,
valores/senha/URL excluídos, pausa/retomada/navegação, limite/rate e expiração
injetada, download local validado pelo importador Python. Não foi aceite humano
Chrome/Edge Windows nem observação de ambiente profissional. Política local do
executor permaneceu intacta. Correção posterior na base tenta symlink real.

## Fechamento verificável da execução intensiva — 2026-11-03

Quatro entregas em rascunho, empilhadas sobre PR6, sem merge em main:

| PR / branch | Código e CI confirmados | Resultado |
| --- | --- | --- |
| #7 / codex/storage-reliability | fa04785 / [41742876982](https://github.com/almirfsneto/observador-escritorio/actions/runs/41742876982) | 4 jobs; Windows 84 executados/0 skips; Linux 75/9 skips |
| #8 / codex/windows-coverage-probe | 805c791 / [41743703126](https://github.com/almirfsneto/observador-escritorio/actions/runs/41743703126) | 4 jobs; Windows 3.11 85/0 skips, 3.12 84/1 skip de foreground; Linux 75/10 skips |
| #9 / codex/synthetic-browser-extension | fdec952 / [41744118720](https://github.com/almirfsneto/observador-escritorio/actions/runs/41744118720) | 5 jobs; Windows 87 executados/1 skip browser separado; Linux 77/11 skips; Chromium real 1/0 skips |
| #10 / codex/task-discovery | 671230b / [41744120777](https://github.com/almirfsneto/observador-escritorio/actions/runs/41744120777) | 5 jobs; Windows 92 executados/1 skip browser separado; Linux 82/11 skips; Chromium real 1/0 skips |

Cada matriz usa Python 3.11/3.12; o browser dedicado usa Python 3.12. **Skips
são lacunas**, não aprovações. O skip específico de foreground do PR8 não ocorreu
nos dois jobs Windows da integração final PR10. Jobs Windows executaram DACL,
DPAPI, links, recuperação, UIA, comparação WPF/WinForms, assistente e escritor.
.NET alvo 8 compilado; preparação real selecionou SDK8/build offline das três
fixtures/provider necessários aos testes. Chromium 151.0.7922.34 carregou MV3 e
validou interações, download/importação sanitizados e contagens/rate, pausa,
expiração e timeOrigin divergente injetados. Reinício REAL de worker e 15 minutos
humanos continuam pendentes; não confundir fault injection com esse aceite.

Correções de CI registradas: alias SDDL LA resolvido por trustees numéricos;
parâmetro de timestamp C# do probe corrigido; timeout intermitente do estimulador
PowerShell em um job (41743078996) agora com estágios estáticos e teto de 30s,
sem relaxar 30 Invoke/pausa/persistência e sem replay automático. O motivo interno
daquele timeout não foi provado; futuras falhas expõem apenas estágio sanitizado.
Preparação guiada inclui WinForms para checkout limpo, preservando WPF manual,
estado inicialmente desativado e JSON v1. Browser encerra conservadoramente ao
mudar timeOrigin do worker, além de relógio UTC/monotônico; não estende prazo.

Baseline: 76 testes/68 Linux executados. Integração: 93 descobertos/82 Linux e
92 Windows executados, mais um browser real em job dedicado. Não há falha aberta
nas rodadas confirmadas. Compileall, wheel sem dependências runtime novas,
manifestos de quatro branches e git diff --check conferidos. Última alteração
documental desta entrega registra evidências; CI final do head também será
conferida no PR. Nenhuma captura/relatório bruto foi versionado.

**Pronto para laboratório:** orçamento/ACL/DPAPI de arquivo, diagnóstico Windows,
extensão em perfil descartável e descoberta no corpus fictício. **Não pronto
para piloto:** SQLite ativo em claro, quota física estrita/ACL adversarial não
validadas, cobertura WinForms incompleta, integração web/Windows sem ACK global,
heurísticas sem calibração, ausência de aceite humano Windows10/11 e Chrome/Edge.
Autostart/serviço/screenshot/sincronização não foram habilitados. Não houve dados
reais, computadores da equipe, sistemas excluídos, custos, deploy ou integração.

**RETOMADA AUTÔNOMA:** docs/RETOMADA_AUTONOMA.md contém checkout, testes, evidências,
limites e próxima entrega recomendada: diagnóstico fechado de saúde e fault
injection de journal/filas, depois integração com proveniência/ACK e testes
reais de suspensão MV3. O desenvolvimento desta execução termina com entregas
revisáveis; nenhum agente/observador permanece trabalhando continuamente.

## Issue 11 — prioridade 1: diagnósticos e armazenamento — 2026-11-03

Base PR10 502d6d3, branch nova codex/closed-lab-diagnostics. Documentos obrigatórios
e retomada lidos, baseline 93 descobertos/82 Linux executados/11 específicos
ignorados. Contrato fechado de agente/filas nativas/Python/writer/orçamento,
reconciliação por estágio, replay de amostras, exportação local e snapshots sem
SQL na UI. Native health ganha gauges compatíveis com mensagens antigas.
Faults BUSY/FULL/IO pré/pós-commit/rollback, TTL/reabertura, fila/shutdown, conflito
UUID e journal vivo testados. Linux: 108 descobertos, 97 executados/11 ignorados;
CI Windows/browser pendente. Nenhum resultado representa aceite humano. Próxima
prioridade desta execução: bridge offline/proveniência/ACK, worker real e negativos
de mineração. PR6 permanece reservado ao responsável, sem alterações.

## Issue 11 — prioridade 2: bridge offline e negativos

Branch codex/offline-source-bridge sobre a entrega de diagnósticos. Inbox próprio,
fontes/slots declarados autorizados, tickets e gerações, sequence por fonte,
receipt+eventos transacionais, replay/conflicto e ACK local explícito. Sem socket,
upload, NativeMessaging ou mudança de permissões. Popup importa ticket/ACK locais
e exporta batch pendente estável; integração Windows automática não foi forçada.
Negativos de mineração corrigem merge por substituição semântica, gaps/clock e
click sem ação. Corpus rotulado: TP17/FP0/FN0/TN28 em 45 pares artificiais, sem
alegação real. Linux: 120 descobertos, 108 executados/12 ignorados. Teste CDP real
de worker stop/restart e ACK arquivo adicionado ao job Chromium; resultado remoto
pendente. Gate PR6, aceite humano e piloto continuam intocados/pendentes.

### Evidência da prioridade 1 e correção de fixture temporal

PR12, código 88b8b2d: CI 41748698571, cinco jobs aprovados. Windows 3.11/3.12:
108 descobertos, 107 executados e um browser separado ignorado; Linux 97/11
ignorados. Chromium anterior: um teste real aprovado. Native/.NET8, contadores,
pausa por falha de saúde com ACK, writer e reabertura preservados. Medição local
sintética: 16.384 bytes atuais, pico agregado observado 29.208 com journal,
reserva 4.390.920/limite 13.631.488, 9 amostras — não quota física.
Na integração PR13, dois testes de TTL com relógio congelado criavam eventos em
hora real após preparação Windows às vezes >100ms. Corrigidos para usar o mesmo
relógio injetado, mantendo tolerância da fila; cleanup usa finally. Evidência
posterior confirmará a revisão. Branch de aceite PR6 permanece em 3d4a770.

## Issue 11 — evidência integrada e limites de retomada

As duas prioridades foram implementadas em entregas separadas, sobre PR10:
- PR12 / codex/closed-lab-diagnostics / b9cb6ec:
  [CI 41752385456](https://github.com/almirfsneto/observador-escritorio/actions/runs/41752385456),
  cinco jobs aprovados; Linux 98 executados/11 específicos ignorados, Windows
  3.11/3.12 108 executados/um browser separado ignorado, Chromium um teste real.
- PR13 / codex/offline-source-bridge / código integrado 633d3ec:
  [CI 41752388247](https://github.com/almirfsneto/observador-escritorio/actions/runs/41752388247),
  cinco jobs aprovados; 121 descobertos, Linux 109 executados/12 específicos
  ignorados, Windows 3.11/3.12 119 executados/dois browsers separados ignorados.
  Chromium executou DOIS testes reais, sem skips: fluxo MV3 anterior e reinício
  real + bridge/receipt/ACK. Skips não comprovam funcionalidade; nesse conjunto,
  browser está coberto no job dedicado, não no núcleo Windows.

Prova do restart: Inspector.targetCrashed emitido por WorkerStopped do Chromium,
seguido de nova performance.timeOrigin, estado ENcerrado do produtor, mesmo lote
pendente com dois eventos, retry idêntico sem regravação e ACK consumido no popup.
Nenhuma alteração de variável substituiu essa prova. Target/Worker wrapper de
DevTools pode sobreviver ao GlobalScope: esperar targetDestroyed/close era erro
do harness, corrigido com eventos do ciclo de vida e novo contexto. CSP do popup
permanece intacta: asserção DOM substituiu espera dinâmica bloqueada, sem bypass.
Política unpacked do executor local não foi contornada. Suspensão natural por
ociosidade/sono do OS e Chrome/Edge humanos continuam sem aceite.

Falhas corrigidas na CI: fixture congelava relógio da fila e gerava evento em
hora real (Windows lento ultrapassava 100ms); agora ambos usam o relógio injetado.
Fechamento incompleto é testado com bloqueio sintético: timeout limitado, snapshot
não bloqueia e registra writer_shutdown_incomplete; depois liberação/flush e
limpeza comprovados. Rollback incerto não vira perda/commit inventado. Budget
inclui amostra de journal vivo; medição local registrada em DIAGNOSTICS.md.
.NET8, native/UIA WPF 30/30, pausa/retomada com ACK, writer, ACL/DPAPI e gate
anterior preservados; WinForms continua sem ação Invoke comprovada nesse caminho.

Negativos de mineração: 10 traces/42 eventos, 45 pares, TP17 FP0 FN0 TN28,
precisão/recall 1 **somente no corpus construído**; não é acurácia real. Click/foco
sem ação, conflitos/duplicatas, fonte negada, sequência faltante, clock regressivo
e interrupções não são colados silenciosamente a tarefas. Dataset independente,
calibração e causalidade continuam pendentes. Economia não é inferida como fato.

Branch PR6 reservada ao responsável permanece em 3d4a770; não houve mudanças nela,
merge de PR, instalação na equipe, dados reais, deploy ou transmissão de capturas.
SQLite ativo/inbox seguem em claro, orçamento não é quota física, fonte/ACK por
arquivo não são autenticados contra falsificador local e inbox não tem expurgo
por tempo. Não apto a piloto; aceite Windows10/11/Chrome/Edge/LGPD permanece.

Retomada integrada: buscar codex/offline-source-bridge e criar outra branch;
ler docs/RETOMADA_AUTONOMA.md, DIAGNOSTICS.md e OFFLINE_BRIDGE.md. Próxima ação
independente: retenção do inbox com receipts/ACK recuperáveis e testes de limites,
depois desenho de IPC autenticado e adaptador opt-in Windows, sem ligar coleta.
Último commit documental registra evidência; a CI do HEAD será conferida também.

## Issue 14 — P1 retenção segura do inbox — 2026-11-04

Base exata cf90de6/PR13, branch nova codex/inbox-retention. Documentos obrigatórios
e referências da Issue/retomada lidos. Baseline Linux 121 descobertos: 109
executados/12 skips específicos. Payload 1h, receipt 24h, markers de IDs globais e
high-water persistentes sem TTL, migração v1 atômica e erro fechado após perda da
janela de ACK. Quota preserva markers, counters agregados, fail-closed e relógio
regressivo conservador. Retenção separada de expiração de sessão e ACK histórico.
14 testes novos locais aprovados: fronteiras, replay pós-purge, conflitos,
restart, duas instâncias, lock/FULL SQLite reais, BUSY/FULL/IO injetados, retorno
pós-commit, os._exit pré/pós-commit ingest/purge + integrity_check, modelo aleatório
seed 1401/100 operações. CI Linux/Windows/Chromium a conferir no PR desta entrega.
Limites/contrato em docs/INBOX_RETENTION.md. PR6 intacto; sem coleta, rede de dados,
instalação, deploy, merge ou afirmação de piloto. Próxima prioridade: análise de
ameaças/autenticação verificável; não ligar transporte sem prova de origem.

Revisão P1: recuperação read-only de fonte conhecida funciona também quando a
reabertura detecta clock regressivo, sem permitir start; tentativa de migração
v1 com colisão global de IDs dá rollback integral e conserva versão/payloads.
15 testes novos de retenção, 136 totais (Linux124 executados/12 skips). README e
contrato offline apontam a retenção v2 para evitar descrição obsoleta sem TTL.

### P1 — evidência CI e revisão final

PR15 / código 448c3aa / [CI 41757902728](https://github.com/almirfsneto/observador-escritorio/actions/runs/41757902728):
5/5 jobs aprovados. Núcleo136 descobertos: Linux124 executados/12 skips,
Windows3.11/3.12 134 executados/2 browsers separados skipped. Chromium2 testes
reais sem skips, incluindo worker restart/receipt/ACK. WPF30/30 Invoke, controlador
60 eventos/60 escritos/0 descartados e filhos encerrados nos dois Pythons.
15 testes novos de retenção passaram em Linux e Windows. Revisão final do teste
kill passa a inspecionar SQLite ANTES do construtor fazer purge, distinguindo
pré/pós-commit de purge por linhas efetivamente recuperadas; depois reabertura
confirma receipt/markers/integridade. Código não muda nessa revisão de evidência.
Windows CI é automação sintética Server2025, não aceite Windows10/11 humano.

### P1 — correção de rollback/commit incerto na revisão adversarial

Identificado risco de ler receipt ainda não commitado se rollback da conexão
falhasse. Transação explícita agora fecha conexão em rollback falho OU exceção
no próprio retorno de commit, mesmo quando in_transaction=false. Não reutiliza
conexão incerta; snapshot counts=null/reopen_required=true/uncertain_transactions,
ACK só após reabertura. Falha posterior a commit retornado com sucesso continua
caso distinto, com receipt durável recuperável. Três regressões adicionais cobrem
rollback pré/pós falha, commit realizado seguido de retorno perdido, e EOF de
JSON truncado. 18 testes de retenção/139 totais: Linux127 executados/12 skips.
Nova CI obrigatória nesta revisão; evidência anterior não é atribuída a ela.
Medição local anterior:32 lotes/64 eventos fictícios,~30,2ms, pico agregado lógico
observado184920 bytes em132 amostras, reserva4390920/limite13631488; não quota/SLA.
