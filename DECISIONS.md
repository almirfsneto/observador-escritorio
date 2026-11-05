# Log de decisoes

## D-001 - Repositorio independente
- **Decisao:** Scaffold criado sem importar codigo de DeskMate/SmartRPA/OpenAdapt.
- **Motivo:** verificacao de licenca e seguranca deve preceder integracao.
- **Revisar se:** comparacao de bibliotecas comprovar melhor opcao.

## D-002 - Captura de eventos, nao video
- **Decisao:** metadados de atividades e prints seletivos, sem video continuo.
- **Motivo:** cinco ou mais dias de trabalho, custo de armazenamento e pesquisa.

## D-003 - Privacidade por padrao
- **Decisao:** nao capturar texto integral de entrada, credenciais nem clipboard.
- **Motivo:** estes dados nao sao necessarios para reconstruir procedimentos e criam risco elevado.

## D-004 - Analise inicial deterministica
- **Decisao:** detector basico de sequencias sobre eventos ficticios.
- **Motivo:** criar contrato testavel antes de componentes IA.

## D-005 - Prototipo Win32/UIA sem dependencia Python adicional
- **Decisao:** ponte PowerShell/.NET original, com timeout, consulta pontual e nenhuma leitura de Name/Value/Text, titulos, teclas ou clipboard.
- **Alternativas:** OpenAdapt, SmartRPA e candidato Deskmate; evidencias e limites em `docs/CAPTURE_ENGINE_REVIEW.md`.
- **Riscos:** processo PowerShell por consulta e lento; sem validacao Windows, eventos de acao ou identificacao de controles iguais. Nao usar em piloto; avaliar provedor persistente apos laboratorio.

## D-006 - Politica fechada e integracao progressiva
- **Decisao:** habilitacao de laboratorio falsa por padrao, allowlist por executavel absoluto, aliases, relogio injetavel com fuso, pausa, expediente e expiracao rechecados depois do backend. Foco gera apenas evento de foco.
- **Alternativas:** ativar loop na CLI ou liberar executaveis por nome. Rejeitadas nesta etapa: ainda faltam indicador visivel e isolamento do app ficticio.
- **Riscos:** ponte interna nao e uma fronteira contra codigo local malicioso; ainda faltam autenticacao de configuracao, acesso local, cota e retencao. Nenhuma captura real foi autorizada ou executada.

## D-007 - Evidencias de CI separadas de testes locais
- **Decisao:** adicionar workflow ausente para Linux/Windows e Python 3.11/3.12, com dados sinteticos e parsing PowerShell. Registrar execucao remota somente quando houver resultado verificavel.
- **Alternativa:** inferir compatibilidade Windows a partir de mocks Linux. Rejeitada por nao demonstrar APIs nativas nem UI interativa.

## D-008 - Laboratorio sintetico dedicado e observador visivel
- **Decisao:** usar projeto WinForms .NET 8 que gera SyntheticTaskApp.exe e controlador Tkinter que inicia desativado, exige acao explicita, limita o alvo ao binario ficticio do repositorio e expira em quinze minutos.
- **Motivo:** separar laboratorio de maquinas e aplicativos reais; eliminar o risco de permitir genericamente powershell.exe utilizado no formulario anterior.
- **Limites:** nenhum evento gravado, nenhuma rede, nenhum print; ainda falta verificar Win32/UIA numa sessao Windows real. A comparacao por caminho de executavel nao valida isoladamente identidade/assinatura do binario nem associa uma instancia por PID. Testes CI nao provam captura interativa.

## D-009 - Provider UIA persistente e isolado por instancia
- **Decisao:** processo .NET 8 original, assinaturas UIA de foco/Invoke/Toggle e filtro de PID/caminho/instante de criacao. RuntimeId salgado e efemero diferencia controles sem nomes ou valores.
- **Alternativas:** polling PowerShell mais rapido ou hooks globais. Rejeitados pelo overhead/perda e pela superficie de coleta. Provider nao importa codigo de terceiros.
- **Riscos:** entrega UIA nao garantida, chamadas de provedor podem travar, comportamentos variam por Windows. Watchdog monotono/heartbeat/EOF e encerramento limitado reduzem orfaos; ensaio humano permanece obrigatorio.

