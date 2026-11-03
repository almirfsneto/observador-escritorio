# Arquitetura pretendida

```text
[Win10/11 agente de sessao] -----> [SQLite/fila local] --- TLS ---> [Servidor do escritorio]
          |                                    |                     |
          +-- UI Automation/Win32              +-- criptografia       +-- ingestao idempotente
          +-- eventos de arquivo allowlist                             +-- agregacao de processos
          +-- screenshot seletiva                                     +-- exportacao redigida
          +-- bandeja, pausa, expiracao

[Extensao web opt-in por dominio] -> [Agente de sessao Windows]
```

**Estado atual:** somente schema e analise offline com dados ficticios. Nenhum dos componentes de captura ou rede foi implementado neste scaffold.

## Correlacao

Campos `event_id`, `session_id`, `device_id` pseudonimo e `timestamp_utc` vinculam a linha do tempo. Eventos externos nao devem receber causalidade apenas por proximidade temporal; use IDs de requisicao/traces quando disponiveis.

## Captura de aplicacoes

Uso de UI Automation e Win32 nos aplicativos Windows que expoem elementos; fallback para metadados de janela quando nao houver semantica. Para sitios web autorizados, extensao com seletores de elementos higienizados. Nunca ler valor sensivel.

## Mineracao

Segmentar por sessao, ociosidade e mudanca de contexto; normalizar acoes; contar sequencias recorrentes, duracao e variacoes. IA interpreta apenas dados redigidos e deve indicar incerteza e referencias verificaveis.
