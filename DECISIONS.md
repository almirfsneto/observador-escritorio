# Log de decisoes

## D-001 - Repositorio independente
- **Decisao:** Scaffold criado sem importar codigo de DeskMate/SmartRPA/OpenAdapt.
- **Motivo:** verificacao de licenca e seguranca deve preceder integracao.
- **Revisar se:** comparacao de bibliotecas comprovar melhor opcao.

## D-002 - Captura de eventos, nao video
- **Decisao:** metadados de atividades e prints seletivos, sem video continuo.
- **Motivo:** cinco ou mais dias de trabalho, custo de armazenamento e pesquisa.

## D-003 - Privacidade por padrao
- **Decisao:** nao capturar texto integral de entrada, credenciais nem clipboard.
- **Motivo:** estes dados nao sao necessarios para reconstruir procedimentos e criam risco elevado.

## D-004 - Analise inicial deterministica
- **Decisao:** detector basico de sequencias sobre eventos ficticios.
- **Motivo:** criar contrato testavel antes de componentes IA.