## D-010 - Pausa com geracoes, buffers limitados e evidencias separadas
- **Decisao:** LabStream sincronizado invalida buffers ao pausar; tokens impedem retorno de eventos antigos. Filas 512/256, texto 200 linhas, contadores de perda. UI nao espera leitura de UIA ou escrita em pipe.
- **Alternativas:** reutilizar Collector compartilhado entre threads ou manter eventos de pausa para exibir depois. Rejeitadas por condicao de corrida e semantica de pausa.
- **Validacao:** protocolo nativo artificial e desktop sintetico sao testes distintos. Ausencia de foreground marca o ensaio como skipped e nao como captura aprovada. Nenhum resultado autoriza piloto ou merge.

## D-011 - Endurecer contrato de metadata e caminhos
- **Decisao:** valores de metadata enumerados/faixas numericas, sem objetos arbitrarios; rejeitar NaN, booleano como numero e caminhos screenshot Windows/UNC enraizados.
- **Risco:** entradas antigas fora dos dominios agora falham explicitamente. Campos textuais gerais continuam exigindo projecao fechada: validar schema nao equivale a anonimizar qualquer dado externo.

## D-012 - Fila sintetica opt-in fora da thread da interface
- **Decisao:** SQLite local opcional, desligado por padrao, 4 MiB de banco principal/10 mil eventos/TTL 1h; projecao fechada, secure_delete, um escritor e fila de 16 lotes de ate 100. Erro de armazenamento pausa captura e conta rejeicoes.
- **Alternativas:** gravar por padrao, bloquear UI em disco lento ou descartar silenciosamente. Rejeitadas por transparencia, responsividade e qualidade da evidencia.
- **Limites:** journal e filesystem nao estao sob cota total; sem cifragem/ACL Windows revisada. Expurgo enquanto programa ativo e na reabertura, nao enquanto desligado; nao promete apagamento forense. So dados ficticios ate validacao humana e gates completos.

## D-013 - Cobertura UIA por provedor, cache minimo e evidencia real sintetica
- **Decisao:** manter WinForms para explicitar limite observado (foco recebido, nenhum Invoke nesse caminho) e usar controles WPF padrao para o ensaio de acoes. Nenhuma instrumentacao especial emite eventos para o observador.
- **Evidencia:** CI no commit c4ca6cf recebeu 30/30 Invoke em dois botoes WPF, sem descartes de fila e com exclusao de senha, em Python 3.11 e 3.12. Isso nao demonstra captura de cliques WinForms nem outros aplicativos.
- **Arquitetura:** notificacao global de foco solicita apenas PID em cache; somente depois de filtrar a instancia uma thread MTA consulta papel, flag de senha e RuntimeId. Eventos de acao sao restritos a subtree e usam cache dessas propriedades, evitando consultas reentrantes no callback. Filas e geracoes continuam limitadas.
- **Alternativas:** tratar ausencia de Invoke como ausencia de trabalho, ler nomes/valores para inferir cliques ou usar hooks globais. Rejeitadas por qualidade e privacidade. Validacao humana Windows 10/11 e medicao de overhead/perda seguem pendentes.

## D-014 - Aceite do controlador separado de testes nativos e de aceite humano
- **Decisao:** testar Tk visivel com loop de mensagens ativo, provider real, fixture padrao e SQLite temporario, preservando estado inicial desativado, ACK de pausa e limpeza de filhos. Caminhos sao injetaveis para testes do wheel; o comando normal mantem defaults do checkout e nao aceita outros apps pela CLI.
- **Evidencia e limite:** 55 testes Windows aprovados na matriz 3.11/3.12; captura UIA isolada 30/30 Invoke e caminho UI/escritor exercitado. Variacao de foco e latencia de provedores nao sao causalidade nem qualidade universal. O aceite humano em Windows 10/11 continua sendo a proxima dependencia, conforme VALIDACAO_MANUAL_WINDOWS.md.

