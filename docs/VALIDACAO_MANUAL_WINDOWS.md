# Aceite guiado Windows 10/11 — somente laboratório

**Não está liberado para piloto.** Use uma VM/computador dedicado de teste, nunca
computador de colaborador nem aplicativos/dados do escritório. Testes automáticos
não substituem a execução humana abaixo, separadamente em Windows 10 e Windows 11.

## O que o TI entrega antes

Uma cópia confiável desta branch (com a pasta `tools`), Python 3.11 ou superior
**com Tk** e **SDK .NET 8** com os packs Windows Desktop já instalados. O assistente
não instala dependências, não pede administrador, não altera registro/startup e
não contorna política de execução. Se faltar algo, peça ao TI para preparar a VM.
Git é opcional para rodar; sem metadados Git disponíveis, o relatório registra a
lacuna de commit e não inventa uma revisão. Use checkout Git para evidência completa.

## Quatro passos para o operador

1. Na pasta do projeto, dê dois cliques em **VALIDAR_LABORATORIO.cmd**.
   Alternativa no terminal: `python tools/validar_laboratorio.py`.
   A coleta inicia **DESATIVADA**. Nenhuma fixture/provider é aberta nesta etapa.
2. Na aba **1. Preparação**, clique em **Verificar e compilar**. O assistente
   verifica Python/Tk/SDK 8, compila offline e calcula SHA-256 do app fictício e do
   observador (incluindo suas DLLs/configurações). Não usa pip, não baixa pacotes.
   Depois clique em **Executar testes automáticos fictícios**: esse botão autoriza
   explicitamente testes que podem abrir somente fixtures/providers de teste.
   Aguarde PASSOU. Falha fica registrada; não instale/force nada para contorná-la.
3. Na aba **2. Ensaio**, abra o laboratório. Na nova janela clique em **Abrir
   aplicativo fictício**, depois **Iniciar ensaio**. Só esse clique inicia coleta
   daquela instância, por no máximo 15 minutos. Os dados já preenchidos são falsos.
   Faça as verificações da tabela. Para ensaiar fechamento/expiração, abra novo
   ensaio depois de encerrar o anterior; limite de seis por assistente.
4. Feche/encerre todos os ensaios e aguarde a limpeza. Na aba **3. Avaliação
   humana**, marque **PASSOU / FALHOU / NÃO EXECUTADO**, com observação padronizada.
   Na aba **4. Relatório**, clique em **Salvar relatório sanitizado local**.
   A tela mostra o arquivo. Ele fica em `%LOCALAPPDATA%\ObservadorEscritorio\aceites`,
   fora de Git. Nenhum upload ocorre. Revise o JSON antes de compartilhá-lo por
   iniciativa própria. Também é possível salvar um relatório de falha/incompleto.

## Verificações realmente humanas

| Item no assistente | O que observar |
| --- | --- |
| Interface | Estado legível e janela responsiva; sem captura antes de iniciar |
| Início/fim | Início explícito, estado ATIVO após ACK e data de fim visível |
| Ações rápidas | Alternar Salvar/Revisar e conferir ações distintas, sem valores de campos |
| Segunda instância | Abrir pelo botão próprio; interagir nela não aumenta contador da primeira |
| Pausa/retomada | PAUSANDO até confirmação, depois PAUSADO; sem novas ações aceitas nem replay ao retomar |
| Senha | Usar apenas senha fictícia; nenhum conteúdo ou foco de senha na timeline |
| Limpeza | Fechar fixture/controlador encerra os processos próprios, sem órfãos |
| Latência | Avaliar visualmente se há lentidão/travamento; selecionar observação padronizada |
| Expiração | Aguardar os 15 minutos: fim permanente, sem reiniciar na mesma janela |
| Persistência | Opt-in desmarcado por padrão; se habilitado, verificar contadores/estado e SQLite fictício |

