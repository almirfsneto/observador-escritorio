# Roadmap de desenvolvimento autonomo

## Fase 0 - Base reprodutivel (iniciada)

- [x] Esquema de eventos validavel e sem conteudo sensivel por padrao.
- [x] Banco SQLite com IDs unicos.
- [x] CLI com dados ficticios e detector simples de padroes.
- [x] Testes unitarios e workflow CI Linux/Windows (4 jobs aprovados no commit f48b31e; evidencia em PROGRESS.md).
- [ ] Revisao independente do scaffold.

## Fase 1 - Avaliacao de motores de captura

- [ ] Inspecionar DeskMate, SmartRPA e alternativas livres; matriz de licenca, seguranca, compatibilidade e manutencao.
  - Entrega inicial: matriz documental em `docs/CAPTURE_ENGINE_REVIEW.md`; identidade do DeskMate referido e auditoria transitiva ainda pendentes.
- [ ] Prototipo Windows UI Automation com aplicativo ficticio.
  - Implementados ponte Win32/UIA, politica testada com mocks e formulario ficticio; ensaio integrado em Windows pendente.
- [ ] Extracao de metadados de janela e controle, sem keylogger nem valores de campo.
  - Projecao fechada de foco/papel implementada; acoes e identificacao segura entre controles iguais pendentes.
- [ ] Integração opcional com captura selecionada e redacao.

## Fase 2 - Agente Windows utilizavel em laboratorio

- [ ] Tray app visivel, allowlist, pausa, janela de coleta e expiracao.
- [ ] Inicializacao no login, fechamento limpo e recuperacao de falhas.
- [ ] Limite de screenshot, cota de disco, politica de expurgo, logs de saude.
- [ ] Pacote de instalacao/desinstalacao; logs e testes Windows com apps sinteticos.

## Fase 3 - Aplicacoes web e multiplas maquinas

- [ ] Extensao opt-in Chrome/Edge por dominio permitido com eventos DOM saneados.
- [ ] Coletor central com TLS, autenticacao, filas e sincronizacao idempotente.
- [ ] Painel de status de agentes e ingestao, sem conteudo pessoal.

## Fase 4 - Mineracao de microtarefas

- [ ] Algoritmos para segmentar sequencias, deduplicar e reconhecer variacoes.
- [ ] Ranking por recorrencia/duracao com revisao humana e indicacao de incerteza.
- [ ] Relatorio exportavel e pacote desidentificado para IA.

## Fase 5 - Piloto controlado

- [ ] Validacao tecnica em 1 Windows com dados ficticios.
- [ ] Piloto voluntario em 2-3 maquinas apos autorizacao.
- [ ] Medicao de perda de eventos e overhead.
- [ ] Expandir a 10 somente apos criterios de aceite.

## Entrega 2 - laboratorio com controle visivel (branch codex/visible-windows-laboratory)
- [x] Projeto WinForms ficticio dedicado (.NET 8), sem leitura de dados reais.
- [x] Controlador Windows visivel inicialmente desativado, iniciar/pausar/encerrar, somente alias e papel, sem persistencia.
- [x] Limite de 15 minutos e testes sinteticos para caminho permitido e expiracao.
- [ ] Validacao integrada em sessao Windows interativa com evidencia e medicao de latencia.
- [ ] Vincular instancia por PID + instante de criacao e substituir polling lento antes do piloto.
- [ ] Fila persistente com cotas, retencao e controles completos de privacidade.

## Entregas 3/4 — revisao, eventos rapidos e fila local
- [x] Revisao tecnica dos PRs 1/2 pelo desenvolvedor, com correcoes documentadas (nao revisao independente).
- [x] Provider UIA persistente, instancia PID/criacao/caminho, foco/Invoke/Toggle e IDs efemeros.
- [x] Buffers limitados, geracoes de pausa, expiração monotona e encerramento dos processos possuidos.
- [x] Fila SQLite opt-in sintetica com cota do banco, TTL, limite de linhas e saude.
- [x] Evidencia CI Windows de UIA, controlador, fila e mineracao sintetica registrada em PROGRESS.md (55 testes Windows; 30/30 Invoke WPF).
- [ ] Aceite humano do controlador em Windows 10/11 e medicao de overhead/perda.
- [ ] ACL/cifragem, cota total incluindo auxiliares, screenshots e demais gates de piloto.

