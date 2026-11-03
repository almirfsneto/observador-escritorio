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

Opcionais: `screenshot_ref` (caminho relativo controlado), `metadata` (dicionario de chaves em allowlist: `control_role`, `http_status`, `result`, `confidence`, `category`).

Nao colocar senhas, CPF, email, nomes reais, valores de formulario, caminhos de cliente ou payloads de rede em `metadata`.

Evolucoes de esquema devem ser versionadas e acompanhadas de migracoes/testes.