## D-015 - Aceite guiado com etapas explícitas e relatório fechado
- **Decisão:** lançador CMD/Python local, sem pip/instalação/elevação/bypass, com preparação offline em SDK 8 fixado, hashes de executáveis e DLLs e testes automáticos iniciados pelo operador. Laboratório continua desativado até início explícito, por 15 minutos.
- **Relatório:** JSON versionado e validado por schema fechado; observações são enums, sem texto livre. Exportação exclusiva para pasta fora de qualquer checkout Git, sem eventos individuais/identificadores da máquina. Todos os PASSOU humanos são auto declarações: o gate permanece pendente de revisão e piloto sempre falso.
- **Alternativas:** regex para tentar anonimizar notas arbitrárias ou promover CI a aceite. Rejeitadas por risco de vazamento e evidência incorreta. Campos não verificáveis ficam nulos/lacunas.

## D-016 - Métricas somente de handles próprios e limpeza dos comandos
- **Decisão:** CPU por delta e RAM por Win32, apenas no controlador e filhos fictícios explicitamente registrados, sem enumeração de processos, nomes, títulos ou conteúdo. Amostra de 500 ms e pico OS de vida inteira são identificados; início/pausa medidos até ACK observado na UI, separados da percepção humana.
- **Confiabilidade:** comandos de preparação/teste usam Job Object kill-on-close só para seus descendentes; buffers de saída bruta limitados em memória e nunca exportados. Artefatos são rechecados antes de cada lançamento/início. Toplevel usa o mesmo interpretador Tk e cancela timers ao fechar.
- **Limites:** falhas de medição não viram zero, amostragem perde picos; não há prova instrumentada de ausência de tráfego de todo o sistema. ACL/cota total ficam fora do escopo da Issue 5, conforme solicitado.

## D-017 - Resultado automático vigente e ACK observado
- **Decisão:** invalidar o PASSOU anterior antes de cada nova execução automática; timeout/erro deixa FALHOU com contagens desconhecidas. Timeout encerra apenas o comando próprio e permite nova tentativa, enquanto fechamento do assistente cancela permanentemente o runner.
- **Evidência:** teste regressivo cobre sucesso anterior seguido de interrupção e tentativa após timeout; integração aguarda o ACK também ser registrado pelo loop Tk antes de consultar a métrica.
- **Motivo:** a primeira CI desta entrega encontrou uma corrida no teste de pausa, que consultava o contador antes do tick da instrumentação; receber o ACK no stream e observar sua medida no controlador são instantes distintos. Nenhum teste automático promove aceite humano.

## D-018 - Reserva de journal e permissões do armazenamento sintético
- **Decisão:** manter schema legado, DELETE/FULL, sem spill de cache, admissão por bytes de todo diretório dedicado e reserva conservadora de rollback. Rejeitar links e corrupção; não redefinir banco automaticamente. Contar descarte após shutdown e preservar contagem de commits.
- **Limite:** não é quota do filesystem/volume nem barreira contra administrador/escritor concorrente externo. A medição é discreta; limites físicos exigem VFS/volume revisado.
- **Windows:** DACL protegida somente usuário atual e SYSTEM antes de dados; falha fecha a fila. DPAPI só em arquivo experimental exportado, escopo usuário e sem UI; SQLite ativo permanece em claro. Alternativas e riscos em QUESTOES_ARQUITETURA_PRO.md.

## D-019 - Comparação UIA/WinEvent sem fabricar ações de WinForms
- **Decisão:** probe explícito separado, SetWinEventHook process-scoped e apenas eventos de acessibilidade de botões nativos. Exporta contagens/custo/atraso agregado e não alimenta ui_action.
- **Motivo:** STATECHANGE não demonstra ativação; absence de Invoke não pode ser corrigida inventando clique. WPF/WinForms são exercitados com controles padrão, mesma rajada e pausa confirmada.
- **Limites:** objetos filhos sem HWND individual, clicks humanos e aplicativos profissionais não estão cobertos por esta medição. Propor adapter semântico opt-in quando incompatível, sem hooks de conteúdo.

## D-020 - Extensão MV3 local com contrato fechado e estado efêmero
- **Decisão:** storage.session, origem 127.0.0.1:8765/caminho sintético, permissão só storage, geração por pausa, IDs aleatórios, sem conteúdo e exportação por download local explícito. Event v1 continua compatível; importador específico rejeita payloads fora da projeção.
- **Limites:** host pattern não limita porta; guardas no worker/content fazem isso. Timestamp é de recepção; unload/suspensão pode perder mensagens. Política unpacked bloqueia execução no executor: não contornar; CI usa Chromium descartável, e Chrome/Edge reais permanecem gate separado.

