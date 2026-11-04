# Matriz objetiva de aceite por sistema operacional

Atualização: estabilização filha do PR18/233b301. Status humano é separado de CI.
O relato do responsável é evidência humana declarada, não um relatório auditado
ou prova do commit exato. Não solicitar o JSON do operador para o repositório.

| Ambiente / versão | Evidência disponível | Status de aceite e lacunas | Critério de encerramento |
| --- | --- | --- | --- |
| Windows 11 / versão declarada PR6 | Relato humano: 3 ensaios, 2 expirações, 3 cleanups, persistência opcional funcional, avaliações positivas | EXECUÇÃO HUMANA RELATADA COM RESSALVAS; SHA ausente por ZIP, dropped=1, skip=1; indicador Win11 incorreto | Revisar ressalvas sem reescrever histórico; repetir casos afetados em origem verificável e registrar resultado sanitizado |
| Windows 10 / PR6 | Nenhum ensaio humano informado | PENDENTE; relato Win11 não cobre Win10 | Mesmo roteiro visível de pausa, fim, expiração, persistência e limpeza em laboratório dedicado |
| Windows 10 / versão candidata nova | Testes portáveis e contrato, sem desktop humano Win10 nesta execução | PENDENTE | Checkout limpo identificado, CI do SHA e roteiro humano completo após revisão |
| Windows 11 / versão candidata nova | Regressões automatizadas do padrão relatado; não execução humana desta versão | PENDENTE | Repetir roteiro visível e validar novo diagnóstico, incluindo skip/descarte e proveniência; não herdar aceite PR6 |
| Windows Server 2025 / runner CI | Win32, processos/handles, UI sintética e testes por Python 3.11/3.12 | SOMENTE AUTOMATIZADO; não substitui Windows10/11 humano, outra conta/sessão, suspensão/energia | Todos os casos aplicáveis executados; cada skip tratado como lacuna; conferir run do HEAD |
| Linux / runner CI e workspace | Núcleo, protocolos, regressões e falhas injetadas | SOMENTE AUTOMATIZADO; casos nativos Windows ignorados | Núcleo aprovado; skips Windows cobertos em jobs Windows, não convertidos em sucesso Linux |
| Chromium descartável / CI Linux | Dois testes reais da extensão sintética em job dedicado | SOMENTE AUTOMATIZADO; não aceite humano Chrome/Edge no Windows | Dois casos executados sem skips; políticas/instalação humana continuam separadas |

## Protocolo mínimo por versão e OS suportado

1. Máquina de laboratório autorizada, aplicações fictícias e indicador visível.
   Registrar OS real, origem e SHA quando Git disponível; ZIP sem SHA fica desconhecido.
2. Executar o guia VALIDACAO_MANUAL_WINDOWS.md. Registrar testes descobertos,
   executados e ignorados, não apenas PASSOU. Sem resumo/execução, preparação falha.
3. Conferir pausa/retomada/fim/expiração, limpeza em cada ensaio e persistência
   opcional. Não produzir dados reais nem ligar o adaptador novo.
4. Novo diagnóstico registra amostras nativas e categorias de skip. dropped>0
   exige investigação; não declarar taxa/perda de ação a partir do agregado.
5. Manter JSONs fora de Git. Comunicar apenas versão/OS, contagens, enums e ressalvas
   em canal autorizado. Ausência de commit não é corrigida com SHA presumido.
6. Revisor humano avalia itens falhos/não executados e evidências locais. Fechar
   requisito de execução Win11 não fecha segurança, Win10 ou autorização de piloto.

Gates globais: revisão independente PR18 e correção filha, outra conta/sessão
Windows autorizada, armazenamento ativo em claro/quota lógica, cobertura WPF vs
WinForms e adapter OFF. Ver SECURITY_REVIEW_PR18.md e STACK_REVIEW_PLAN.md.
