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
conexão incerta; snapshot counts.*=null/reopen_required=true/uncertain_transactions,
ACK só após reabertura. Falha posterior a commit retornado com sucesso continua
caso distinto, com receipt durável recuperável. Três regressões adicionais cobrem
rollback pré/pós falha, commit realizado seguido de retorno perdido, e EOF de
JSON truncado. 18 testes de retenção/139 totais: Linux127 executados/12 skips.
Nova CI obrigatória nesta revisão; evidência anterior não é atribuída a ela.
Medição local anterior:32 lotes/64 eventos fictícios,~30,2ms, pico agregado lógico
observado184920 bytes em132 amostras, reserva4390920/limite13631488; não quota/SLA.

### P1 — confirmação da revisão de segurança

PR15 / código6d521cf / [CI41759340778](https://github.com/almirfsneto/observador-escritorio/actions/runs/41759340778):
5/5 jobs aprovados. Python3.11/3.12: Linux127 executados/12 skips; Windows137
executados/2 browsers separados skipped;139 descobertos. Chromium2 reais sem
skips. Rollback falho e retorno de commit incerto executados nos quatro jobs,
com reabertura/integridade e nenhum ACK da conexão descartada. 18 novos testes
de retenção; EOF/truncamento também negativo. Manifesto/wheel/compileall/diff
verificados. Esta atualização final é documental; CI do HEAD também será conferida.

## Issue 14 — P2 análise de autenticação e simulador — 2026-11-04

Branch codex/synthetic-source-auth-model sobre P1/448c3aa. Threat model e protocolo
em docs/SOURCE_AUTHENTICATION.md: arquivos/SHA não autenticam; pareamento precisa
peer kernel bidirecional e canal privado de chave, não JSON declarado. Conforme
P2.6, entrega especificação/simulador/testes negativos, **sem IPC inseguro ou
integração controlador→inbox habilitada**. Não declarar autenticação realizada.
Modelo HMAC/challenge com default off, expiração, gerações, replay/restart,
limites e escopo explícito de ACK; 100 mutações seed1402, benchmark64 frames só
em memória (~10–14ms local, amostra variável, não SLA). Probe Windows separado
confere handle de filho próprio/caminho/criação/sessão, sem coletar; teste nativo
aguarda CI, não equivale a autenticar peer de canal. Novos testes: nove modelos
Linux aprovados, um probe Windows skipped; matriz/Chromium pendentes no novo PR.
Próxima etapa técnica: implementar/verificar canal nativo e gates adversariais
antes de qualquer adapter opt-in; nenhuma decisão humana rotineira é necessária.

### P2 — evidência verificada e limite de segurança

PR16 / código ef8ca60 / [CI 41758466029](https://github.com/almirfsneto/observador-escritorio/actions/runs/41758466029):
5/5 jobs aprovados. Núcleo146 descobertos: Linux133 executados/13 skips,
Windows3.11/3.12 144 executados/2 browsers separados skipped. Chromium2 testes
reais aprovados/sem skips. Probe de identidade do filho WPF executou nativamente
nos dois Windows: caminho/criação/sessão conferidos, falsificações rejeitadas;
transport_peer_verified=false/inbox_integrated=false, honestamente distintos.
Benchmark modelo64 frames: ~13,6/16,9ms Windows, ~10,2/17,0ms Linux; amostras de
um ensaio, não SLA. Revisão corrige rótulo da medida de bytes para medir envelope
completo (antes media batch); próximo CI registra medida correta.

P1 revisão5c914f2 integrada à filha em0c45883, sem merge de PR/main. Nova CI de
HEAD em acompanhamento. Wheel sem dependências runtime novas, compileall e
git diff --check aprovados. JSON de aceite v1 e branch PR6 permanecem intocados.

**Pendente técnico explícito:** não existe backend novo que vincule peer do
canal aos handles verificados nem entrega privada de chave comprovada. Portanto
P2 usa a alternativa segura P2.6 (spec/simulador/negativos), não integração ligada
ou autenticação real alegada. Próxima execução: canal Windows herdado do filho
próprio com herança mínima, peer/kernel, EOF/cancelamento/ACL/colisão/timeout,
antes do adapter opt-in. Não é necessário pedir escolha técnica rotineira.
SQLite claro, orçamento não físico e aceite humano/LGPD continuam bloqueando piloto.

### Issue14 — evidência integrada final e retomada

PR16 / código integrado bc23073 / [CI41759416977](https://github.com/almirfsneto/observador-escritorio/actions/runs/41759416977):
5/5 jobs aprovados após correção de rollback/commit incerto.149 descobertos:
Linux3.11/3.12 136 executados/13 skips; Windows3.11/3.12 147 executados/2 browsers
separados skipped. Chromium2 ensaios reais sem skips, worker restart/receipt/ACK.
18 regressões de retenção + nove modelos + um probe Windows somados ao baseline.
Probe confirmou filho próprio/caminho/criação/sessão, rejeitando incompatíveis,
com transport_peer_verified=false/inbox_integrated=false. Modelo64 frames mediu
~10,6/16,0ms Linux e10,8/18,1ms Windows, envelope2015 bytes; só amostras Python em
memória, não IPC/SLA. Counters/bytes não são quota física nem aceite humano.

P1/PR15 permanece separada; última sincronização de documentos/evidências não
altera runtime nem testes de bc23073. CI final dos dois HEADs será conferida nos
PRs, sem atribuir skips a êxito. PROGRESS/DECISIONS/ROADMAP/RETOMADA e manifesto
atualizados. PR6 preservado em3d4a770, PR13 emcf90de6; nenhum merge de PR, instalação,
dado real, captura oculta, deploy, host ou transmissão externa de capturas.

P2 encerra na alternativa segura P2.6, com spec/simulador/negativos e prova parcial;
canal/adapter NÃO habilitados. Retomada: codex/synthetic-source-auth-model, ler
docs/RETOMADA_AUTONOMA.md e SOURCE_AUTHENTICATION.md; implementar/verificar canal
herdado de filho próprio e gates nativos adversariais antes do opt-in. SQLite em
claro, limite lógico, autenticação e aceite Windows10/11/Chrome/Edge/LGPD continuam
pendentes; não apto a piloto. Nenhuma rotina de observação segue ativa após os testes.

## Issue17 — canal privado Windows, Etapa A isolada — 2026-11-04

Base obrigatória PR16/294cb39 conferida, nova codex/verified-owned-channel.
Documentos obrigatórios/Issue/retomada lidos. Baseline149: Linux136 executados,
13 skips. Revisão NativeSession/C#: ready.pid identifica alvo, não emissor;
stdio antigo sem MAC e comandos JSON sem framing autenticado não serão promovidos
a canal comprovado. Permanecem intocados junto ao PR6/aceite v1.

Nova fixture IPC isolada Python -I -S -B, Win32 CreatePipe/lista4 handles/parent
query limitado/Popen retido/Job, chave32 pelo pipe privado+EOF e challenge HMAC
bidirecional vinculado a identidades/código/epoch/sessão. Framing estrito16KiB,
64 mensagens, pausa/reproof, worker/timeout/cancelamento/cleanup. Sem adapter,
UIA nova, rede ou coleta. Testes iniciais: três wire portáveis aprovados; três
Windows reais aguardam CI, skips Linux não representam prova. Contrato/riscos em
docs/OWNED_CHANNEL.md. Próximas etapas independentes: adversariais/capacidade e
plano de revisão/consolidação sem merge/rebase de branches anteriores.

### Issue17 — primeira comprovação Windows e avanço independente de P2

PR18 /22f99e5 / [CI41809413254](https://github.com/almirfsneto/observador-escritorio/actions/runs/41809413254):
5/5 jobs aprovados; Windows3.11/3.12 153 executados/2 browsers skipped; Linux139
executados/16 skips;155 descobertos, Chromium2 reais sem skips. Os três testes
Windows NOVOS executaram processos/handles reais, inclusive dez modos adversariais,
chave privada/handshake, pausa/reproof/cleanup e TTL natural curto de3s. Não é
simulador de PR16, nem prova de autenticação do provider C# antigo ou aceite humano.

P2 ampliada: saturação REAL das constantes1024/10000/32 via API normal, purge e
reaberturas sem reset, passou localmente em~3,5s; clocks de retenção INJETADOS.
Testes Windows adicionais de decoy/filho externo/replay/contexto/duas instâncias/
restart/kill do parent/retorno de IO/cap64 e harness inbox24h ainda precisam CI.
Diagnóstico novo usa fase/exitcode fixos do processo próprio, nunca chave/frame.
Adapter WPF/agente segue OFF. Plano de consolidação/revisão independente será
registrado sem alterar/rebasear/integrar qualquer PR anterior.

Plano de consolidação/revisão independente em docs/STACK_REVIEW_PLAN.md contém
cadeia/SHAs capturados, unidades de revisão e gates futuros, sem executar merge,
rebase, squash ou retarget. Acrescentado teste WPF real de não herança de endpoints
com comparação de objetos (evita confundir número reciclado com handle herdado),
sem modificar fixture/agent/aceite. Publicação do segundo commit encontrou erro
interno GitHub commit_refs/HTTP500; não há recusa de autorização. Código está
commitado localmente e será publicado por caminho suportado, preservando históricos.

### Issue17 — CI ampliada: falha explícita de harness e correção do probe

Publicação por API928b301 (árvore e17973fa idêntica ao snapshot local) preservou
parent22f99e5 em fast-forward. Push Git encontrou500; commits locais não publicados
foram preservados, sem rebase/force/merge. CI41811218903: Linux/Chromium/Windows3.11
aprovados, Windows3.12 FALHOU em owner_harness_no_ready antes do kill. Não foi skip
nem aceito como prova. Demais adversariais reais/capacidade/WPF passaram naquele
job, mas isso não torna o job aprovado. Causa interna do harness não foi exposta
pelo stdout vazio; agora publica somente fase/exitcode fechados, sem trace/segredo.

Revisão encontrou fragilidade independente: número de handle válido pode ser
reutilizado para outro objeto, não prova herança. Probe de descendente/unrelated
agora duplica slots APENAS de filho possuído e usa CompareObjectHandles com objetos
locais; decoy é verificado pelo parent antes de gerar chave. Teste injeta lista de
herança alargada e exige rejeição ANTES de geração da chave. Bootstrap fechado é
checado antes de alocar outros handles. Nenhuma alegação de causa específica do
harness é feita sem nova evidência. Saturação1024 usa oito sessões normais128,
reduzindo flush/ACL/reopens redundantes sem mudar limites ou dispensar restart.

### Issue17 — revisão de objetos aprovada e corrida de ID eliminada

260900d / [CI41812922153](https://github.com/almirfsneto/observador-escritorio/actions/runs/41812922153):
5/5 jobs aprovados. Núcleo170: Linux143 executados/27 skips; Windows3.11/3.12
168 executados/2 browsers separados skipped. Chromium2 reais sem skips.14 testes
novos Windows do canal executaram, incluindo parent-kill, WPF/decoy/descendente,
foreignchild, lista alargada antes de chave, replay/contexto,2 instâncias/pausa,
restart/timeout/cap64/cancelamento e harness inbox. Saturação1024/10000/32 real
passou nos quatro Pythons/OS, clock de TTL injetado e integrity_check. A falha
anterior de prontidão vazia não é ocultada nem atribuída a causa não comprovada;
essa nova rodada passou sem reduzir checks/transformar falha em skip.

Revisão de concorrência encontrou risco potencial ao cancelar por native_id:
thread ID poderia ser reciclado antes de OpenThread. Worker agora duplica seu
próprio pseudohandle em handle real não herdável e o mantém sob lock curto para
CancelSynchronousIo/close, sem lookup por ID. Nenhum cancelamento de thread alheia
é permitido. Regressão existente exige handle não herdável e liberado após cancelar
IO pendente. Nova CI do HEAD requerida. Sem mudança no adapter (OFF).

Wheel sem dependências novas, compileall e manifesto conferidos. Plano completo
em STACK_REVIEW_PLAN.md; RETOMADA aponta PR18 e diferencia comprovado/modelo/
clock injetado/pendente. Nenhum PR anterior recebeu merge/rebase/retarget.

### Issue17 — evidência final do runtime e estado para revisão independente

PR18 / código0588d8a / [CI41814049436](https://github.com/almirfsneto/observador-escritorio/actions/runs/41814049436):
CINCO jobs aprovados.170 descobertos: Linux3.11/3.12 143 executados/27 skips,
Windows3.11/3.12 168 executados/2 browsers separados skipped. Chromium2 reais
aprovados sem skips (MV3/restart/receipt/ACK), nenhum caso foi aprovado via skip.
14 novos testes Windows do canal +4 portáveis de wire/default-off +3 de capacidade
somados ao baseline149. Endpoints/decoy/descendentes/WPF inspecionados como objetos
reais; lista alargada recusada antes da chave, argv/env sem chave inicial, segredo
por bootstrap32+EOF, handshake/identidades/HMAC verificados em processos reais.
Parent-kill encerrou descendente; IO pendente cancelou por HANDLE retido e liberado,
não thread ID reaberto. Worker/filhos encerrados, cap64 falha fechada e duas
instâncias/pausa/restart/replay/inbox exercitados.24h/TTL de retenção são clocks
injetados, não espera física; PID reuse forçado não foi alegado.

A revisão260900d/CI41812922153 já havia passado5/5;0588 comprova também a correção
de retenção do handle de worker. Falha de prontidão do harness3.12 em928b301 foi
registrada: causa interna do stdout vazio não isolada, sem falsificar aprovação;
as duas rodadas posteriores completas passaram. Investigar recidiva por fases,
nunca afrouxar schema/identidade ou repetir cegamente até passar.

Limites preservados: fixture IPC Python autenticada não é o WindowsObserver C#;
NativeSession/C#/lançador/schema de aceite v1 intocados. Adapter WPF continua OFF,
sem nova captura. Outra conta/sessão e humanosWin10/11/Chrome/Edge não executados;
mesmo token/admin/injeção/checkout adulterado não são fronteiras comprovadas.
SQLite/inbox em claro, quota lógica/amostrada, não OS/SSD/backups. Gates humanos e
LGPD/revisão independente permanecem, não apto a piloto. Nenhum dado real, equipe,
serviço/host/autostart, deploy, merge/rebase/retarget ou transmissão de capturas.

PROGRESS/DECISIONS/ROADMAP/RETOMADA, OWNED_CHANNEL e STACK_REVIEW_PLAN atualizados.
Manifesto124 arquivos, compileall, wheel sem dependências runtime novas e diff
conferidos. Última atualização é documental; CI do HEAD será conferida no PR.
Próxima tarefa: revisão independente do argumento de capacidade/ACL/herança e
matriz por outra conta/sessão autorizada, antes de novo entrypoint C# e adapter.
Plano de consolidação é só proposta por unidades de revisão; não executa merges
ou rebases. PR6 continua3d4a770 e PR16 continua294cb39. Nenhum observador segue ativo.

## Estabilização após primeiro aceite humano Win11 — 2026-11-04

Base PR18/233b301, branch nova codex/acceptance-stabilization, anteriores intactas.
Baseline170: Linux143 executados/27 skips. Recebido SOMENTE relato do responsável:
PR6/Win11,3 ensaios,2 expirações,3 limpezas, persistência opcional funcional e
avaliações positivas; ressalvas native_drop1,skip1,ZIP sem commit,flagWin11 indevida.
JSON local não solicitado/lido/versionado; SHA exato/build/skip/cause não inferidos.
Não transfere aceite humano para PR18 ou esta branch, nem libera piloto.

Correções de cálculo de gaps por OS com execução declarada, falha em todos skipped/
resumo desconhecido, root Git exato para impedir ZIP herdar commit ancestral,
runner com categorias fechadas e UI distinguindo execução de cobertura. Diagnóstico
complementar separado do schema v1 preservado, agregados/saúde cacheada em novas
sessões e sem taxa/causa/final-health inventados. Salvar v1 e falhar sidecar informa
resultado parcial corretamente. Fixtures são CONSTRUÍDAS, não JSON do operador.
11 regressões portáveis novas passaram localmente; Windows/CI ainda a conferir.
Documento docs/ACCEPTANCE_STABILIZATION.md registra semântica, limites e encerramento.

Autorrevisão SR-01: cleanup de PR18 podia interromper recursos/futures após
OSError de fechamento. Correção isolada continua os fechamentos/join e marca
shutdown não confirmado; duas regressões de falha INJETADA, não kernel real.
Pacote SECURITY_REVIEW_PR18.md organiza revisão independente ainda PENDENTE;
ACCEPTANCE_MATRIX.md separa OS/versão e gates, STACK_REVIEW_PLAN atualizado sem
convergência executada. Suite local181:154 executados/27 skips Windows/browser;
11 regressões novas executadas sem skips. Compileall, wheel e diff conferidos.
CI Windows e Chromium do novo HEAD ainda pendentes de publicação/execução.

### Evidência CI da estabilização — PR19 / código51b0691

https://github.com/almirfsneto/observador-escritorio/pull/19 (draft sobre PR18).
Commits117fbb6 (cleanup) e51b0691 (aceite/diagnóstico).
CI https://github.com/almirfsneto/observador-escritorio/actions/runs/41843386924
confirmada5/5 jobs, sem falhas. Logs de cada job consultados:

| Job | Descobertos | Executados | Ignorados / lacuna |
| --- | --- | --- | --- |
| Ubuntu Python3.11 |181|154|27:25 Windows +2 browser|
| Ubuntu Python3.12 |181|154|27:25 Windows +2 browser|
| Windows Server2025 Python3.11 |181|179|2 browser dedicado|
| Windows Server2025 Python3.12 |181|179|2 browser dedicado|
| Chromium real dedicado |2|2|0|

Os11 testes novos executaram em ambos os Windows/Linux; cleanup adversarial é
falha injetada. Guiado/exportação complementar e demais testes Win32 executaram
realmente no runner Windows, incluindo os casos de canal do PR18. Não houve skip
de foreground nesta rodada, mas isso não identifica o skip histórico do operador.
Skips browser no núcleo foram executados no job Chromium separado; não se tornam
aprovação do validador offline do operador. Execução estruturada local classificou
25 Windows/2 browser/0 unclassified. Manifesto132 arquivos, schema v1/lançador
intactos e nenhum JSON local do operador.

Inventário remoto conferido: todos os14 PRs anteriores continuam drafts com HEADs
e bases preservados, PR6=3d4a770, PR18=233b301. Sem merge/rebase/retarget, adapter
OFF, nenhuma instalação/coleta real/piloto. Próximos gates: revisão independente
por SHA, esclarecer descarte/skip/origem desconhecidos, Win10 humano e repetição
da candidata em Win10/11 autorizados. Matriz e critérios em ACCEPTANCE_MATRIX e
ACCEPTANCE_STABILIZATION; revisão organizada, não concluída, em SECURITY_REVIEW_PR18.
A próxima atualização é documental; conferir CI do HEAD final no PR19.

Revisão complementar do wrapper: CancelSynchronousIo antes ignorava retorno falso.
Agora1168/sem IO pendente é corrida normal; outro erro gera OSError tratado como
cleanup não confirmado. Terceiro teste de falha injetada exercita o wrapper real
com retornos success/1168/invalid-handle/None. Suite passa a182 descobertos; CI
do novo código será conferida. Wrappers compartilhados OwnedJob/ProcessProbe
ainda não verificam CloseHandle: risco explicitado no checklist independente,
sem alterar o contrato comum de cleanup de todas as entregas nesta correção.

### Evidência final do código de cancelamento — ed6099c

CI https://github.com/almirfsneto/observador-escritorio/actions/runs/41844547231
confirmada5/5 jobs.182 descobertos: Linux3.11/3.12,155 executados/27 skips
(25 Windows e2 browser); Windows Server2025 3.12,180 executados/2 skips
browser; Windows3.11,179 executados/3 skips (2 browser +1 foreground indisponível
no ensaio guiado). Chromium dedicado2 executados/0 skips. Logs consultados,
12 regressões novas executadas em Linux/Windows. Job Windows3.11 demorou mais,
mas concluiu aprovado nos executados; nenhuma causa da demora foi inferida.
O teste guiado3.11 NÃO executou nessa rodada;3.12 executou. Não confundir esse
skip conhecido de CI com o skip histórico desconhecido do operador. A anotação
inicial de dois skips em ambos os Windows foi corrigida ao conferir o log3.11.
Rodadas documentais abfd1a2/41844243856 e41844251334 foram CANCELADAS pela
concorrência ao publicar a correção seguinte; não contadas como aprovadas.
Suite local182:155 executados/27 skips; compileall e manifesto verificados.

Critérios de encerramento técnico: CI do candidato, regressões e matriz documentada.
Critérios de aceite continuam abertos: revisão independente por SHA, auditoria dos
wrappers compartilhados, origem/skip/descarte históricos e ensaios humanos por
OS/versão. PR19 permanece draft, PR6 e anteriores intactos. Último commit apenas
registra esta evidência; resultado dos checks do HEAD final também consta no PR19.

## Issue 20 — fechamento e identidade próprios — 2026-11-04

Base exata PR19/bee7d1c, nova codex/verified-handle-cleanup. Leitura obrigatória e
Issue20 conferidas; baseline182: Linux155 executados/27 skips. A1–A4 corrigidos:
BOOL CloseHandle verificado, erro cleanup_unconfirmed, referência retida e sem
retry automático; job termina membros explicitamente/consulta zero antes de
fechar; runner continua limpeza de processo/reader/stdout e bloqueia reutilização
incerta; sampler tenta todos os probes e integra falha à limpeza do aceite v1.
Duplicação de handle Popen retido substitui OpenProcess(pid), com identidade
conferida antes de memória. Token de ACL falha fechado sem retornar SID em erro.

Nove regressões portáveis executadas; quatro Windows novas aguardam CI. São
falhas injetadas, não exploração observada. Testes reais planejados usam apenas
handles sintéticos protegidos contra fechamento e job com descendente próprio.
Critério de revisão distinta do implementador permanece pendente; nenhuma
aprovação independente simulada. Detalhes em docs/HANDLE_LIFETIME_REVIEW.md.
PR6/schema v1 e branches anteriores preservados, adapter OFF e nenhum piloto.

### Issue20 — evidência Windows real e CI do código7740254

PR21 em rascunho sobre PR19, código cb8b27f e regressão7740254.
CI https://github.com/almirfsneto/observador-escritorio/actions/runs/41857555311
(rodada PR): CINCO jobs aprovados; logs de todos consultados.

| Ambiente | Descobertos | Executados | Ignorados |
| --- | --- | --- | --- |
| Ubuntu Python3.11, por job |195|164|31:29 Windows +2 browser|
| Ubuntu Python3.12, por job |195|164|31:29 Windows +2 browser|
| Windows Server2025 Python3.11 |195|193|2 browser dedicado|
| Windows Server2025 Python3.12 |195|192|2 browser +1 foreground do ensaio guiado|
| Chromium dedicado |2|2|0|

Na rodada push41857540952, Windows3.12 também concluiu aprovado:193 executados/
2 skips; o ensaio guiado executou ali. Push3.11 concluiu aprovado:192 executados/
3 skips (2 browser e1 foreground guiado). A rodada push também teve CINCO jobs
aprovados, todos os logs conferidos. Skips de foreground são lacunas explícitas,
não testes aprovados nem identificação do skip humano histórico.

Os13 novos testes executaram em ambos os Windows: nove negativos injetados e
quatro nativos reais. REPRODUZIDO EM KERNEL, de modo controlado: CloseHandle
retorna falha para job/probe próprios deliberadamente protegidos com
HANDLE_FLAG_PROTECT_FROM_CLOSE. Referência preservada/cleanup_unconfirmed; teste
remove proteção e libera o handle ainda comprovadamente próprio em cleanup.
Job com pai/descendente confirmou ActiveProcesses>=2 antes e zero após término;
prova do mesmo objeto duplicado/não herdado, ticks e recusa após exit passou.
Não é falha espontânea de campo, exploração ou reuso real de PID demonstrado.

SIMULADO/INJETADO: falhas de terminate/query/timeout, identidade inicial falsa,
falhas de token/probes/múltiplos recursos e atribuição ao job após spawn. Incluem
futures drenados, reader.join, stdout fechado e recusa de retry após incerteza.
Não atribuir esses cenários ao kernel real nem ao descarte histórico do PR6.

Suite local195:164 executados/31 skips, categorias29 Windows/2 browser/zero
unclassified. Compileall, wheel, diff e manifesto135 arquivos verificados;
schema v1 e CMD iguais à base. Critério6 (revisor distinto do implementador)
permanece PENDENTE; a Issue20 não recebe sign-off independente por esta execução.
Sem merge/rebase/deploy/instalação, adaptador OFF, nenhum dado real ou piloto.
Última atualização documental terá seus checks de HEAD conferidos no PR21.

Inventário residual: NativeSession.creation_ticks ainda fecha sem verificar BOOL
e abre por PID. Fora dos wrappers A1–A4/métricas; entrypoint legado não alterado
nesta entrega focada. Exige revisão separada antes de ampliar confiança/piloto;
não é falha observada de campo. Ver HANDLE_LIFETIME_REVIEW para a fronteira.

As rodadas cb8b27f/41857235380 e41857457482 foram canceladas pela concorrência
ao publicar a regressão seguinte, não contadas como aprovadas. A entrega não
encerra o critério6 sem revisão por pessoa distinta. Próxima tarefa: revisor
auditar diff focado e confirmar ownership/teardown usando provas por SHA; depois
tratar o inventário residual em entrega própria, sem habilitar adapter ou piloto.

## Issue22 — AI-01/AI-02 — 2026-11-04

Base PR21/8abbb5b, nova codex/legacy-binding-cleanup. Auditoria da Issue22 aceita
tecnicamente A1–A4/Issue20 por revisão IA distinta, sem assinatura humana/piloto.
AI-01: identidade legado por duplicata do Popen retido, criação/PID conferidos,
CloseHandle verificado; sem PID lookup ou provider após falha de binding/close.
AI-02: cleanup por recurso com enums/contagens fechados, sempre tenta demais
filhos/sink/sampler/joins/IO; children_stopped=false se algum recurso fica incerto.
Startup parcial também faz teardown; não fecha pipe sob thread ainda viva.
Schema v1/CMD e PR6 intactos. Contrato em docs/LEGACY_BINDING_CLEANUP.md.

Baseline195: Linux164/31 skips. Revisão206:172 executados/34 skips locais; oito
negativos/controle novos passaram, três Windows novos aguardam CI. São injeções,
não reuso real de PID ou falhas do operador. AI-03 terá análise e experimento
isolado em filha separada, sem alterar launcher em uso, adapter ou demais gates.

### Issue22 AI01/02 — PR23 e bloqueio de CI

PR23: https://github.com/almirfsneto/observador-escritorio/pull/23, código
a332be4beb61fa219d136582e3b005c72e43be9f, base PR21/8abbb5b.
CI push41900708978 e PR41900750727 falharam nos CINCO jobs antes de qualquer
etapa: steps null/vazios, conclusão em poucos segundos, logs BlobNotFound.
Uma reexecução controlada do PR (attempt2) repetiu cinco falhas sem etapas.
Não há teste CI aprovado ou Windows novo comprovado nesta entrega. Causa
administrativa não exposta; consulta de anotações não suportada pelo conector
e CLI normal recebeu Forbidden. Não atribuir a cobrança/quota sem evidência.

Local Linux:206 descobertos,172 executados/34 skips (32 Windows/2 browser).
Oito regressões portáveis novas executadas; três Windows novas apenas preparadas
e compiladas, NÃO executadas. Snapshot de sintaxe/wheel/diff conferido. Chromium
local tem ExtensionInstallBlocklist=*; não contornado nem contado como aprovado.
A CI completa deve ser reexecutada após restaurar o serviço/permissão do Actions.
Revisor técnico deve considerar patch ainda SEM comprovação Windows desta revisão.

Próximo passo independente viável: finalizar estudo AI03 em filha separada, sem
alterar Popen→assign dos launchers existentes ou habilitar adapter. Nova revisão
IA por SHA não é assinatura humana; AI04 continua integralmente aberto.

## Issue22 — AI03, estudo isolado

Branch codex/suspended-launch-study sobre PR23/5c37576. Design compara launcher
atual, criação suspensa e Job na criação. Suspender/assign/resume não resolve
morte do launcher antes do assign; essa limitação permanece explicitamente aberta.
Experimento exclusivamente em tests/, não empacotado no runtime; nenhum launcher
em uso foi trocado. Quatro casos Windows preparados: pre-resume/membership/
decoy/descendente, falhas injetadas, crash pós-assign e crash pré-assign com
capacidade retida pela raiz para cleanup. Nenhum deles executou em Windows nesta
sessão; nomes REAL são condicionais à execução futura, não evidência presente.

Contrato em docs/SUSPENDED_LAUNCH_STUDY.md. CI será solicitada no PR desta filha;
bloqueio pré-etapas do PR23 registrado, sem novas tentativas cegas nem alteração
de política/cobrança/permissões. AI04 segue aberto. Nenhuma captura, adapter ou
piloto; todos os PRs anteriores e o schema de aceite v1 ficam intactos.

Verificação local da filha AI03:210 descobertos,172 executados/38 skips
(36 Windows/2 browser), nenhum skip contado como aprovado. Os quatro novos
casos Windows não executaram; sintaxe/importação compilaram no Linux. As únicas
mudanças em src/ na filha são a categoria de skip do runner, não launchers.

## Issue22 AI02 — ciclo de vida do worker, complemento sobre PR24

Nova codex/cleanup-worker-lifetime, filha de PR24/b974356. Revisão final revelou
que o worker daemon podia ser abandonado ao terminar o intérprete após join
limitado. Regressão em subprocesso REAL Linux reproduziu marker ausente com
atraso CONTROLADO de200ms e join10ms; não é falha espontânea de Windows/operador.
Worker agora é não daemon e espera standalone aumenta de6s para20s. O mesmo
teste passou após correção. Teardown pode sobreviver ao retorno do main e
concluir os recursos; não há promessa de deadline global se uma API travar.

Suíte local211:173 executados/38 skips (36 Windows/2 browser). Oito cenários
negativos portáveis de AI01/02 mais a nova regressão de lifetime executaram;
os três novos Windows de binding/cleanup e quatro de AI03 NÃO executaram.
CIs finais do PR23/5c37576 (41901835390/41901844826) e PR24/b974356
(41902372110; conferir também rodada PR) falharam antes de qualquer etapa nos
cinco jobs; nenhum teste foi executado nesses jobs. CI desta terceira entrega
será solicitada ao publicar, sem presumir sucesso.

PR23/PR24 e os16 PRs anteriores preservados. O candidato final é esta filha;
revisor deve conferir cada diff contra sua base e os três SHAs finais. Restaurar
execução do Actions, reexecutar matrizes completas, corrigir resultados Windows
e Chromium e só então avaliar aceitação técnica; AI04/piloto seguem bloqueados.

## Issue27 — diagnóstico primeiro, base PR25 exata — 2026-11-04

Nova codex/suspended-cleanup-diagnostics sobre d820396176f64323c578f481132856aa484b58f0.
Issue27/atualizações22 e pareceres23/24/25 lidos. Infraestrutura voltou a executar
após mudança de visibilidade feita pelo responsável; não foi alteração desta
tarefa. Base PR25/CI41903503682 attempt2 tem dois erros reais em cada Windows
211 descobertos/2 skips; Linux e Chromium passaram. PR23 attempt2 passou5/5.

Primeira entrega mantém a falha: diagnósticos só no estudo tests/, com fases/
recursos fechados, primeiro erro, estado do Job/handles e observação posterior
da espera após falha. Nenhum PID/handle numérico/path/segredo/exceção livre.
Não há promoção de status.confirmed ou mudança de timeout/checagens. Step focado
Windows antecede suíte completa para obter evidência causal antes de corrigir.
Prioridade2: stop pré-worker será corrigido após esse diagnóstico, com injeções
e fallback se thread não iniciar. Todos os PRs anteriores preservados.

### Issue27 P1 — causa demonstrada antes da correção

Diagnóstico ed7c50d/CI41929775944: Linux3.11/3.12 e Chromium success; ambos
Windows FALHARAM no estudo focado4 testes/2 erros, sem skips. Logs dos dois
Windows consultados: first_failure=process_fallback, native_error=access_denied,
job_terminate/job_zero/job_handle_close=passed, processes_confirmed=true;
process_wait inicial=timeout, after_failure_wait=passed, ambos handles=closed.
A falha era o fallback TerminateProcess prematuro após Job zero: o código
transformava BOOL false em erro antes da confirmação posterior que provava saída.
Não foi falha comprovada de CloseHandle/Job nem vazamento de handle.

Correção: quando atribuição retornou sucesso e Job terminou/zerou/fechou, aguardar
o processo antes do fallback. Mantém orçamento original de2s por processo;
fallback só usa o remanescente, sem aumento de timeout. AccessDenied no fallback
só pode ser recuperado com espera sinalizada e Job confirmado; evento de erro
continua visível com exit_race_confirmed. Outras falhas de API/espera/close
permanecem cleanup_unconfirmed e os demais handles continuam tentados.
Cinco regressões injetadas passaram localmente; dois novos Windows preparados:
close protegido continua recusado, e API real de término em processo já saído
com primeira espera INJETADA. Novos resultados nativos ainda a conferir.

### Issue27 P2 — stop pré-worker tolerante a erros

Stream, controles Tk e pré-observações do aceite agora são tentativas isoladas.
Falha em Thread constructor/start usa fallback síncrono; barreira de startup e
lock garantem erro registrado antes do resultado e uma única limpeza mesmo se
start lançar após launch. Join não iniciado não escapa do finally. Erros ficam
em enums/contagens e children_stopped=false; não se atribui sucesso ao fallback
só porque filhos acabaram. Seis testes portáveis novos passaram, incluindo cada
controle, observação, startup e caso positivo; um Windows preparado usa TclError
real de controles destruídos com filhos/IO/queue/sampler reais.

Suite local225:184 executados/41 skips. Não são provas Windows; aguardar CI da
revisão P2. Contrato/evidência em docs/ISSUE27_CLEANUP.md. Política de worker não
daemon/join20s inalterada: API bloqueada ainda pode reter processo, sem promessa
de deadline global. Sem integração do launcher suspenso ou mudança de adapter.

P1 corrigida640bb36/CI41930859247: CINCO jobs aprovados, logs conferidos.
Windows3.11/3.12: foco11 executados/0 skips, suíte218 descobertos/216 executados/
2 browsers ignorados; Linux178 executados/40 skips; Chromium2/0. Os dois erros
originais desapareceram com confirmação de saída/Job/handles. Close protegido
continua explicitamente reprovado dentro do teste negativo; corrida híbrida
registra erro real de TerminateProcess em processo saído + primeira espera
INJETADA. P2 e seu teste Tk real ainda aguardam a próxima CI.

### Issue27 — evidência integrada P1/P2 e revisão final

PR28: https://github.com/almirfsneto/observador-escritorio/pull/28, draft sobre
PR25/d820396 exato. Código integrado6e0cf86,
https://github.com/almirfsneto/observador-escritorio/actions/runs/41931710044
confirmada5/5 jobs, logs de todos consultados.

| Job | Descobertos | Executados | Ignorados |
| --- | --- | --- | --- |
| Linux Python3.11 |225|184|41:39 Windows +2 browser|
| Linux Python3.12 |225|184|41:39 Windows +2 browser|
| Windows Python3.11 |225|223|2 browser dedicado|
| Windows Python3.12 |225|223|2 browser dedicado|
| Chromium dedicado |2|2|0|

Foco suspenso adicional:11 executados/0 skips em cada Windows (não somar como
casos inéditos à suíte completa). Nenhum skip de foreground nessa rodada.
Os14 testes novos executaram nos Windows;11 portáveis também passaram no Linux.
REPRODUZIDO/REAL: diagnóstico inicial dos dois erros apontou fallback prematuro
access_denied após Job confirmado e espera posterior sinalizada; erro de close
protegido segue recusado realmente; TclError de controles próprios destruídos
foi real e filhos/IO/queue/sampler foram comprovados encerrados, mantendo
children_stopped=false pela falha da UI. Crash pré/pós-assign continua exercitado
como estudo isolado, com limpeza final da raiz, não contenção atômica integrada.

INJETADO: retornos/esperas/Job/close nos cinco testes portáveis de diagnóstico;
stream/UI/observação/constructor/start/after-start nos seis casos pré-worker.
HÍBRIDO: TerminateProcess real em processo já saído, primeira espera simulada;
recuperação exige prova e mantém evento failed/access_denied explícito. Nenhum
caso foi convertido em skip nem timeout aumentado para obter aprovação.

Compileall, wheel sem dependências novas, diff e manifesto147 arquivos
verificados; v1/CMD e launchers CommandRunner/OwnedSyntheticChannel intocados.
Rodada diagnóstica ed7c50d/41929775944 permanece FALHA como evidência causal,
não mascarada. Rodada inicial d5218bd cancelada por concorrência ao corrigir
import do helper sob -I; não contada como aprovação. P1/640bb36 passou depois;
a implementação P2/6e0cf86 passou integrada. Próxima atualização é documental;
checks do HEAD final serão conferidos e vinculados na descrição do PR28.

Gates abertos: API que bloqueia sem exceção ainda pode reter worker não daemon;
sem watchdog/deadline global, assinatura humana ou aceite Win10/11 desta versão.
Morte da raiz pré-assign permanece gap, estudo não integrado, adapter OFF e AI04
inalterado. Próxima tarefa é nova revisão técnica por SHA, sem merge/rebase,
instalação, coleta real ou piloto. Todos os19 PRs anteriores serão conferidos
novamente com seus HEADs/bases/draft preservados.

## Issue29 — Job na criação, sem integração — 2026-11-04

Base exata508c38ad0996e7854c788cf08f655c8b65225707/PR28, nova
codex/job-at-creation-study. Issue29, Issue22/atualizações e parecer técnico28
lidos integralmente, além dos documentos obrigatórios. Experimento em tests/
usando STARTUPINFOEXW/JOB_LIST no CreateProcessW com filho suspenso, herança zero,
ambiente mínimo, kill-on-close, membership antes de resume e sem assign/fallback.
Lista/valor retidos até Delete VOID; falha preserva storage/diagnóstico, tenta
outros recursos e permanece não confirmada. Contrato em JOB_AT_CREATION_STUDY.md.

Sete testes portáveis aprovados localmente, oito Windows apenas preparados:
positivo/descendente/decoy, três crash points, nested externo aberto, argumentos
inválidos reais, guardas injetados e close protegido. Windows exigido sem skip;
novo step focado antecede suíte geral. Não alegar execução nativa antes da CI.
Nenhum arquivo src/, launcher ou aceite modificado. Issue30 não iniciada.

### Issue29 — primeira CI e investigação de contagem

2839ab8/CI41958864997: Linux/Chromium aprovados; ambos Windows FALHARAM no
positivo, ActiveProcesses=3 contra2 esperado. Os três crashes e nested/negativos
executaram e passaram, mas isso não aprova o job. Não reduzido assert nem timeout.
Hipótese testável: descendant Popen sem CREATE_NO_WINDOW solicita console novo.
Revisão acrescenta A/B real mudando somente esse flag, contagem antes/depois e
zero após cleanup. Fixture padrão passa a não solicitar console para descendant,
mantendo assert exato2. Aguardar comparação nativa antes de afirmar causa.
Root agora transfere/fecha explicitamente o handle Popen retido com BOOL checado,
além dos handles duplicados, IO e reader; não depende do GC para essa prova.

A hipótese de console isoladamente NÃO se confirmou:4130c29/CI41959187379
teve3 membros mesmo com NO_WINDOW e4 no positivo posterior; Windows falharam,
Linux/Chromium passaram. Não atribuir identidade ao membro adicional nem dizer
que o flag corrigiu a contagem. Substituir a premissa incorreta de cardinalidade
exata2 por verificação MAIS ESPECÍFICA: QueryInformationJobObject(ProcessIdList)
do Job próprio deve conter os dois IDs obtidos de handles retidos, lista completa
limitada16, contagem agregada>=2 e zero obrigatório após término. Nenhum PID
reaberto/processo adicional inspecionado. A/B fica diagnóstico, não causa inferida.
Nested agora cobre também pós-resume, com Job externo aberto e zero consultado
após morte do launcher: inclui todos os membros, não somente os dois conhecidos.
Negativas injetadas de terminate/query/close usam recursos Windows reais e mantêm
cleanup não confirmado, tentando atributos/ambos handles. Não alterado src/.

Revisão b930aab/CI41959651181: primeiro Windows executou positivo, lista completa,
zero, três crashes, nested pré-verify e negativos. Subcaso nested pós-resume FALHOU
na barreira de controle: CLI ainda codificava nested_before_verify para ambos.
Erro do harness, não filho órfão observado; finally limpou os recursos. Corrigir
encaminhamento explícito nested_after_resume antes de novo aceite. A/B confirmou
membros3/4 com ambos conhecidos presentes e zero após cleanup; origem adicional
não identificada. Não chamar esse run de aprovado, nem ampliar timeouts.

### Issue29 — evidência integrada por SHA e limites de revisão

PR31 em rascunho sobre PR28 exato; código518678a7d991e3e26650172ca8557203ae34e15f.
CI https://github.com/almirfsneto/observador-escritorio/actions/runs/41959802089
CINCO jobs aprovados; logs dos cinco consultados. Não transferir essa evidência
para integração runtime nem aceite humano. Último commit apenas documental terá
CI própria conferida no PR31.

| Job | Descobertos | Executados | Skips |
| --- | --- | --- | --- |
| Windows Python3.11 |242|240|2 browser dedicado|
| Windows Python3.12 |242|240|2 browser dedicado|
| Linux Python3.11 |242|191|51:49 Windows +2 browser|
| Linux Python3.12 |242|191|51:49 Windows +2 browser|
| Chromium dedicado |2|2|0|

Foco Job List17/0 skips por Windows; foco suspenso anterior11/0 por Windows.
São reexecuções de casos presentes na suíte, não testes únicos adicionais. Os17
novos casos únicos executaram em cada Windows: sete portáveis e dez dependentes
de Windows; dois destes últimos injetam guardas/cleanup em recursos reais. Oito
casos Windows reais incluem cinco barreiras de crash (três normais e dois subcasos
aninhados),
positivo completo, argumentos inválidos, A/B de console e close protegido.
Skips não são aprovações; nenhum foreground ignorado nesta rodada.

REAL em ambos Windows: CreateProcess com Job List, IsProcessInJob antes de resume,
sem herança de Job/decoys, descendant membership; processo suspenso não escreve
marker. Launcher morto abruptamente pré-verify/pré-resume/pós-resume: capacidades
retidas pela raiz sinalizadas, sem Job alvo retido. Nested pré-verify E pós-resume:
Job externo permanece aberto; filhos conhecidos saem e consulta de TODO Job
externo confirma zero antes de seu fechamento. Handles duplicados/launcher Popen
foram fechados explicitamente, reader/IO encerrados. Parâmetros inválidos recusados
por API real; handle protegido recusado realmente sem cleanup confirmado/retry.

A/B REAL e lista do Job registraram membros adicionais aos dois conhecidos,
com ambos presentes e ZERO após cleanup. Origem adicional NÃO identificada;
nenhum PID reaberto/imagem de processo extra inspecionada. Não prometer exatamente
um descendant total nem atribuir a conhost/redirector. Crash sem Job externo prova
diretamente só processos conhecidos; nested/positivo provam zero de todos os
membros por consulta kernel. Não manter Job alvo para consultar depois do último
close, pois invalidaria causalidade. Isso permanece ponto de revisão explícito.

INJETADO: sete contratos de tamanho/lifetime/erros/ordem/sanitização em Linux e
Windows, mais guardas membership/resume e recusa terminate/query/close sobre
recursos Win32. Exceção de Delete VOID conserva storage e status não confirmado;
retorno normal cumpre contrato da API, não é verificação independente de heap.

Local242:191 executados/51 skips, compileall, wheel sem experimento no pacote e
manifesto151 arquivos verificados. Diff de src/, ferramentas, extensão, v1/CMD
idêntico à base. Vinte PRs anteriores conferidos sem alteração de HEAD/base/draft,
inclusive PR6. Adapter OFF; sem merge/rebase/deploy/instalação/dados reais/piloto.

Rodadas falhas2839ab8/41958864997 e4130c29/41959187379 preservadas: premissa de
cardinalidade exata incorreta, hipótese console insuficiente. b930aab/41959651181
falhou na barreira nested pós-resume; corrigido encaminhamento em518678a. Não foram
skips, falhas do produto em campo ou razões para ampliar timeout. Em nenhuma delas
a prova de sucesso foi satisfeita por emergency cleanup da raiz.

Próximo gate: revisão independente do SHA final conforme JOB_AT_CREATION_STUDY.md.
Experimento permanece só tests/, sem corrigir ainda Popen→assign dos launchers.
Runner Server x64 não prova Win10/11 humano, ARM64/x86, mesmo token/admin, todos
nested Jobs ou criadores/brokers. Issue30 NÃO iniciada; liveness/AI04 e demais
gates continuam abertos. Aguardar revisão do responsável antes da próxima issue.

## Issue #30 — liveness de cleanup, fase de desenho (2026-11-05)

Base congelada PR31/8fd16bcd00183eb04d3ac759fa91d57978260b56, branch `codex/cleanup-liveness-contract-issue30`. O PR31 já havia sido
revisado tecnicamente como experimento Win32, não liberado para runtime. A Issue29
está encerrada no escopo de prova isolada; Issue22/AI04 e revisão humana abertos.

Este ciclo não modifica `src/`, os launchers, WindowsObserver, adapter, IPC ou
coleta. Novo desenho `docs/CLEANUP_LIVENESS_DESIGN.md`: contrato distingue
liveness de worker, cancelamento, teardown real de filhos/Job/handles e UI.
Comparadas três opções: thread local/cancelamento limitado; processo supervisionado
com Job-at-create; watchdog externo. O processo sintético supervisionado é
hipótese de próxima fase, NÃO mecanismo implementado nem prazo global garantido.

`tests/test_cleanup_liveness_design.py` acrescenta 9 testes: oito contratos
negativos/positivos fechados e um processo real **sintético** com thread
não-daemon bloqueada após join limitado; o teste termina apenas seu processo próprio.
Não é teste de CancelSynchronousIo real nem prova de Job ou coleta operacional.
Local Linux/Python3.13: 9/9. CI Windows3.11/3.12, Linux3.11/3.12 e Chromium
precisa ser aferida no SHA desta branch, sem promover skips ou repetição de foco.
MANIFESTO_SHA256 inclui os dois arquivos novos e as mudanças de documentação.

Próximo gate: conferir a CI e a revisão do desenho antes de implementar supervisor.
Nenhum merge/rebase, ativação de adaptador, piloto, instalação ou dado real.

## Issue #30 — segunda leitura adversarial do contrato

Após a CI verde do SHA 457734be/42003106492, dois invariantes estavam sem teste:
worker que termina **após** deadline perdia o registro de expiração; ACK de
cancelamento sem pedido era aceito. Foram corrigidos no classificador **somente de
testes**, acrescidos dois negativos (agora 11 casos novos). O campo
`worker_exit_confirmed` permite relatar conclusão tardia, sem apagar
`worker_state=deadline_expired`. Prova física de limpeza e pontualidade são
dimensões separadas. O classificador não é ledger nem prova origem das flags;
proveniência e histórico monotônico permanecem requisitos de futura integração.

A CI 42003106492 prova apenas o SHA anterior, não o HEAD corrigido. Reexecutar
Windows3.11/3.12, Linux3.11/3.12 e Chromium antes de aceitar esta revisão.
Nenhum runtime, launcher, adapter, IPC ou dado real foi alterado.

## Issue33 — supervisão sintética isolada — 2026-11-05

Base exata PR32/f1fb334bc4b9048c6a604610923e028ecd3ef658, nova branch
codex/synthetic-process-supervision. Issue33/contrato30/parecer32 e documentos
obrigatórios lidos; CI42006356534 do SHA base success5/5 conferida. Nenhum runtime,
launcher, C#, extensão, IPC ativo ou adapter alterado. Costura de fixture somente
no harness de testes31 preserva default. Novo experimento usa Job List na criação,
lock indefinido no subordinado e raiz independente, flags sticky de prazo/erro,
protocolo fechado e APIs de saída/zero/close como prova física.

Guarda recusa Job com extras desconhecidos e não faz bulk kill. Desarmar
kill-on-close com verificação antes de liberar Job incerto; término emergencial
somente por handles próprios. Se disarm falha, reter Job, não declarar limpeza;
limite de destruição posterior da raiz/driver permanece. Desenho/evidência em
SYNTHETIC_PROCESS_SUPERVISION.md. 14 portáveis passaram, dez Windows preparados,
ainda não executados. Foco Windows e matriz completa mantidos, sem converter skips.

### Issue33 — primeira CI: recusa real de ownership, não relaxar segurança

470cc6a/CI42010080293: Linux/Chromium passaram; ambos Windows FALHARAM no foco24
(4 falhas cada, zero skips). Snapshots nativos mostraram raiz responsiva, join
insuficiente e deadline sticky; membros adicionais desconhecidos reais também
neste worker. Guarda recusou bulk termination, disarm foi confirmado, somente
processo conhecido terminou por handle e Job zerou/handles fecharam. Estado final
manteve cleanup_unconfirmed por ownership, corretamente. Expectativa do teste de
aprovação incondicional era incorreta; não remover guarda nem apagar erro.

Revisão exige TODAS as provas físicas e, em unknown, bulk nunca chamado + disarm
confirmado + resultado unconfirmed. Crash pós-início recusava barreira e finalmente
limpava, em vez de provar morte abrupta. Nova barreira desarma Job alvo incerto
ANTES do crash e entrega somente capacidade própria à raiz. Depois da morte real
do launcher, raiz tenta terminar worker por esse handle e exige saída; não alega
kill-on-last-close para Job desarmado. Nested externo também é desarmado se houver
membros incertos, mantido aberto até consulta zero. Origem extra não inferida.
Os novos testes são julgados pela próxima CI; nenhum timeout aumentado/skip novo.

Autorrevisão adicional do caminho de espera falha: reter a capacidade de processo
quando saída não é confirmada, em vez de fechar a última referência a um worker
possivelmente vivo. Thread e demais recursos continuam tentados. Negativo portável
exige ausência de close do processo e referência retida; negativo Win32 usa cópia
retida independente, confirma saída com API real e só então faz PRIMEIRO close da
referência original (sem retry de slot failed). Erro da primeira limpeza continua
sticky. Não há garantia de recuperação se o SO negar todas as provas de saída.

Complemento de cancelamento: janela cooperativa local50ms sem bloquear raiz,
com leitura de cancel_without_ack da fixture antes de encerrar. Snapshot distingue
recusa observada de mera falta de resposta. Expiração global local continua200ms,
sem aumento. Corrida de exit após pedido não apaga falta de ACK; ping não sobrescreve
pedido cancel pendente. Novo negativo portável realça os dois invariantes (15
portáveis novos,25 focados somando10 Windows). Não é CancelSynchronousIo nativo.

### Issue33 — falha real de comunicação pré-teardown e regressão de sharing

f502c9f/push CI42011080743: Windows3.11 passou; Windows3.12 FALHOU na suíte
completa (foco24 havia passado), em saída tardia. Snapshot: atributos/Job/handles
não tentados e só process_wait marcado; a exceção ocorreu antes de NativeWorker.close,
na escrita do comando release. Classe WinError da ocorrência NÃO foi capturada;
não atribuir código específico ao run antigo. Fixar finally no estimulador tardio
para sempre executar teardown e classificar erro de comunicação corretamente.

Há corrida verificável no desenho de arquivo: replace atômico Windows concorre
com leitores Python sem FILE_SHARE_DELETE. Novo negativo REAL prepara reprodução de recusa
em arquivo sintético próprio e compara leitor Win32 com sharing7, que permite
replace. Raiz e worker passam a ler com esse sharing e CloseHandle verificado;
fechamento de arquivo falho retém dono failed e impede confirmação. Não aumentar
timeout/repetir replace cegamente. Novo teste portável cobre close de arquivo.
Agora16 portáveis +11 Windows=27 focados novos; futura suíte280. Os runs anteriores
cancelados ao publicar revisões não são aprovações. Aguardar CI deste código.

cd18fd9/CI42012749672: ambos Windows falharam apenas na expectativa de WinError32
no negativo de arquivo (27 focados,26 passaram/zero skips). O retorno REAL foi
AccessDenied5 nos dois Pythons. Ajustar o código esperado para5, mantendo recusa
obrigatória e sucesso da MESMA substituição com leitor share7. Não confundir com
identificação do WinError do run antigo f502, que não foi capturado. Os demais
casos, incluindo LateWorker com finally e sharing, passaram no foco; matriz total
ainda depende de CI verde deste próximo SHA.

1e7ba5c/CI42013116584: ambos Windows falharam no sucesso de replace mesmo com
share7; Win3.12 também não observou a recusa de cancelamento no fluxo antigo.
Hipótese sharing suficiente REFUTADA. Redesenhar transporte só de testes com nomes
imutáveis por sequência: não substituir arquivo aberto. Regressão conserva ambas
recusas reais e exige publicar nome novo mantendo leitor antigo aberto e dados
antigos intactos. Mesmo limite256/seq64, sem retry/timeout ampliado. Histórico das
hipóteses falhas permanece, sem claim causal retroativo ao primeiro run.

### Issue33 — evidência integrada da publicação imutável — 2026-11-05

PR34 em rascunho, base EXATA f1fb334bc4b9048c6a604610923e028ecd3ef658/PR32.
Código e2a865543126abeb6b3eb960e0b91b0e81a4f7e4:
https://github.com/almirfsneto/observador-escritorio/actions/runs/42014095213
CINCO jobs aprovados; logs de todos consultados.

| Ambiente | Descobertos | Executados | Skips |
| --- | --- | --- | --- |
| Windows Python3.11 |280|278|2 browser dedicado|
| Windows Python3.12 |280|278|2 browser dedicado|
| Linux Python3.11 |280|218|62:60 Windows +2 browser|
| Linux Python3.12 |280|218|62:60 Windows +2 browser|
| Chromium dedicado |2|2|0|

Foco novo27/0 em cada Windows; foco anterior17/0 e11/0 preservados. São os mesmos
casos da suíte, não somar duas vezes. Novos27 únicos:16 portáveis +11 Windows,
sendo nove de operações Win32 reais e dois com falhas de API/ownership injetadas
em recursos reais. Nenhum skip de foreground nesta rodada; skips não são aprovação.

REAL nos dois Windows: worker normal e lock indefinido após join; raiz com ticks/
pong, deadline_expired antes de stop; processo sinalizado, Job zero e recursos
fechados. Extras desconhecidos reapareceram; bulk foi recusado, disarm confirmado
e somente handle próprio usado. physical_cleanup_confirmed=true NÃO apagou
cleanup_unconfirmed por ownership. Cancel recebeu resposta explícita de recusa
sem ACK e permaneceu unconfirmed; saída tardia preservou expiração. Erro de close
protegido foi real e nunca aprovado. File replace aberto recusou AccessDenied5
COM e SEM share de delete; publicar nome imutável novo funcionou com leitor
antigo ainda aberto e conteúdo antigo intacto. Esses dois fatos são distintos;
sharing sozinho não foi solução. Nenhum retry/timeout ampliado para verde.

Crash REAL pré-start: Job conhecido armado, kill-on-last-close confirmou saída.
Pós-start e nested: Job alvo com extras foi desarmado ANTES de matar launcher;
raiz externa encerrou worker por handle próprio e confirmou saída. Isso é
root_retained_process_handle, NÃO término automático por último Job. Nested
também observou extras no externo, desarmou-o e manteve-o aberto até zero de todos
os membros. Raiz não manteve Job alvo; IO/readers/capacidades próprios fechados.
Se raiz externa também morrer após disarm, essa prova não garante contenção.

INJETADOS: criação/atributos/membership, terminate/query/wait/closes, cancelamento
sem resposta/ACK indevido/corrida de exit, erros de comunicação e file close,
unknown members e disarm negado. Wait sem prova retém capacidade de processo;
negativo real usa cópia própria para provar fim antes do PRIMEIRO close da
referência retida. Disarm negado conserva Job, sem bulk/close, e não confirma.
Não é driver real bloqueado nem garantia global de liveness/cleanup da própria raiz.

Histórico preservado:470cc6a/42010080293 falhou em quatro expectativas por Win;
f502c9f/push42011080743 falhou na saída tardia Win3.12 antes de teardown;
b882cce/42011761928 falhou em comunicação/expiração no ensaio tardio Win3.12;
cd18fd9/42012749672 falhou na expectativa de código32 (real5);
1e7ba5c/42013116584 refutou replace aberto mesmo com share7. Runs cancelados de
78860e9 e PR/f502 não são aprovados. Erro original de f502 não teve WinError
capturado; não lhe atribuir5 retroativamente. Arquitetura imutável foi validada
APENAS no novo SHA. Último commit documental terá seus próprios checks conferidos.

Local280:218 executados/62 skips; compileall, wheel sem experimento no pacote,
manifesto157 e diff de runtime/ferramentas/extensão/v1/CMD congelados verificados.
22 PRs anteriores mantêm HEAD/base/draft, inclusive32 e6. Sem merge/rebase,
instalação, dados reais, coleta, adapter ou piloto. Evidência é CI Server x64,
não humano10/11, outro token/admin, isolamento de extras ou deadline de driver.

Retomada: revisão independente do SHA final e guards, conforme
SYNTHETIC_PROCESS_SUPERVISION.md; não migrar funções/handles/IPC para runtime.
Flags são monotônicas somente em memória nesta tentativa; sem ledger durável.
API/FS do supervisor ainda pode bloquear. Quarentena armada e dupla morte após
disarm são riscos distintos e não resolvidos. Aguardar revisão do responsável.

## Issue36 — Gate B1 finito, KISS — 2026-11-07

Base EXATA17da1a0fe2ebddb29aca8f2a671a87b3fa814ec6/PR34, nova codex/job-gate-b1.
Issues35/36 e parecer34 lidos. Uma matriz fechada8 células com7 fases, duas mortes
duplas observadas externamente e uma regressão portátil de consulta/lista/race.
Reutilizar negativos base de disarm negado, CloseHandle protegido e Wait sem sinal,
sem reinventar mecanismo. Nenhum src/, launcher, adapter ou integração alterado.
Decisão conservadora explícita: manter OFF Job coletivo incerto (II), sem bulk
termination nem último close armado incerto. Não iniciar nova rodada da hipótese.

JOB_GATE_B1_DECISION.md registra limites e menor plano de integração não executado:
zero runtime novo; estender teste do controlador até CLI analyze/relatório da mesma
SQLite e escrever roteiro de VM sintética. Funções já existem; não criar novo
supervisor/IPC/adapter/minerador. Uma regressão portátil passou; Windows aguarda CI.

### Issue36 — entrega finita concluída no código a577fa9

PR37 draft, base17da1a0 exata. CI42368430074 success5/5, logs dos cinco consultados.
Windows3.11/3.12 cada284 descobertos/282 executados/2 skips browser; Linux219/65
por versão (63 Windows,2 browser), Chromium2/0. Foco novo4/0 nos dois Windows:
matriz8 células e duas mortes duplas +contrato portátil; não contar subcasos/focos
como testes únicos extras. Negativos herdados de disarm/close/wait executados.

Matriz idêntica nos dois Pythons: antes de criar0; suspenso/após resume imediato1
conhecido. Pronto console sem/com descendant:1/2 membros todos conhecidos;
NO_WINDOW sem/com descendant:2/4 membros,1/2 desconhecidos. Ancestral controlado
não alterou padrão; ambient_job=present, não alegar host sem ancestor. Leituras
observadas estáveis/Active concordante, não snapshot atômico. Disarm antes de
fechar, zero consultado e nenhum TerminateJobObject nas novas células; depois de
fechar, contagem não consultável, não zero inventado. Não identificar extras por
correlação nem abrir/terminar PIDs desconhecidos.

Dupla morte armada/suspensa com só conhecido encerrou worker; desarmada/em lock
com extra desconhecido deixou worker VIVO após ambas raízes. Observador externo
com capacidade própria limpou e confirmou saída, nunca como prova de contenção
autônoma. Disarm negado foi somente injetado; Job incerto armado não foi morto.

DECISÃO FINAL II: manter mecanismo coletivo incerto OFF e fora do MVP. Sem nova
hipótese/ciclo nesta tarefa. Marco B permanece limitado, sem liberação operacional.
Plano KISS documentado, NÃO implementado: estender teste existente até CLI analyze
sobre a mesma SQLite +roteiro de VM; zero alterações de runtime se comportamento
já existente passar. Não criar launcher/IPC/adapter/minerador novo para essa fatia.

Local284/219 executados/65 skips, compileall/manifesto160 conferidos. Runtime,
ferramentas/C#, extensão e v1/CMD idênticos à base;23 PRs anteriores preservados.
Nenhum merge/rebase/instalação/captura real/piloto. Última entrega documental terá
CI própria vinculada ao SHA final. Próximo gate é revisão da decisão e plano,
não mais exploração do mesmo mecanismo sem decisão expressa.
