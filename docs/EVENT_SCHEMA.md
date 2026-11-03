# Contrato de evento v1

Campos obrigatorios:
- `schema_version`: numero inteiro 1
- `event_id`: UUID
- `timestamp_utc`: ISO 8601 com timezone UTC
- `device_id`: identificador pseudonimo persistente, nao hostname real
- `session_id`: UUID da sessao autorizada
- `app`: aplicacao profissional canonicamente identificada
- `event_type`: tipo controlado (`session_start`, `session_end`, `window_focus`, `ui_action`, `file_action`, `browser_action`, `error`, `screenshot`)
- `action`: verbo semanticamente higienizado (`open`, `click`, `save`, `rename`, `move`, `paste_metadata`, etc.)
- `target`: papel/classe de UI sem texto pessoal
- `duration_ms`: duracao nao negativa (0 quando indisponivel)

Opcionais: `screenshot_ref` (caminho relativo sem barras invertidas, drive ou
componentes vazios/ponto), `metadata` com dominios fechados:

- `control_role`: button, checkbox, combobox, edit, listitem, menuitem, tab, window ou control.
- `http_status`: inteiro 100–599, sem booleanos.
- `result`: success, failure, cancelled ou unknown.
- `confidence`: numero finito entre 0 e 1, sem booleanos.
- `category`: demo, laboratory ou synthetic.
- `source_sequence`: inteiro positivo menor que 2^63, opcional e restrito a sessao.
  Desempata observacoes com o mesmo timestamp; nao e prova de ordem causal.

O campo opcional source_sequence preserva compatibilidade com eventos v1 anteriores;
nenhuma migracao de tabela e necessaria porque metadata e armazenada no JSON.
O endurecimento de dominios rejeita metadata antiga fora da allowlist atual.

Nao colocar senhas, CPF, email, nomes reais, valores de formulario, caminhos de cliente ou payloads de rede em `metadata`.

Evolucoes de esquema devem ser versionadas e acompanhadas de migracoes/testes.
