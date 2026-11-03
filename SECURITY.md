# Seguranca, privacidade e piloto

O escritorio trabalha com dados juridicos possivelmente sigilosos e dados pessoais de clientes e colaboradores. Transparencia sobre o monitoramento e uma condicao necessaria, mas nao basta por si so: definir finalidade, base legal, proporcionalidade, politica de acesso e periodo de retencao com responsavel apropriado.

## Padroes fechados

- Modo inicial: DEMO. Captura real desabilitada ate configurar allowlist e obter autorizacao do piloto.
- Janela de coleta: expediente limitado e prazo final automatico.
- Credenciais, telas de login, apps pessoais, bancos, gerenciadores de senhas e campos de senha devem ser excluidos e testados; detectar janela sensivel deve suspender prints.
- Nao registrar valores de formularios, conteudo de teclas, clipboard ou corpos de mensagens.
- Screenshots em armazenamento protegido; mascara automatica nao garante que todos os dados foram ocultados. Exportacao deve requerer revisao.
- Dados individuais protegidos; analise por processo de trabalho, nao vigilancia punitiva de pessoas.
- Proibir uploads automaticos para IA e fontes de telemetria externas.
- Nenhum dado real em Git, CI, logs de teste ou issue tracker.
- Retencao configuravel, expurgo rastreavel e backups com prazo compatível.

## Modelo de ameacas resumido

- Vazamento por capturas: mitigacao por allowlist, mascaramento, segregacao e expurgo.
- Exposicao de servidores: autenticar sincronizador, TLS, minimo privilegio, sem portas abertas desnecessarias.
- Coleta fora do expediente: janelas temporais e desligamento pelo usuario.
- Manipulacao de eventos: IDs, hashes de lote e trilha de auditoria; nao tratar capturas como prova incontestavel.
- Falha de conectividade: fila local com limite e politica clara de descarte.

## Gate do piloto real

Aprovacao expressa do responsavel do escritorio, comunicacao documentada a todos participantes, escopo de dados, versao do coletor revisada, teste com dados ficticios, procedimento de parada imediata, retencao e politica para incidente de seguranca.
