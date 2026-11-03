# Prototipo de laboratorio: estado e retomada

O nucleo `collector.py` aplica allowlist por caminho absoluto do executavel,
aliases ficticios, horario local de um relogio com fuso, inicio/fim, pausa e parada
definitiva ao expirar. O backend Windows consulta Win32 antes de UIA e rejeita
processos nao permitidos, foco de outro processo, senha, troca de janela e erros.
O resultado preserva apenas indice do aplicativo, tipo do controle e flag booleana
de senha. Eventos persistiveis usam alias, papel e acao `focus`, sem nomes ou
titulos. Foco nao prova clique, edicao ou conclusao de uma tarefa.

Nao existe comando de captura real na CLI. `laboratory_enabled` inicia falso.
Este modulo e uma biblioteca experimental, sem loop autonomo, indicador visual,
autoarranque ou instalador. Nao habilitar em computadores de colaboradores.

## Validacao automatica

```powershell
python -m pip install .
python -m unittest discover -s tests -v
```

CI configurada para Ubuntu e Windows, Python 3.11/3.12. Mocks nao comprovam UIA
real. O workflow tambem analisa a sintaxe dos scripts no Windows sem coleta.
As quatro combinacoes passaram no commit `f48b31e`; evidencia em `PROGRESS.md`.

## Aplicativo ficticio para o proximo teste Windows

```powershell
powershell.exe -NoProfile -File tools/synthetic_windows_app.ps1
```

Abre formulario WinForms com texto e senha ficticios, botao e aviso de ausencia
de coleta. Fechar a janela encerra o formulario. Nao grava nem transmite dados.
Respeitar a politica de execucao do Windows; nao contorna-la automaticamente.

**Importante:** o formulario roda dentro de PowerShell. Nao permitir genericamente
`powershell.exe` no coletor: outras janelas do mesmo executavel tambem entrariam.
Antes do ensaio integrado, converter o formulario em executavel dedicado ou
adicionar vinculacao segura de PID + instante de criacao do processo de teste.

## Proxima entrega objetiva

1. Criar executavel ficticio dedicado e runner de laboratorio visivel, inicialmente
   pausado, com botoes de pausa/fim e data de expiracao; nao iniciar coleta antes
   da janela existir. Ensaio estritamente sintetico, sem instalar em maquinas reais.
2. Integrar fila SQLite com cota de disco, retencao e estado de saude; impedir que
   atraso do backend prejudique a pausa. A consulta atual pode levar ate 8s.
3. Exercitar foco em botao/edicao/senha, troca para app negado, acesso negado,
   timeout e expiracao em Windows 10/11. Arquivar evidencias saneadas.
4. Medir perda e custo. Hoje ha deduplicacao por aplicativo/papel: controles do
   mesmo papel nao sao distinguiveis e polling pode perder transicoes curtas.
5. Somente depois adicionar acoes UIA, screenshot seletiva com mascaramento,
   indicador tray, autoarranque opt-in e desinstalacao.

Pendencias adicionais: schema existente aceita strings livres nos campos e valores
de metadata; a projecao nova e fechada, mas o contrato geral ainda precisa de
hardening antes de ingestao externa. SQLite nao e criptografado; export JSONL da
CLI e demonstrativo, nao sanitizador de dados reais. Nenhum gate de piloto mudou.
