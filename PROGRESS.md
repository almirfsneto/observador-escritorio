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
