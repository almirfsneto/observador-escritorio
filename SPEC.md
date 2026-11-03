# Especificacao funcional - Observador Escritorio

## Problema

Mapear o trabalho real de 10 colaboradores, cada qual com Windows, para encontrar procedimentos repetidos e oportunidades de automacao de microtarefas. Periodo de observacao curto, com conhecimento e orientacao da equipe. Usuario nao deseja operacao manual para iniciar/parar cada tarefa.

## Exigencias de produto

- Inicializar automaticamente em cada login autorizado e respeitar o intervalo de coleta configurado.
- Monitorar apenas aplicativos, janelas, dominios e pastas profissionais incluídos em allowlist; por padrao, nao coletar.
- Registrar eventos semanticos (troca de janela, clique em controle com papel/nome saneado, atalho sem conteudo, inicio/fim de transferencia, criacao/renomeio/movimento de arquivos autorizados, falhas e latencias).
- Capturar prints de eventos relevantes com limite por minuto, mascara e revisao antes do compartilhamento; dispensar video permanente.
- Identificar o que e observado automaticamente, sem depender de anotacoes do colaborador.
- Manter armazenamento local por computador e centralizar somente quando autorizado e com cifragem e autenticacao.
- Encontrar sequencias de 2+ etapas recorrentes e estimar frequencia/duracao/variacoes; evitar interpretar proximidade temporal como prova de causalidade.
- Gerar exportacoes agregadas e evidencias desidentificadas para analise por IA.
- Permitir desligamento, pausa, expiracao do piloto e exclusao verificavel da captura.

## Requisitos nao funcionais

- Desempenho: baixo overhead e degradacao graciosa; limites de CPU, memoria, disco e screenshots configuraveis.
- Dados: schema versionado, timestamps UTC, integridade, nao duplicar eventos e atribuir confianca a inferencias.
- Compatibilidade: Windows 10/11. Pilotar antes de uso em varias maquinas.
- Confiabilidade: gravação local continua sem rede; sincronizador idempotente; log de saude sem PII.
- Seguranca: criptografia local e no transporte quando implementado, allowlist, permissoes de acesso, revisao LGPD e trilha de administracao.

## Fora do escopo inicial

- Analise de produtividade ou ranking individual de empregados.
- Registro de texto integral de teclas/clipboard e captura invisivel.
- Monitoramento de sistema operacional da Hostinger ou da Calculadora OAB.
- Execucao automatica de rotinas nos sistemas dos clientes.
- Instalacao silenciosa e remota em computadores de terceiros.

## Saidas desejadas

1. Linha do tempo pesquisavel por processo (pseudonima).
2. Relatorio de microtarefas candidatas, com frequencia, passos, duracao e incerteza.
3. Evidencias sanitizadas por ocorrencia, sem PII.
4. Lista priorizada de automacoes com estimativa e necessidade de validacao.