## D-021 - Mineração por semântica mínima, variantes e cenários explícitos
- **Decisão:** motor novo paralelo ao legado; normaliza roles/ações sem alvos livres, segmenta sessões/gaps e agrupa edit-distance<=1 com âncoras. Intervalos não sobrepostos por família; famílias são hipóteses alternativas, não totais aditivos. IDs conflitantes são erro.
- **Inferência:** confiança heurística não probabilística, spans não são trabalho efetivo, retrabalho são sinais, economia é null salvo hipótese explícita. UIA genérico sem significado recebe baixa confiança.
- **Alternativas:** PrefixSpan MIT e PM4Py AGPL-3.0 consultados e não incorporados; auditoria transitiva/benchmark pendentes. Limites e evidências em docs/TASK_DISCOVERY.md.

## D-022 - Encerramento conservador do worker web e diagnóstico do estimulador
- **Decisão:** worker MV3 usa prazo UTC e monotônico; mudança de timeOrigin termina coleta, preserva buffer e exige início explícito para outra sessão. Não tentar continuidade silenciosa após suspensão incerta.
- **Evidência:** fault injection de expiração/timeOrigin em Chromium real; reinício real do worker e aceite humano de 15 minutos continuam separados.
- **Harness Windows:** timeout de PowerShell foi observado em um job; causas internas não provadas. Etapas estáticas e limite 30s diagnosticam o processo estimulador sem relaxar exigências do coletor ou repetir ações automaticamente. Nova compilação offline inclui fixture WinForms para não depender de artefatos da CI.

## D-023 - Diagnósticos agregados independentes do aceite humano
- **Decisão:** schema fechado v1 e snapshots por componente, sem identificadores/payloads. Equações por lifetime/estágio, gauges cacheados e lacunas de amostra/proveniência; história recusa replay/regressões sem prometer autenticidade ou exactly-once.
- **Armazenamento:** distinguir commit conhecido de rejeição/duplicata/outcome incerto. Rollback falho fecha writer e registra incerteza; erro após commit não conta commit como perdido. Erro assíncrono rejeita pendências e não retoma sozinho.
- **Limites:** snapshots não globais, contadores voláteis, purge inclui DB anterior; orçamento observado não é quota física e SQLite continua em claro. Branch PR6 e JSON de aceite v1 intocados.

## D-024 - Bridge por arquivos locais e ACK de inbox, sem IPC implícito
- **Decisão:** contrato fechado de fontes fictícias, tickets/gerações, high-water por fonte, batches idempotentes e receipt transacional persistido; transferência manual de arquivos, sem rede/permissões MV3 novas. Novo dono revoga tickets antigos, histórico commitado continua consultável.
- **Limites:** proveniência de arquivo é declaração, não autenticação; hash não é assinatura. ACK não é intenção/resultado de negócio nem pausa global de produtores. Não impor ordem/relógio global; inbox separado limitado e em claro, sem expurgo temporal automático. IPC autenticado e integração contínua ficam posteriores.

## D-025 - Negativos de mineração sem substituição semântica silenciosa
- **Decisão:** variantes só revisão opcional/repetição adjacente; substituições/missing etapas são hipóteses distintas. Sequência local precede relógio, gaps/clock regressivo cortam tarefas; foco conhecido filtrado não gera gap. Click sem ação é ruído.
- **Avaliação:** pares rotulados exclusivamente artificiais (10 traces/45 pares), TP17/FP0/FN0/TN28. Precisão/recall no corpus não é acurácia fora dele; não inferir causalidade nem tempo economizável.

