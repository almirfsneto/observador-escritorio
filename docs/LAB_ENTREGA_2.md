> Estado historico da entrega 2. O roteiro atual esta em [LAB_PERSISTENTE.md](LAB_PERSISTENTE.md).

# Entrega 2 — aplicativo ficticio dedicado e controlador visivel

> Somente laboratorio. Este nao e um instalador nem um programa para monitorar
> colaboradores. Nao grava eventos reais, nao usa rede e nao faz screenshots.

## Objetivos implementados

- Aplicativo WinForms em projeto .NET 8 com executavel dedicado
  `SyntheticTaskApp.exe`; campos e operacoes exclusivamente ficticios.
- Controlador Tkinter Windows com quatro acoes visiveis: abrir aplicativo,
  iniciar voluntariamente, pausar/retomar e encerrar.
- Estado inicial desativado; abertura do aplicativo nao habilita observacao.
- Allowlist contendo somente o caminho do executavel ficticio esperado.
- Expiracao automatica de quinze minutos e fim permanente de sessao.
- Consultas UIA em thread separada para manter a interface responsiva.
- Nenhum banco ou arquivo de evidencias e escrito pelo controlador; a linha
  do tempo limitada aparece apenas em memoria e e descartada ao fechar.

## Como executar em um computador Windows de teste

No terminal PowerShell, na raiz deste repositorio, com .NET SDK 8 e Python 3.11+:

```powershell
dotnet build .\tools\SyntheticTaskApp\SyntheticTaskApp.csproj -c Release
python -m pip install -e .
python -m unittest discover -s tests -v
python -m observador.lab_controller
```

1. Verifique que o controlador inicia com "DESATIVADO".
2. Clique em "Abrir aplicativo ficticio": nenhuma captura deve ocorrer.
3. Clique em "Iniciar ensaio". Selecione os botoes, checkbox, campo de texto
   e campo de senha ficticios no outro aplicativo.
4. Volte ao controlador para conferir apenas alias, tipo de controle e horario.
   Nao deve haver conteudo de campo ou senha.
5. Clique em "Pausar", tente interagir, e confirme que o contador nao aumenta.
6. Clique em "Retomar" e depois "Encerrar". A mesma sessao nao pode reiniciar.
7. Feche o aplicativo ficticio e controlador. Verifique ausencia de arquivos
   capturados e de conexoes externas atribuiveis ao laboratorio.

## Limites e verificacoes que ainda faltam

- A API Win32/UIA real deve ser validada em Windows interativo, com evidencias
  saneadas. CI Windows somente compila o exe e valida tests/PowerShell.
- O backend atual inicia um PowerShell por consulta e pode perder acoes rapidas.
- Eventos sao de foco, nao cliques comprovados ou alteracoes reais.
- O filtro de processo se baseia no caminho do executavel; a identidade de
  instancia (PID + hora de criacao) precisa ser vinculada antes de ensaios
  mais amplos.
- Sem screenshots, fila persistente, quota/retencao, instalador, extensao,
  sincronizacao, criptografia ou inicio automatico.
- Ainda nao atende aos gates de piloto nem autoriza observacao de pessoas.
