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
