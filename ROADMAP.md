# Roadmap de desenvolvimento autonomo

## Fase 0 - Base reprodutivel (iniciada)

- [x] Esquema de eventos validavel e sem conteudo sensivel por padrao.
- [x] Banco SQLite com IDs unicos.
- [x] CLI com dados ficticios e detector simples de padroes.
- [x] Testes unitarios e workflow CI Linux/Windows (execucao CI a confirmar apos publicacao).
- [ ] Revisao independente do scaffold.

## Fase 1 - Avaliacao de motores de captura

- [ ] Inspecionar DeskMate, SmartRPA e alternativas livres; matriz de licenca, seguranca, compatibilidade e manutencao.
- [ ] Prototipo Windows UI Automation com aplicativo ficticio.
- [ ] Extracao de metadados de janela e controle, sem keylogger nem valores de campo.
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
