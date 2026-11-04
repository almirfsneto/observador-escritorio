# AI-03 — estudo de arquitetura e teste isolado, sem integração

Base: codex/legacy-binding-cleanup (PR23), filha do PR21. Experimento somente em
tests/isolated_suspended_spawn.py e test_suspended_study.py, fora do pacote runtime.
CommandRunner e OwnedSyntheticChannel continuam usando o launcher anterior;
não há correção de contenção pré-assign integrada ou adapter habilitado.

## Comparação de alternativas

| Alternativa | O que pode demonstrar | Limite aberto |
| --- | --- | --- |
| Popen→assign atual | Job após associação, kernel membership/teardown | Execução e spawn antes do assign; morte do launcher nesse intervalo |
| CreateProcessW suspenso→assign→verify→resume | Thread primária da fixture não executa antes de associação verificada | Morte do launcher ANTES do assign pode deixar filho suspenso fora do Job próprio |
| Job na criação, via STARTUPINFOEX/JOB_LIST | Candidato para associação na própria criação | Disponibilidade nos OS alvo, contratos Win32, limites e falhas ainda não exercitados |
| Broker externo | Pode manter capacidade/cleanup fora do launcher | Acrescenta processo de confiança/lifetime/protocolo; não implementar serviço ou instalação por inferência |

Decisão: estudar a sequência suspensa em fixture sintética, sem promovê-la ao
launcher em uso. Suspensão sozinha não elimina a janela de lifetime. Avaliar
PROC_THREAD_ATTRIBUTE_JOB_LIST para futura associação na criação; não alegar
atomicidade/compatibilidade antes de implementar e provar. Mesmo token/admin,
injeção de código, loader hostil e checkout adulterado não são fronteiras cobertas.

## Experimento preparado

CreateProcessW fixa sys.executable -I -S e um script próprio: cria descendente
inerte, grava um byte sintético exclusivo no diretório temporário e espera. Usa
CREATE_SUSPENDED/CREATE_NO_WINDOW/ambiente mínimo, bInheritHandles=false e stdio
nulos; não lê apps, DOM, textos, rede, usuário ou dados reais. Job mantém
KILL_ON_JOB_CLOSE. Resume só após IsProcessInJob confirmar associação, com contagem
anterior de suspensão igual a1. Decoy de pipe herdável é sondado como objeto do
kernel, nunca por validade do número do slot. Cleanup tenta Job, processo e
ambos os handles mesmo em falha, com CloseHandle verificado.

Quatro casos Windows preparados:
1. Fixture bloqueada antes do resume, membership verificada, decoy não herdado,
   marker posterior e pai/descendente confirmados zerados no Job.
2. Exceções controladas antes/depois do assign e retornos de membership/resume
   INJETADOS; recursos são reais, mas as falhas nesses callbacks são simulações.
3. Morte real do launcher DEPOIS do assign, ANTES do resume; esperar término do
   filho por kill-on-close sem finally do launcher.
4. Morte real ANTES do assign; esperar filho ainda suspenso e marker ausente,
   demonstrando o limite arquitetural. Teste raiz conserva capacidade do filho,
   confirma estado e o encerra/libera. Nunca deixar o processo para limpeza humana.

O slot comunicado privadamente pelo launcher só localiza um handle dentro do
Popen próprio retido. A raiz duplica essa capacidade, verifica objeto de processo
e aguarda/encerra por handle; não abre PID. Esse tráfego fica em pipes de teste,
sem chaves/identificadores no log ou relatório. Antes de obter a capacidade, erro
do harness solicita cleanup cooperativo ao launcher, com prazo.

## Evidência real nesta execução e bloqueios

**Os quatro casos Windows NÃO executaram nesta sessão.** Foram escritos, importados
no Linux (skipped por plataforma) e compilados; nomes REAL/prints nos testes são
emitidos somente se futuramente executados e não representam prova presente.
CI completa está sendo solicitada, mas PR23 falhou antes das etapas nos cinco
jobs, inclusive após reexecução controlada; causa administrativa não disponível.
Não inferir resultado nativo de análise, Linux ou CIs de SHAs anteriores.

Antes de integração: restaurar CI; executar casos nos dois Pythons Windows;
revisar SHAs; resolver a janela de morte pré-assign por mecanismo adequado;
provar abort/falhas de criação/atribuição/resume, handles mínimos, ausência de
órfãos e coexistência com Job externo. Só depois considerar proposta separada
para os launchers, com regressões de herança/chave/identidade do PR18 e preparo.
AI-04, revisão humana, Win10/11 da candidata e demais gates continuam abertos.