## Issue 5 — aceite guiado com relatório sanitizado
- [x] Lançador local com preparação offline, dependências previamente instaladas, hashes e testes explícitos.
- [x] Avaliação manual PASSOU/FALHOU/NÃO EXECUTADO com observações fechadas.
- [x] CPU/RAM de processos próprios, tempos de ACK e contadores separados de percepção humana.
- [x] Relatório local fora de Git com schema fechado; nenhum upload ou liberação de piloto.
- [x] Confirmar CI Linux/Windows desta entrega e registrar evidências em PROGRESS.md (76 testes Windows; Ubuntu 68 executados + oito skips).
- [ ] Execução humana em Windows 10 e 11 dedicados, que continua obrigatória.

## Execução intensiva — entregas sobre PR6
- [x] PR7: orçamento agregado e reserva de journal, recuperação/erros, DACL Windows e arquivo DPAPI experimental.
- [x] PR8: diagnóstico process-scoped e comparação WPF/WinForms; incompatibilidade permanece explícita, sem inferir clique.
- [x] PR9: MV3 somente fixture loopback, pausa/limites e importação fechada; CI Chromium real aprovada.
- [x] PR10: famílias de microtarefas/variantes sem IDs, suporte não sobreposto, cenários de economia e corpus fictício.
- [ ] Criptografia da fila SQLite ativa, cota física estrita e revisão adversarial com outra conta.
- [ ] Adapter semântico específico para WinForms incompatível; teste de input humano em Windows 10/11.
- [ ] Integração browser/agente, ordenação multi-origem e durabilidade/ACK de exportação.
- [ ] Calibração do minerador com corpus sintético maior e comparação executada de bibliotecas auditadas.
- [ ] Aceite humano Windows 10/11 e Chrome/Edge em perfil descartável; nenhum piloto autorizado.

## Issue 11 — diagnósticos e contrato offline
- [x] PR12: diagnóstico fechado v1, contadores por fase, budget observado e faults BUSY/FULL/IO/rollback/commit/shutdown.
- [x] PR13: bridge de arquivos sintéticos, proveniência declarada, gates, ACK transacional/idempotência e fonte/ordem separadas.
- [x] Chromium: stop/restart REAL do worker, buffer/retry/ACK local; Linux/Windows 3.11/3.12 em CI.
- [x] Negativos e métricas em corpus rotulado inteiramente sintético, sem afirmação de acurácia externa.
- [ ] Retenção do inbox/receipts com recuperação após restart e limites adicionais.
- [ ] IPC autenticado/adaptador Windows opt-in e coordenação confirmada de produtores.
- [ ] Dataset independente, calibração, Chrome/Edge e Windows 10/11 humanos; PR6 permanece reservado.

## Issue 14 — retenção e autenticação sintéticas
- [x] Implementar TTL separado de payload/receipt, markers permanentes limitados e ACK recuperável.
- [x] Testes de crash, replay após purge, conflitos, clocks, quota e migração v1.
- [x] P1/6d521cf CI41759340778 e P2/bc23073 CI41759416977: cinco jobs aprovados em cada entrega; conferir também HEADs documentais finais.
- [ ] Análise de ameaças, pareamento autenticado e integração exclusivamente sintética revisada.
- [x] P2: threat model, protocolo/simulador fechado, negativos/fuzz e probe separado de identidade de filho Windows.
- [ ] P2: peer do canal verificado, chave entregue por handle privado, testes adversariais/IPC e adapter opt-in; NÃO habilitados pelo simulador.

## Issue 17 — canal herdado e auditoria
- [x] Etapa A isolada: processo IPC Windows real, lista mínima de handles, bootstrap privado e HMAC com identidade kernel; primeira CI41809413254 aprovada.
- [x] Testes reais adicionais: decoy/descendente/WPF/filho não possuído, replay/contexto, duas instâncias/pausa, kill/timeout/cancelamento e cap64; CI41814049436 aprovada nos dois Windows.
- [x] Saturação real1024/10000/32 sem reset/monkeypatch, clocks injetados; Linux/Windows3.11/3.12 aprovados.
- [x] Plano de consolidação/revisão independente, sem merges/rebases em docs/STACK_REVIEW_PLAN.md.
- [ ] Aprovação independente/outra conta/Windows10/11 e autenticação do WindowsObserver C#; adapter continua OFF.
