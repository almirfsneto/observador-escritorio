# Laboratorio persistente — somente dados ficticios

Na raiz de um checkout Windows com Python 3.11+ (Tk) e .NET SDK 8:

```powershell
dotnet build tools/SyntheticTaskApp/SyntheticTaskApp.csproj -c Release
dotnet build tools/SyntheticWpfTaskApp/SyntheticWpfTaskApp.csproj -c Release
dotnet build tools/WindowsObserver/WindowsObserver.csproj -c Release
python -m pip install -e .
python -m unittest discover -s tests -v
python -m observador.lab_controller
```

A UI inicia desativada e abre por padrao SyntheticWpfTaskApp. Abrir fixture nao inicia observador. Iniciar cria um unico
processo .NET vinculado ao PID/caminho/instante de criacao da instancia ficticia.
UIA registra assinaturas de foco, Invoke e Toggle; nao ha hook de teclado/mouse,
leitura de Name/Value/Text, screenshot ou clipboard. Somente o processo ficticio
em primeiro plano e aceito. IDs de controles sao hashes de RuntimeId com sal
aleatorio por sessao: nao permitem correlacao entre sessoes.

A timeline mostra acao, papel, identificador efemero e UTC. Pausa limpa filas e
invalida mensagens antigas, inclusive depois de retomar. Fim, expiracao, falta de
heartbeat, fechamento da fixture ou janela encerram a sessao. O encerramento do
provider e limitado e tem fallback de kill. Nao ha reinicio automatico. A janela
exibe fim e perdas; seu texto tem limite de 200 linhas. Dados permanecem somente
em memoria nesta etapa.

## Evidencias distintas

- Linux: testes de contrato, filas, politica, deteccao de sequencias sinteticas;
  compilacao cruzada .NET e possivel, sem executar Win32/UIA.
- Windows CI: compila fixture/provider; testa handshake, rejeicao de identidade,
  EOF, rajada de 2000 eventos artificiais, pausa e expiracao em --protocol-test.
  Esse modo nao assina UIA nem observa desktop.
- Ensaio automatizado de desktop Windows: tests/test_windows_desktop.py abre
  apenas a fixture WPF, invoca botoes a intervalos curtos e verifica exclusao de senha.
  Se o runner nao permite foreground, o teste fica **skipped** com motivo explicito.
  Skip nao comprova captura. Falha de inscricao UIA ou perda de invokes gera falha.
- Validacao humana: executar o controlador, alternar entre as duas janelas,
  pausar/retomar, fechar fixture/controlador e observar responsividade, exclusao de
  senha e limpeza dos processos. Registrar versao Windows, commit, resultados e
  contagens sem prints contendo dados reais. CI nao substitui esse aceite.

Nao utilizar o observador em colaboradores, aplicativos reais ou dados de clientes.
Os PRs permanecem em rascunho e dependem de revisao/autorizacao para merge.

## Cobertura por framework: nao presumir eventos universais

O ensaio inicial de WinForms .NET 8 recebeu foco, mas zero callbacks Invoke, sem
erros/descarte no provider. Inspecao do Button.OnClick no codigo publico do
[WinForms v8.0.0](https://github.com/dotnet/winforms/blob/v8.0.0/src/System.Windows.Forms/src/System/Windows/Forms/Button.cs)
mostrou notificacoes de propriedades nesse caminho, sem garantia de Invoke.
Codigo consultado sob MIT apenas para diagnostico; nenhum trecho importado.
WinForms continua no repositorio para expor essa limitacao. A fixture WPF usa
controles padrao, sem instrumentacao de captura ou emissao artificial de eventos
para o observador. Seu ensaio verifica o caminho UIA Invoke quando o provedor o
oferece. Isso nao demonstra cobertura de cliques de aplicativos WinForms, legados,
navegadores ou sistemas do escritorio. Nao habilitar hooks globais ou ler Name/
valores como atalho para completar essa cobertura.

## Persistencia opcional na entrega seguinte

A caixa de gravacao local inicia desmarcada. Se habilitada, aplica limites e
retencao descritos em [LAB_QUEUE.md](LAB_QUEUE.md); a UI mostra gravados,
descartados e expurgados e pausa em erro. O modo padrao continua somente memoria.
