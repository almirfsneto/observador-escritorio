# Issue36 — Gate B1: investigação finita e decisão

Base exata PR34/17da1a0fe2ebddb29aca8f2a671a87b3fa814ec6. Uma entrega, sem runtime,
sem integração e sem nova linha de experimentação. Ler Issues35/36 e parecer34.

## Decisão técnica e regra de parada

**Manter DESATIVADA a integração do mecanismo de Job coletivo incerto (opção II).**
A prova de um filho suspenso conhecido não autoriza tratar extras como próprios.
Snapshot de membership não congela adições concorrentes. Recuperação externa não
é contenção autônoma após disarm. Não migrar os harnesses para src/, não autorizar
TerminateJobObject/último close armado sobre membros incertos. Não alterar os
launchers existentes neste PR nem afirmar que já foram corrigidos.

Esta é a decisão conservadora apoiada nas limitações já comprovadas da base;
a matriz abaixo a delimita, não é pretexto para perseguir indefinidamente a origem
dos extras. Se as novas observações não comprovarem origem/propriedade, permanece
opção II. Após a CI e revisão desta entrega, PARAR B1. Qualquer novo experimento
exige nova decisão explícita, não continuação automática.

## Experimento mínimo fechado

Oito células predefinidas: sem/com descendant próprio × console/CREATE_NO_WINDOW
(no filho primário e, quando houver, descendant) × sem/com ancestral criado PELO
TESTE. Sem ancestral controlado não significa ausência de ancestral do runner;
registrar ambient_job, sem breakaway nem manipulação do Job do host.

Fases: antes de criar filho; após Job List/CreateProcessW suspenso; antes/depois
do resume; pronto com capacidades conhecidas; antes/depois de fechar Job. Lista
completa limitada16, duas leituras e ActiveProcesses entre elas detectam divergência
observável, não atomicidade. Só GetProcessId de handles retidos; nenhuma abertura
por PID, nome/identidade inferida ou inspeção de membro extra. Desconhecidos só
contados, nunca identificados como conhost/runner/descendant por hipótese.
Depois de fechar, Job não consultável: contagens NULL, sem inventar zero novo.
Zero é provado ANTES do close. Matriz sempre desarma/reconsulta antes do término
por handles próprios e nunca chama TerminateJobObject. Falha de disarm conserva
Job; falha de espera conserva capacidade. Ancestral controlado é desarmado antes
de autorizar criação, mantido aberto até zero e fechado por uma tentativa verificada.

Duas mortes reais com observador externo: observador conserva processos próprios
de ambas raízes e worker, sem reter Job alvo. Primeiro mata a raiz externa, depois
o dono do Job, com capacidades previamente conferidas (imagem/criação/sessão).
EOF não solicita cleanup ao dono; mortes são abruptas sem finally. (a) Worker
suspenso, membership estável e só referência própria: saída por último close
armado. (b) Worker em lock, Job desarmado: esperar sobrevivência por200ms, depois
observador termina APENAS worker conhecido e verifica sinalização. Essa limpeza
não conta como contenção autônoma; não deixa órfão deliberadamente. Não provocar
morte real de Job incerto armado para testar disarm negado.

Negativos novos: erro/truncamento/duplicatas/race da lista. Reutilizar os negativos
já presentes do PR34 na suíte completa: NativeBackendInjectionTest para disarm
negado/quarentena; WindowsProcessSupervisionTest para CloseHandle realmente
protegido e Wait não sinalizado INJETADO sobre recursos reais. Não reimplementar
essas mesmas provas. Modelo/falhas injetadas não são falha espontânea de kernel.

Budgets de teste: leitura de controle10s, startup8s, fixture simples limitada10s,
comunicação de célula30s (startup + vida limitada + cleanup); esperas2s e prova de
morte5s, janela de sobrevivência200ms. Não são deadline global de driver/FS/API;
não ampliar para obter verde. Somente processos e arquivos sintéticos próprios.

## Convergência ao Marco B do plano35

B1 entrega uma decisão, não aprovação de B2/B3/B4. Se origem continua desconhecida,
Job coletivo fica FORA do MVP e não é controle de segurança. Nem shutdown limpo
pontual nem CI substituem governança/aceite humano10/11, outros tokens, AI04/LGPD.
Não propor novo supervisor/serviço/IPC nesta entrega. Contenção automática de falha
dupla e autenticação do provider C# continuam não comprovadas.

## Menor próximo conjunto para a fatia fictícia (NÃO implementado)

A maior parte JÁ existe: LaboratoryWindow/NativeSession coletam somente fixture
WPF própria; AsyncLabQueue grava SQLite; test_windows_controller verifica30 Invoke
persistidos; test_windows_desktop já executa SQLite→discover_patterns. CLI existente
`python -m observador analyze --db ... --out ...` grava relatório JSON de candidatos.
Portanto não é necessário criar novo launcher, adapter, IPC ou minerador para
completar essa fatia sintética. Usar detector simples já compatível, sem prometer
mineração entre sessões ou causalidade. Não habilitar task_discovery genérico via
projeção ad hoc apenas para aumentar escopo.

Menor entrega futura: **dois arquivos**:
1. Estender tests/test_windows_controller.py: depois de flush/encerramento e leitura
   verificada da MESMA SQLite, chamar CLI analyze existente para relatório temporário
   fora de Git; validar JSON, recorrências, duração, aviso de revisão humana e
   ausência de valores/senha. Incluir pausa/expiração/limpeza sem Job coletivo,
   sem chamar ensaio skipped de aprovado. Não mudar o runtime para cumprir esse teste.
2. Um roteiro curto de operação em VM Windows10/11 dedicada: iniciar laboratório
   desativado, marcar persistência fictícia, executar sequência WPF, pausar/encerrar,
   conferir limpeza e executar analyze; registrar SHA/hash/contagens/relatório local.

**Alterações mínimas de runtime: zero**, desde que o teste confirme o comportamento
já existente. Se falhar, corrigir SOMENTE o ponto demonstrado em nova entrega
revisável, sem aproveitar para migrar Jobs ou canais. Os caminhos legados de
Popen/cleanup têm limites e não ganham garantia de crash por não usar Job coletivo;
ensaio supervisionado e processos próprios conhecidos são premissas obrigatórias.
SQLite ativo em claro, quota não física, IPC C# não autenticado e controles humanos
impedem dados reais/piloto. Fora do MVP1: screenshots, web, centralização e equipe.
Não copiar coleta real para esta fatia nem transferir aceite histórico do PR6.

## Evidência desta entrega

Até CI do SHA: uma regressão portátil passou, três testes Windows preparados
(matriz de oito subcasos e duas mortes duplas). Skips Linux não são provas nativas.
Resultados, SHA e CI finais em PROGRESS e PR da branch codex/job-gate-b1.
