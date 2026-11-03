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

## D-013 - Cobertura UIA por provedor, cache minimo e evidencia real sintetica
- **Decisao:** manter WinForms para explicitar limite observado (foco recebido, nenhum Invoke nesse caminho) e usar controles WPF padrao para o ensaio de acoes. Nenhuma instrumentacao especial emite eventos para o observador.
- **Evidencia:** CI no commit c4ca6cf recebeu 30/30 Invoke em dois botoes WPF, sem descartes de fila e com exclusao de senha, em Python 3.11 e 3.12. Isso nao demonstra captura de cliques WinForms nem outros aplicativos.
- **Arquitetura:** notificacao global de foco solicita apenas PID em cache; somente depois de filtrar a instancia uma thread MTA consulta papel, flag de senha e RuntimeId. Eventos de acao sao restritos a subtree e usam cache dessas propriedades, evitando consultas reentrantes no callback. Filas e geracoes continuam limitadas.
- **Alternativas:** tratar ausencia de Invoke como ausencia de trabalho, ler nomes/valores para inferir cliques ou usar hooks globais. Rejeitadas por qualidade e privacidade. Validacao humana Windows 10/11 e medicao de overhead/perda seguem pendentes.