## D-026 - Provar reinício do contexto, não desaparecimento do host DevTools
- **Evidência:** Chromium preserva ServiceWorkerDevToolsAgentHost após StopWorker. Teste exige Inspector.targetCrashed do WorkerStopped e uma nova performance.timeOrigin, mais buffer persistido/producer encerrado/retry/ACK real; não exige wrapper/target destruído nem muta timeOrigin para simular restart.
- **Segurança:** CSP mantida, asserções DOM no popup, perfil descartável permitido em CI; bloqueio unpacked local não contornado. Referência consultada: chromium/chromium, content/browser/devtools/service_worker_devtools_agent_host.cc (WorkerStopped/Close), sem importar código.
- **Limites:** isso não valida todos os casos de idle/sono/energia, nem autentica arquivo/ACK, nem muda gates humanos. Precisão/recall só no corpus rotulado artificial; próxima etapa é retenção de inbox/receipts e desenho de IPC autenticado, não monitoramento real.

## D-027 — Retenção com markers finitos permanentes, ACK de duração limitada
- **Decisão:** inbox v2 migra v1 atomicamente; payload 1h, receipt/ACK 24h desde admissão, IDs globais e high-water por fonte sem TTL. Expurgo não elimina proteção histórica. Cap de markers bloqueia admissão, nunca eviction/reset.
- **Recuperação:** retry vivo é leitura independente de quota; receipt vencido produz receipt_expired_or_unknown, não negação de commit. Clock regressivo fecha admissão/congela purge; avanço UTC ainda é risco explícito.
- **Alternativas:** apagar IDs junto ao payload permitiria replay; hash/Bloom limitado introduziria colisões/falsos positivos; histórico ilimitado viola orçamento. Cap conservador requer revisão antes de qualquer uso contínuo.
- **Limites:** SQLite claro, orçamento lógico/amostrado, limpeza somente quando executada, sem relógio confiável/admin-proof, exactly-once ou aceite humano. Contratos anteriores/PR6 preservados.
- **Revisão D-027:** rollback falho ou exceção no retorno de commit invalida/fecha conexão e requer reopen; SQLite pode expor linhas ainda não commitadas na conexão original. in_transaction=false não resolve resultado ambíguo. Diagnóstico null/uncertain evita ACK fabricado. Erro após retorno de commit bem-sucedido permanece conhecido, com leitura histórica válida.
- **Evidência final D-027:** código6d521cf/CI41759340778, cinco jobs aprovados, incluindo as regressões de rollback/commit incerto nos quatro ambientes Python/OS e dois testes Chromium reais. Conferir CI do head documental no PR15.

## D-028 — Autenticação modelada não habilita canal sem peer comprovado
- **Decisão:** aplicar Issue14/P2.6: especificação de ameaças/protocolo, modelo HMAC/challenge em memória e probe de handle próprio Windows; nenhum IPC/adaptador ligado. Identidade declarada no simulador é premissa, não prova de origem.
- **Alternativas:** arquivos com MAC sem pareamento privado e loopback sem autenticação rejeitados. Preferir pipes herdados de filho próprio antes de named pipes com ACL/peer kernel bidirecional. NativeMessaging só avaliação futura, sem instalar host.
- **Prova pendente:** associação do peer do canal com PID/criação/caminho/sessão, herança mínima/entrega de chave, ACLs adversariais, colisão/EOF/cancelamento reais. Mesmo usuário/admin não são fronteira de proteção demonstrada. Modelo transporte/inbox/producer pause têm ACKs distintos.
- **Evidência D-028:** CI41758466029 executou o probe nativo nos dois Pythons Windows e modelo em quatro jobs; isso prova identidade do filho retido, não do peer de transporte. Integração continua fechada até associação ao canal e testes adversariais reais.
- **Evidência integrada D-028:** bc23073/CI41759416977, cinco jobs, Windows147/Linux136 executados por Python e Chromium2 reais; skips explícitos. Probe nativo continua parcial, IPC/adaptador seguem desligados. Próxima tarefa/requisitos em RETOMADA_AUTONOMA.md/SOURCE_AUTHENTICATION.md.

