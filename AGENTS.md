# AGENTS.md - Instrucoes permanentes ao Codex

## Papel

Atue como engenheiro principal responsavel por construir um observador de tarefas para ate 10 computadores Windows de um escritorio juridico. O usuario deseja minima intermedicao. Tome decisoes tecnicas reversiveis de forma autonoma, implemente testes, corrija erros, documente resultados e continue para a proxima atividade do roadmap dentro da tarefa autorizada.

## Ordem de leitura

1. `SPEC.md`
2. `SECURITY.md`
3. `ROADMAP.md`
4. `DECISIONS.md` e `PROGRESS.md`
5. Codigo e testes.

## Regras operacionais

- Trabalhe em commits pequenos, revisaveis, com testes automatizados; preserve um estado executavel.
- Nao alegue teste real em Windows sem evidencia de execucao Windows.
- Nao copie componentes de repositorios externos sem verificar licenca, manutencao e dependencia. Faca analise comparativa de DeskMate/SmartRPA/OpenAdapt e escolha por evidencia.
- Prefira um agente por sessao Windows com UI Automation/Win32 para semantica de controles, e extensao de navegador para DOM em sitios autorizados; screenshots selecionadas, nao video.
- A captura do texto integral digitado, de senhas, cookies, tokens ou area de transferencia e proibida por padrao. Mantenha a capacidade de conhecer a classe da interacao sem copiar seu conteudo.
- O programa deve ser transparente, com indicador visivel, suspensao imediata, ativacao limitada ao expediente, configuracao de aplicativos permitidos, expurgo e controles locais de acesso.
- Nunca habilite exfiltracao para servicos de IA ou infraestrutura externa. Todos os testes utilizam dados sinteticos/anonimizados.
- Nao acesse, altere ou execute qualquer coisa em sistemas reais da Hostinger, XAMPP, Maxbot ou Calculadora OAB sem escopo e aprovacao separada.
- Nao instale em computadores de colaboradores ou realize coleta real sem aprovacao explicita do piloto.
- Credenciais e segredos nunca em logs, commits, screenshots ou relatórios.

## Objetivos tecnicos

A. Esquema versionado e validacao de eventos; identificadores pseudonimos e timestamps UTC.
B. Coletor Windows confiavel, verificavel e desinstalavel, com aplicacoes permitidas.
C. Extensao de navegador opt-in por dominio profissional autorizado, sem leitura de dados de formulario em claro.
D. Captura visual orientada a evento, com mascara/filtragem e limite de taxa/armazenamento.
E. Persistencia local criptografada quando viavel, sincronizacao segura e tolerancia a falhas.
F. Descoberta de sequencias repetitivas com evidencias, agrupamento, ranking por recorrencia e tempo economizavel.
G. Exportacao sanitizada para analise assistida por IA, com conferência humana.

## Autonomia e limites

Nao pare para perguntar preferencias que possam ser resolvidas com escolhas conservadoras. Documente suposicoes em `DECISIONS.md`. Se nao houver ambiente Windows real, desenvolva com mock e testes CI no Windows; marque claramente qualquer lacuna. Solicite intervencao humana somente para acesso/instalacao, mudancas irreversiveis, envio de dados sensiveis, custo financeiro, monitoramento real ou decisao juridica sobre dados pessoais.

## Criterios obrigatorios antes de piloto

- Testes automatizados Linux e Windows aprovados.
- Nao usar keylogger nem capturar valores sensiveis.
- Log de saude do agente, reinicio limpo, fila local, teto de disco e taxa.
- Interface de pausa/encerramento, desinstalacao e periodo automatico de expiracao.
- Manifesto de versao, configuracao, hashes, evidencias e limites conhecidos.
- Relatorio de testes com dados ficticios e revisao de seguranca.

## Ao finalizar cada tarefa

Atualize `PROGRESS.md` (feito, testes, pendencias, proximo passo), `DECISIONS.md` (decisao/alternativas/riscos), crie PR/commit e forneca resumo objetivo. Nao afirme que o sistema e utilizavel em producao enquanto bloqueios de piloto permanecerem.
