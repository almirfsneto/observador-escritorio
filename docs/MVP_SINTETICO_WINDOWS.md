# Fluxo fictício ponta a ponta — VM Windows

Somente VM dedicada Windows 10/11, sem aplicativos, contas ou dados profissionais.
Use checkout Git confiável desta entrega, Python 3.11/3.12 com Tk e SDK .NET 8
com Windows Desktop previamente preparados pelo TI, sessão interativa desbloqueada
e usuário comum. Não instalar na equipe. B1 está encerrado: Job coletivo incerto
continua fora da integração; não executar novos experimentos nem ativar adaptador.

## Preparar e conferir o ensaio automático

Na raiz do checkout, no PowerShell (não é necessário instalar o pacote Python):

```powershell
git rev-parse HEAD
git status --short
python --version
dotnet --version
$env:PYTHONPATH = 'src'
dotnet build tools/SyntheticWpfTaskApp/SyntheticWpfTaskApp.csproj -c Release
dotnet build tools/WindowsObserver/WindowsObserver.csproj -c Release
python -m unittest discover -s tests -p test_windows_controller.py -v
```

Se faltar dependência ou houver bloqueio de política/desktop, parar e registrar;
não elevar, instalar ou contornar políticas. O teste abre somente a fixture WPF
e o controlador, aciona dois botões 15 vezes cada e verifica pausa, retomada,
pausa por falha de armazenamento INJETADA, fila e término dos processos próprios.
Após o escritor terminar e as conexões fecharem, chama a CLI REAL sobre a MESMA
SQLite temporária. Não usa `demo` nem exige 36 eventos.

`SYNTHETIC_CONTROLLER_ANALYSIS` registra somente contagens e confirmações:
30 Invoke, padrões, CLI zero, mesma SQLite inalterada, escritor encerrado e
checagens de conteúdo. A suíte também imprime `SYNTHETIC_CONTROLLER_COUNTS`.
JSON/SQLite temporários são apagados pelo teste; não são anexados ao CI.
`skipped` por foreground indisponível significa **NÃO EXECUTADO**, mesmo com
`OK (skipped=...)`. Sem marcador e aprovação do caso, não há prova ponta a ponta.

## Ensaio humano separado

1. Em checkout exclusivo de laboratório, conferir que `lab-data/events.sqlite3`
   ainda não existe. Se existir, não misturar sessões: preservar localmente o
   ensaio anterior e usar outro checkout limpo. Não apagar evidência de falha.
2. Executar `python -m observador.lab_controller`. Confirmar DESATIVADO e opção
   de persistência desmarcada. Clicar **1. Abrir aplicativo fictício**: ainda não
   deve haver observação. Marcar **Salvar eventos fictícios locais**, então
   **2. Iniciar ensaio**; aguardar ATIVO.
3. No aplicativo WPF, alternar **Salvar ficticio / Revisar ficticio** 15 vezes
   (30 ações), aguardando os contadores estabilizarem. Não digitar conteúdo novo;
   os campos já contêm apenas canários fictícios. Registrar timeline/gravados,
   descartes, perdas de fila e lacunas; foco pode acrescentar eventos.
4. Clicar **Pausar**, aguardar PAUSADO e repetir algumas ações: contadores não
   devem aumentar. Clicar **Retomar**, aguardar ATIVO, sem novas ações antes de
   encerrar se desejar conservar os 30 Invoke. Limite da sessão: 15 minutos;
   expiração exige novo ensaio, não reinicia o atual.
5. Clicar **Encerrar**, aguardar o escritor/processos próprios terminarem e fechar
   o controlador. Não analisar enquanto grava. Verificar fechamento da fixture e
   do provider; em Gerenciador de Tarefas comparar apenas os processos desta VM
   identificados localmente ao abrir o ensaio. Janela fechada sozinha não prova
   cleanup: dúvida, sobrevivência ou aviso **limpeza nao confirmada** = FALHOU/
   NÃO CONFIRMADO. Não terminar processos por nome genérico nem alegar contenção
   de crash; o teste automático verifica saída pelos processos retidos.

## Gerar e inspecionar o relatório local

Logo após encerrar (retenção da fila: uma hora), na mesma raiz/terminal:

```powershell
# Leitura somente; imprime contagens, nunca eventos ou valores.
python -c "import sqlite3,json; c=sqlite3.connect('file:lab-data/events.sqlite3?mode=ro',uri=True); r=c.execute('SELECT payload_json FROM events').fetchall(); print({'events':len(r),'invoke':sum(json.loads(x[0])['action']=='invoke' for x in r)}); c.close()"
if ($LASTEXITCODE -ne 0) { throw 'Falha ao conferir SQLite; parar' }
$destino = Join-Path $env:LOCALAPPDATA ('ObservadorEscritorio\mvp-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $destino -ErrorAction Stop | Out-Null
$relatorio = Join-Path $destino 'analise.json'
python -m observador analyze --db lab-data/events.sqlite3 --out $relatorio
if ($LASTEXITCODE -ne 0) { throw 'Analyze falhou; nao considerar aprovado' }
$padroes = @(Get-Content -Raw -Encoding UTF8 $relatorio | ConvertFrom-Json)
$padroes | Select-Object occurrences, median_duration_seconds, confidence_note
Get-FileHash -Algorithm SHA256 lab-data/events.sqlite3
Get-FileHash -Algorithm SHA256 $relatorio
```

O diretório de destino deve ficar fora de qualquer Git. Inspecionar JSON localmente:
lista não vazia, passos de ação/alias/ID efêmero, `occurrences >= 3`,
`median_duration_seconds >= 0` e nota `requer revisao humana`. Nenhum valor do
formulário, senha fictícia ou legenda de botão pode aparecer. São candidatos
temporais com sobreposição possível, não causalidade, produtividade ou economia.
`analyze` cria banco vazio se caminho estiver errado: conferir existência e
contagens ANTES. Um relatório vazio não satisfaz este ensaio.

Guardar fora de Git: SHA e estado limpo/modificado, edição/build Windows,
Python/.NET, resultados e skips com motivos, contagens/saúde, hashes e JSON
EXCLUSIVAMENTE sintético. Registrar PASSOU/FALHOU/NÃO EXECUTADO separadamente
para automação e observação humana. Em falha, registrar etapa e categoria
(desktop, build, armazenamento, pausa, limpeza, análise, conteúdo); não copiar
exceções brutas, usuário, caminhos pessoais, PID, prints ou banco para issues.
Relatório não é anonimização universal: não enviar arquivos automaticamente.

CI Windows Server não substitui aceite humano Windows 10/11. SQLite ativo em
claro, quota lógica, IPC C# não autenticado e limites de cleanup/crash permanecem.
Nenhum resultado libera dados reais, instalação na equipe ou piloto. Encerrar
esta tarefa após revisão das evidências; não iniciar outra automaticamente.