## D-029 — Canal de capacidade herdada, isolado do protocolo de aceite
- **Decisão:** Etapa A com fixture IPC Python isolada e Win32 pipes anônimos/lista explícita de quatro handles. Chave só pelo bootstrap herdado; Popen retido/identidades kernel e prova HMAC associam canal ao filho possuído. Sem endpoint público ou attach a PID.
- **Alternativa:** mudar C#/NativeSession em uso pelo aceite aumentaria a superfície de regressão; preservar e testar entrypoint novo primeiro. Named pipes acrescentam ACL/squatting/peer API; não necessários ao experimento herdado.
- **Limite:** não é isolamento de mesmo token/admin/injeção/checkout adulterado, nem consulta PID do peer via API de named pipe. Python é fixture IPC real executada em Windows, não UIA nem modelo em memória. Adapter permanece OFF e afirmações dependem de CI Windows real/revisão independente.
- **Evidência inicial D-029:**22f99e5/CI41809413254 executou a Etapa A em processos/handles Windows reais nos dois Pythons; somente o peer da fixture IPC é autenticado por capacidade herdada+HMAC. Ampliar adversariais antes da revisão independente; provider C#/adapter continuam fora dessa prova.
- **Revisão D-029:** probe deve comparar identidade de objetos do kernel, não apenas validade de um número reciclável. Herança alargada é recusada antes da criação da chave; bootstrap fechado conferido e erros do harness têm somente fase/exitcode. CI41811218903/Windows3.12 não foi aprovada; novas provas requeridas.
- **Prova ampliada D-029:**260900d/CI41812922153, cinco jobs,14 testes Windows reais e capacidade1024/10000/32 nos quatro ambientes. Outra conta/sessão, humanos10/11 e adapter C# continuam fora da prova.
- **Cancelamento D-029:** reter handle do worker obtido de GetCurrentThread/DuplicateHandle, sem OpenThread por ID reciclável; lock breve protege cancel/close. Não sacrificar identidade de objetos por conveniência de cleanup. Nova revisão exige CI própria.
- **Evidência final D-029:**0588d8a/CI41814049436 teve5/5 jobs; todos os14 novos casos Windows reais, incluindo cancelamento por handle retido. Quatro wire/default-off e três capacidades executaram em Linux/Windows; browser separado2 reais. Adapter continua OFF: fixture IPC não autentica C# antigo, outra conta e aceite humano/revisão independente pendentes. Consolidação futura somente proposta em STACK_REVIEW_PLAN.md, sem operações de merge/rebase executadas.

## D-030 — Estabilizar interpretação do aceite sem reescrever a evidência humana
- **Decisão:** execução humana Win11 relatada é evidência da versão declarada PR6 com ressalvas, sem atribuir SHA ausente/skip/causa. Corrigir gap do OS já ensaiado no ramo novo; human_gate/pilot continuam fechados e Win10 separado.
- **Compatibilidade:** schema JSON v1/CMD/branch PR6 preservados; diagnóstico fechado separado acompanha futuras exportações locais. Cache de saúde explica limites/amostras, nunca causa/taxa de perda ou health final confirmada.
- **Proveniência/cobertura:** ZIP não recebe commit inventado nem ancestral. Skips são cobertura incompleta; todos skipped/resumo ausente não são sucesso. Não solicitar JSON do operador para Git nem usar fixtures construídas como aceite real.

### D-031 — Cleanup resiliente a falhas e revisão independente por SHA

A autorrevisão de PR18 encontrou OSError de fechamento/cancelamento capaz de
interromper cleanup. A filha tenta os recursos restantes e drena futures; expõe
cleanup_errors/cleanup_unconfirmed e não confirma shutdown após erro. Não repetir
cegamente número de handle com ownership incerto. Regressões usam falha injetada,
separadas das provas Win32 normais. Não atribuir esse achado ao descarte do PR6.
Pacote SECURITY_REVIEW_PR18.md organiza revisão externa, sem inventar signoff ou
enviar mensagens. Consolidação permanece plano por SHA, sem merge/rebase/retarget.

Complemento D-031: verificar retorno real de CancelSynchronousIo;1168 significa
nenhum IO pendente e é tolerado, demais erros não são silenciados. Regressão
portável injeta retornos no wrapper, sem alegar falha real de kernel provocada.
Auditoria dos wrappers compartilhados de job/métricas continua gate explícito.

## D-032 — CloseHandle confirmado, referência em quarentena e métrica por capacidade

Issue20/A1–A4: uma tentativa de CloseHandle com BOOL declarado/verificado; em
erro, referência retida, estado failed e erro estático cleanup_unconfirmed. Sem
retry de slot numérico incerto. Job usa TerminateJobObject e consulta limitada a
zero processos antes do fechamento; falhas de teardown continuam tentando os
outros recursos, nunca dão confirmação limpa. Construtor falho preserva seu dono.

