# Aceite humano pendente — laboratorio Windows 10/11

Executar somente em VM/computador de teste dedicado, com dados ficticios, sem
instalar o observador nos computadores da equipe. CI automatizada nao substitui
este aceite. Nenhum item abaixo autoriza piloto com pessoas, deploy ou merge.

## Preparacao

Usar a branch do PR4 e o roteiro de build em [LAB_PERSISTENTE.md](LAB_PERSISTENTE.md).
Registrar commit, edicao/build do Windows, versoes de Python/.NET e hashes dos dois
executaveis usados, sem hostname, nomes pessoais ou caminhos de clientes. Repetir
o roteiro em Windows 10 e 11 suportados pelo runtime; guardar resultados locais.

```powershell
git rev-parse HEAD
python --version
dotnet --list-runtimes
(Get-FileHash tools/WindowsObserver/bin/Release/net8.0-windows/WindowsObserver.exe -Algorithm SHA256).Hash
(Get-FileHash tools/SyntheticWpfTaskApp/bin/Release/net8.0-windows/SyntheticWpfTaskApp.exe -Algorithm SHA256).Hash
python -m unittest discover -s tests -v
python -m observador.lab_controller
```

## Registro de aceite

| Verificacao | Resultado esperado | Windows 10 | Windows 11 |
| --- | --- | --- | --- |
| Abrir controlador | DESATIVADO; persistencia desmarcada; sem provider de captura | Nao executado | Nao executado |
| Abrir fixture pelo botao | Aplicativo ficticio visivel; ainda sem observador/eventos | Nao executado | Nao executado |
| Iniciar explicitamente | Estado ATIVO apos ACK, data fim visivel; so instancia lancada | Nao executado | Nao executado |
| Alternar botoes WPF rapidamente | Acoes distintas, repeticoes preservadas; sem conteudo dos campos | Nao executado | Nao executado |
| Campo de senha ficticio | Nenhum evento de foco da senha nem valor em timeline/SQLite | Nao executado | Nao executado |
| Segunda instancia da mesma fixture, aberta separadamente | Interacoes nela nao aumentam o contador; fechar essa instancia manualmente | Nao executado | Nao executado |
| Pausar e interagir na fixture original | Nenhum novo evento aceito; PAUSANDO ate ACK, depois PAUSADO; sem replay ao retomar | Nao executado | Nao executado |
| Persistencia opt-in | Somente eventos projetados em lab-data; gravados/descartados/expurgados visiveis | Nao executado | Nao executado |
| Expiracao de 15 minutos | Sessao termina; nao reinicia na mesma janela; provider/fixture possuidos encerrados | Nao executado | Nao executado |
| Fechar fixture ou controlador | Fim permanente e ausencia de processos filhos orfaos; banco integro | Nao executado | Nao executado |
| Responsividade e custo | Registrar CPU/RAM dos processos ficticios e latencia percebida, inclusive ao pausar | Nao executado | Nao executado |

Nao e necessario capturar screenshots ou video. Registrar apenas versoes, hashes,
contagens, tempos e resultados. Arquivos de ensaio sao ficticios; nao importar dados
reais para enriquecer o teste. WinForms permanece com limitacao observada de Invoke;
WPF nao demonstra compatibilidade com todos os aplicativos profissionais.

Depois do aceite: anexar relatorio saneado a nova entrega, comparar perda/overhead
com os objetivos e decidir sobre melhorias de cobertura por aplicativo. Cifragem,
ACL Windows, retencao com agente desligado, cota total de disco, instalador/tray,
revisao independente e gates juridicos do piloto continuam pendentes. Nao expandir
para colaboradores ou sistemas do escritorio com base apenas no CI.
