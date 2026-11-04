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
