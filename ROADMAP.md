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
- [ ] Confirmar CI Linux/Windows desta entrega e registrar evidências em PROGRESS.md.
- [ ] Execução humana em Windows 10 e 11 dedicados, que continua obrigatória.
