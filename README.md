# Observador Escritorio - Base de desenvolvimento para Codex

**Estado: scaffolding funcional, NAO e um observador Windows instalado ou concluido.**

Este repositório inicia um projeto de descoberta de tarefas repetitivas em computadores Windows utilizados por uma equipe informada sobre o piloto. O núcleo entregue já valida eventos sintéticos, persiste em SQLite, exporta JSONL e detecta sequências repetidas. A instrumentação do Windows, a extensão do navegador e a centralização dos dez computadores ainda devem ser desenvolvidas e testadas.

## Objetivo

Descobrir microtarefas que podem ser simplificadas ou automatizadas, a partir de eventos de interações profissionais (aplicativo ativo, elemento de UI, operações de arquivos, erros e capturas selecionadas), correlacionando-as sem gravar vídeo contínuo.

## Início rápido

Requer Python 3.11+.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m observador demo --db demo.sqlite3
python -m observador analyze --db demo.sqlite3 --out analise.json
python -m unittest discover -s tests -v
```

O modo `demo` usa apenas eventos fictícios. **Nenhuma ação de usuário é capturada por este código inicial.**

## Codex

Leia `AGENTS.md`, `SPEC.md`, `SECURITY.md` e `ROADMAP.md`. Abra `PROMPT_INICIAL_CODEX_OBSERVADOR.txt` e use-o como primeira tarefa do Codex. Registre progresso em `PROGRESS.md`, decisões em `DECISIONS.md` e mantenha a suíte de testes verde.

## Cuidados

- Proibidos: captura secreta, interceptação de senhas, coleta contínua do texto digitado, exposição de dados de clientes ou transferência automática de material bruto a provedores de IA.
- Exigir: ciência dos participantes, operação restrita a expediente/aplicações autorizadas, sinalização visível, pausa, retenção curta e revisão humana antes da exportação à IA.
- O piloto não deve instalar ferramentas nas dez máquinas automaticamente nem alterar sistemas de produção.

## Conteúdo

- `src/observador`: modelo de evento, SQLite, descoberta simples de padrões, CLI.
- `tests`: testes do núcleo inicial.
- `samples`: dados sintéticos.
- `docs`: arquitetura e checklist de piloto.
- `.github/workflows`: CI Linux/Windows.

Licenças de projetos terceiros devem ser verificadas antes de importar qualquer código, inclusive DeskMate, SmartRPA e OpenAdapt. O código deste scaffold é novo; não inclui fontes dos projetos citados.

## Entrega de desenvolvimento — 2026-11-03

Prototipo experimental Win32/UIA e politica de coleta implementados como biblioteca,
com mocks, allowlist, pausa, expediente e expiracao. A CLI continua demonstrativa.
Veja `docs/WINDOWS_LAB.md` para limites e retomada, e
`docs/CAPTURE_ENGINE_REVIEW.md` para comparacao dos motores. Nao validado em Windows
interativo e nao apto a piloto com pessoas.

## Laboratorio persistente e fila sintetica

O controlador experimental agora usa um provider .NET UIA persistente limitado a
instancia ficticia; foco, Invoke e Toggle usam IDs efemeros e nao valores de campo.
Siga `docs/LAB_PERSISTENTE.md`. Gravacao local e opcional e desligada por padrao;
limites e retencao em `docs/LAB_QUEUE.md`. A revisao dos PRs 1/2 esta em
`docs/REVIEW_PRS_1_2.md`. Nao utilizar com pessoas ou dados reais.

## Aceite guiado para operador Windows (Issue 5)

Com Python 3.11+ com Tk e SDK .NET 8 previamente instalados em **máquina dedicada
de teste**, abra `VALIDAR_LABORATORIO.cmd`. Verifique/compile, execute os testes
fictícios, abra o laboratório desativado e inicie o ensaio explicitamente. Preencha
os itens humanos e salve JSON sanitizado fora de Git. O assistente não instala
nada nem faz upload. Veja `docs/VALIDACAO_MANUAL_WINDOWS.md`; CI não substitui
aceite humano e nenhum relatório libera piloto.

## Entregas experimentais posteriores ao assistente

Somente laboratório sintético, ainda sem autorização de piloto:
[armazenamento/ACL/arquivo DPAPI](docs/STORAGE_HARDENING.md),
[diagnóstico WPF/WinForms](docs/WINDOWS_COVERAGE.md),
[extensão MV3 local](docs/WEB_EXTENSION.md) e
[descoberta de microtarefas](docs/TASK_DISCOVERY.md).
O SQLite ativo continua em claro; WinForms permanece com cobertura limitada.
[Retomada autônoma e próximos testes](docs/RETOMADA_AUTONOMA.md).

Issue 11: [diagnóstico fechado e faults sintéticos](docs/DIAGNOSTICS.md),
[ponte offline por arquivos/ACK](docs/OFFLINE_BRIDGE.md) e
[retomada atualizada](docs/RETOMADA_AUTONOMA.md). A ponte não possui socket nem
autenticação de peers/retenção temporal de inbox; continua restrita a laboratório.