Métrica duplica handle do Popen retido, não abre PID nem usa primeiro processo
encontrado como baseline. Fonte/duplicata têm criação conferida antes da leitura;
saída normal conserva só amostras históricas válidas. Token ACL também falha
fechado no close. Alternativas rejeitadas: apagar referência em erro, retry cego,
assumir que fechar job prova término, comparar apenas PID/nome.

Falha protegida de handle real será distinguida de BOOL/identidade injetados;
reuso real de PID e falha em campo não são alegados. A janela Popen→assignJob
preexistente e fronteira mesmo token/admin não são resolvidas por esta correção.
Revisão distinta exigida pela Issue continua gate humano, não substituída pela CI.

Evidência D-032: código7740254/CI41857555311 teve cinco jobs aprovados. As falhas
de CloseHandle protegido em job/probe foram REAIS e controladas nos dois Windows;
falhas de terminate/query/identidade continuam INJETADAS. Não promover skips ou
CI a aceite humano. Revisão distinta do implementador permanece pendente.

## D-033 — Binding legado por capacidade e teardown independente

Issue22/AI01–02: duplicar handle do Popen retido com direitos de query/sync, conferir
PID/criação antes de provider e validar fechamento. Falha retém dono e impede
launch, sem fallback PID. Cleanup independente registra enums/contagens sem
exceções brutas; falha de sink/secondary/IO não interrompe os demais recursos.
Não fechar wrapper IO bloqueado por thread viva; registrar incerteza. Confirmação
no v1 só após todos os recursos, sem alterar seu schema.
Auditoria IA da Issue22 é evidência técnica distinta, não assinatura humana nem
aprovação end-to-end. AI03 requer design/ensaio isolado separado; adapter OFF.

D-033 / evidência: oito casos novos portáveis passaram localmente; CI de a332be4
falhou antes dos testes nos cinco jobs, inclusive após um retry controlado. Sem
prova Windows desta revisão, não inferir resultados a partir do PR21 ou dos skips.
Causa do bloqueio não foi exposta; não alterar cobrança, permissões ou política
de extensão para contornar. Restauração do Actions e revisão dos SHAs são gates.

## D-034 — Suspensão é estudo isolado, não solução de lifetime pré-Job

AI03: criar suspenso impede thread primária da fixture de executar antes do
resume verificado, mas pai morto antes do assign pode deixar processo suspenso
fora do Job próprio. Não integrar essa alternativa como correção completa.
Preparar experimento Win32 só em tests/, com zero herança de endpoints, callbacks
negativos injetados e prova de crash por capacidade retida da raiz. Avaliar Job
na criação (STARTUPINFOEX/JOB_LIST) futuramente; suporte/garantias não comprovados.
Os testes Windows desta entrega não rodaram devido à falha de CI anterior a
etapas. Não transformar expectativa arquitetural em prova de kernel executada.

## D-035 — Cleanup não pode depender de thread daemon após main retornar

Complemento AI02 em filha do estudo: recursos posteriores podiam perder a tentativa
se o processo terminasse após o join limitado. Reproduzido em subprocesso real
com atraso artificial, sem UI/Win32; corrigido com worker não daemon e graça20s
no standalone. Contrapartida: API travada pode manter o processo aguardando, sem
promessa de deadline global. Não sacrificar tentativas de cleanup por saída
silenciosa. Nenhum launcher suspenso foi integrado, nenhum adapter habilitado.

## D-036 — Observar a primeira falha Win32 antes de alterar cleanup

Issue27: erro genérico de SuspendedProbe não identifica causa. Instrumentação
exclusiva do harness registra fases/enums/contagens e confirmação pós-falha, mas
a entrega diagnóstica conserva status de erro. Não assumir corrida de término,
não aumentar timeout nem dispensar asserts. Step focado nos dois Windows antes
da matriz completa; correção depende de evidência nativa, seguida de regressões.

D-036 / causa confirmada: CI41929775944 nos dois Windows mostrou erro5 no
fallback após Job confirmado e antes de esperar término; observação posterior
sinalizou processo, handles fecharam. Esperar saída pós-Job e reutilizar o mesmo
orçamento2s. Recuperação limitada a AccessDenied + espera sinalizada + Job
confirmado, com erro preservado no diagnóstico; jamais tolerar close falho ou
API inválida por essa regra. Origens win32/injected/híbrida são explícitas.