Não há texto livre para observações: isso evita transcrever nomes, senhas, caminhos
ou títulos de telas. Se a categoria não descrever um problema, escolha **Outro
problema: requer revisão**. Não anexe print, vídeo, log bruto ou base real. NÃO
EXECUTADO é válido e não se transforma em PASSOU por causa do CI.

## O que as medidas significam

- CPU: maior taxa **amostrada** por diferença de tempo de CPU/tempo decorrido,
  expressa como percentual de um núcleo; threads podem somar mais de 100%.
- RAM: maior working set observado e pico de working set informado pelo Windows;
  este último cobre toda a vida daquele processo, não somente o ensaio.
- Amostras tentadas a cada 500 ms: picos entre amostras podem não aparecer.
  Somente controlador, fixture, provider e segunda fixture abertos pelo assistente;
  não há enumeração de processos de colaboradores. PID/nome de processo não entram
  no relatório. `null`/`not_sampled`/`unavailable` não significam custo zero.
- Início: tempo do clique de iniciar até o ACK ativo observado pelo controlador.
  A chamada de lançamento da fixture mede criação do processo, não renderização.
- Pausa: maior tempo pedido→ACK observado no loop do controlador. Pedido trocado
  ou encerrado antes do ACK fica não confirmado; não se inventa latência.
- Responsividade/latência percebidas continuam humanas, separadas desses números.
  Contadores de fila não provam que o provedor UIA entrega todo evento de foco.

## Conteúdo e limites do JSON

Schema em [ACEITE_REPORT_SCHEMA.json](ACEITE_REPORT_SCHEMA.json). Contém somente
edição/build do OS por allowlist, versões, commit/flag de modificação, hashes,
status/observações enumeradas e agregados. Não inclui hostname, usuário, IP,
pastas, títulos, eventos individuais, conteúdo de formulário, senha ou imagem.
Campos extras/valores livres são rejeitados antes de criar arquivo.

`human_gate` permanece **PENDENTE_REVISAO_HUMANA** mesmo que todos os itens sejam
marcados PASSOU: é declaração do operador a revisar. CI usa `origin=automated_test`.
`pilot_authorized` é sempre falso. Lacunas de dependências, métricas, commit,
testes, OS e ausência de verificação instrumentada de rede ficam explícitas.

A ausência de rede de outros processos não é monitorada. O código não faz upload;
a compilação elimina fontes NuGet e desativa telemetria/avisos de workload, sem
prometer auditar tráfego do Windows/SDK inteiro. Frameworks variam: WinForms
.NET 8 teve cobertura limitada de Invoke; a fixture WPF não representa todos os
aplicativos profissionais. Cifragem/ACL/cota total de filesystem e expurgo com
programa desligado continuam tarefas separadas. Não instalar, fazer deploy,
integrar PRs ou observar pessoas com base neste relatório.

## Interpretação após a estabilização filha do PR18

O PR6 permanece congelado: não atualizar sua branch nem editar seu JSON histórico.
Na versão nova, PASSOU de testes significa somente os executados; a tela informa
quantos foram ignorados. Todos ignorados ou resumo desconhecido falham. Guarde o
relatório v1 e o diagnóstico complementar fora de Git. Um erro do complemento
não apaga o v1 já salvo; a tela informa a falha parcial. Não enviar JSON para o
repositório. Consulte ACCEPTANCE_MATRIX.md para separar versão/OS e CI de humano.

Sem Git na raiz, commit é desconhecido (ZIP não comprova SHA). Uma sessão iniciada
e avaliada manualmente registra execução declarada no OS atual e remove só o gap
de execução desse OS; isso não aprova o ensaio nem o piloto. Descarte nativo acima
de zero e skips precisam revisão. O diagnóstico não atribui causa ou taxa ao
descarte e não confirma amostra final de saúde. Se precisar repetir, usar apenas
o app fictício em máquina de laboratório autorizada, com indicador visível.
