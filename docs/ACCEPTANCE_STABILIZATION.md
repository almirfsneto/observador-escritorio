# Estabilização do aceite — evidência Windows 11 e correções incrementais

Base: PR18/233b301, branch nova codex/acceptance-stabilization. PR6 continua em
3d4a77052b3dc9cf77805dd73f0bfd6d5dae674c. Nenhuma branch anterior é modificada.
Não é nova captura, adapter, piloto ou migração do JSON local do operador.

## Evidência recebida e alcance

O responsável informou primeiro aceite humano sintético Windows11 na versão do
PR6: três ensaios, dois encerrados por expiração, três limpezas confirmadas,
persistência opt-in funcional e avaliações humanas positivas. É evidência positiva
DECLARADA de execução humana daquela versão, com ressalvas. O JSON original não
foi solicitado, lido, copiado, anexado ou versionado. Não inventamos build/edição,
contagens adicionais, hashes/commit, nome do teste ignorado ou assinatura de revisão.
Fixtures de regressão reproduzem esse padrão com dados construídos, não com o
arquivo do operador. O resultado não valida automaticamente PR18 ou esta branch.

## Quatro ressalvas

| Ressalva | Diagnóstico | Correção proposta nesta branch | O que ainda falta |
| --- | --- | --- | --- |
| Native dropped=1 | Agregado de saúde; pode incluir falha de callback, fila de foco/saída ou mensagem de saúde/ACK. Não prova qual ação foi perdida ou taxa de perda | Diagnóstico sinaliza descarte/causa desconhecida; novas sessões registram somente amostras cacheadas, erros e profundidades/idade/fase Python observada | Repetição controlada WPF, contagens por etapa; investigar ocorrência sem zerar/suprimir contador |
| Um teste ignorado | PASSOU no v1 significa sucesso dos executados; não cobertura completa. Nome/motivo não foram fornecidos | Runner local emite categorias fechadas no fim; UI mostra executados/ignorados. Todos skipped, contagem inconsistente ou resumo ausente não ganham PASSOU | Identificar categoria do caso relevante e executar/justificar lacuna; não adivinhar qual foi |
| Commit ausente no ZIP | Comportamento esperado sem Git; PR6 é atribuição declarada, não commit verificado | Não inventar SHA. source_state exige .git na raiz e toplevel correspondente: ZIP aninhado não herda commit de outro repositório | Futuro ensaio com checkout exato/limpo e hashes registrados, sem alterar o arquivo histórico |
| windows11_trial_required após ensaio Win11 | Bug de orientação: ambos os OS eram adicionados incondicionalmente | Remover só a exigência de execução do OS atual quando há origin operator_guided, sessão iniciada e alguma avaliação humana. Ambiente sozinho/CI/checkbox sem sessão não bastam | Revisão humana continua pendente; falhas/manuais incompletos permanecem explícitos, Win10 exige ensaio próprio |

Na fonte congelada PR6, skips condicionais em Windows incluem os ensaios de
foreground de test_acceptance_windows, test_windows_controller e
 test_windows_desktop. Isso limita hipóteses; não identifica o caso do operador,
principalmente sem SHA verificável. Não atribuir o skip a symlink/browser de PRs
posteriores que não existiam naquela versão. Não atribuir dropped=1 ao canal
Python de PR18, que é outra entrega/protocolo e permanece sem adapter.

## Compatibilidade e diagnósticos novos

ACEITE_REPORT_SCHEMA.json v1 e VALIDAR_LABORATORIO.cmd permanecem byte a byte.
O cálculo de gaps é corrigido só aqui; não reescreve o JSON original nem concede
aceite. human_gate=PENDENTE_REVISAO_HUMANA e pilot_authorized=false sempre.
A remoção do gap significa execução DECLARADA neste OS, inclusive se o ensaio
falhou; não significa aprovação. Falhas e itens não avaliados exigem revisão/
repetição e estão nos próprios campos e no diagnóstico complementar.

A exportação futura salva o v1 e um diagnostico-<id>.json fora de Git, sem upload.
Schema separado: ACCEPTANCE_REVIEW_SCHEMA.json. Só agregados/enums e SHA256 do
v1 canônico; hash liga arquivos, não autentica operador/código. Sem IDs de processo,
host/usuário, paths, eventos, conteúdos ou motivos livres de skip. Mesmo se o
arquivo complementar falhar, UI informa que o v1 foi salvo, sem alegar perda.
Não há importador/CLI para recolher o JSON antigo. Usar apenas dados fictícios.

NativeHealthObservation conta amostras distintas do cache já existente, sem SQL,
UIA extra ou novos campos do provider. Pico é das amostras, não contínuo. Fase é
Python quando o aumento foi observado, não geração/causa do descarte nativo.
Nenhuma amostra => highwater=null, não zero inventado. Health final nunca é
confirmada pelo contrato atual, mesmo com cleanup confirmado. Counters de
lifetime/fases diferentes não podem produzir uma taxa de perda de usuário.

O packet do runner local contém contagens e categorias fechadas: foreground,
plataforma Windows, browser dedicado, privilégio de symlink e unclassified.
Exige schema/contagens consistentes; packet ausente/legado fica unclassified,
não reconstrói causa. Identificadores/reasons do unittest não entram nos JSONs.
Os testes browser do núcleo continuam skips de cobertura separada, não aprovados
por este validador offline. A CI executa Chromium em job dedicado.

## Encerramento desta estabilização

1. CI Linux/Windows3.11/3.12 e Chromium aprovadas no HEAD, skips discriminados.
2. Regressões do padrão de três ensaios, flags por OS, skips, ZIP/Git ancestral,
   saúde amostrada, exportação parcial e cleanup adversarial passam.
3. Matriz por OS atualizada sem transferir aceite de versão ou transformar CI em
   humano. Relato Win11 permanece com ressalvas até origem/skip/descarte revistos.
4. Revisor independente conclui pacote SECURITY_REVIEW_PR18.md e assina decisão
   em canal autorizado; esta implementação não é essa revisão.
5. Sem adapter/piloto/merge/rebase; pendências de Win10, nova versão e segurança
   continuam abertas. Futuro operador não precisa enviar JSON para Git: comunicar
   apenas contagens/enums/versão em canal autorizado, mantendo artefato local.