## D-037 — Nenhuma exceção pré-worker pode pular teardown

Issue27 P2: isolar stream/Tk/observação; construir/startar worker dentro de try
com fallback síncrono. Barreira de startup impede publicar sucesso antes de
conhecer erro de start; lock serializa worker/fallback. Categorias fixas controls
e cleanup_worker mantêm incerteza mesmo com recursos encerrados. Não depender
de repetir stop após finished=True. Não usar retry de close nem transformar
TclError em skip. Mantém limite conhecido de API travada/worker não daemon.

Evidência D-036/D-037:6e0cf86/CI41931710044 cinco jobs aprovados; Windows
223 executados/2 skips por Python, Linux184/41 e Chromium2/0. Estudo focado11/0
em cada Windows. TclError/close protegido foram falhas reais controladas;
startup/retornos API portáveis são injetados; corrida com primeira espera
simulada é híbrida. Diagnóstico inicial FALHOU intencionalmente para estabelecer
causa antes da correção; não apagado nem promovido a passe. Revisão independente
por SHA e gates humanos permanecem, sem integração do estudo ou adapter.

## D-038 — Job List apenas em experimento reversível antes de migrar runtime

Issue29/AI03B: CreateProcessW suspenso com STARTUPINFOEXW e JOB_LIST próprio, sem
herança/breakaway, pode remover o intervalo userspace Create→assign no harness.
Exigir prova Windows por SHA: morte do launcher pré-verify/pré-resume/pós-resume,
capacidade de processo retida pela raiz sem Job alvo, saída kernel dos filhos.
Nested externo mantido aberto separa causalidade do Job interno; nunca contornar
hierarquia do runner. Delete VOID é contrato de API, não BOOL/heap independente;
reter lista/lpValue até retorno normal e falhar fechado em exceção de wrapper.
Negativos reais de parâmetros/close distintos de retornos injetados. Não extrapolar
para IPC herdado, mesmo token/admin ou Windows10/11 humanos. Não migrar launchers,
não iniciar Issue30 nem considerar CI autorização de integração/piloto.

D-038 / evidência:518678a/CI41959802089 cinco jobs aprovados, Windows240/2 skips,
Linux191/51 por Python, Chromium2/0; foco novo17/0 nos dois Windows. Lista própria
completa e zero de Job substituem premissa inválida de exatamente2 membros; origem
de membros adicionais não identificada, hipótese de console isoladamente refutada.
Não abrir PIDs extras para inventar identidade. Nested externo aberto comprova
zero de todos membros após crash pós-resume; caso sem externo observa somente
capacidades de processos conhecidos. API/handle protegidos realmente recusados;
retornos de guardas/cleanup e Delete que lança são injetados. Nenhum timeout
ampliado, fallback antigo ou claim de integração. Issue30 aguarda revisão29.

## D-039 — Liveness não equivale a cleanup confirmado (Issue #30)

`threading.Thread(daemon=False)` mais `join(timeout=20)` evita abandono silencioso
mas não fixa deadline global: API bloqueada pode manter o processo Python vivo.
`CancelSynchronousIo` é tentativa de cancelamento de I/O síncrona, não interrupção
universal. Preservar `cleanup_unconfirmed` para falha anterior mesmo que recursos
independentes terminem depois; UI, worker, recursos/Job e tempo têm estados separados.

Decisão de engenharia **somente para estudo**: priorizar o desenho de um processo
sintético supervisionado com Job associado na criação, condicionado à propriedade
dos handles, membership verificável e fechamento do último Job; não integrar
antes de provas adicionais de IPC/herança e de segurança. Não usar `TerminateThread`,
`os._exit`, thread daemon nem timeout como atalho para declarar encerramento.

O teste do processo isolado com lock é uma demonstração real da limitação de join,
não simulação de API Win32 não cancelável. Os demais negativos são contratos
simulados. Nenhuma garantia global ou watchdog de runtime foi implementado.
Revisão humana e Issue22/AI04 continuam abertas.
