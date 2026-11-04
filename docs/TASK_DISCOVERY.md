# Descoberta de microtarefas — somente corpus sintético

O detector legado `discover_patterns` e comandos anteriores continuam intactos.
`discover_tasks` acrescenta projeção fechada, normalização por categoria de app,
tipo/ação/papel (nunca alvo ou ID efêmero), deduplicação por UUID com rejeição de
conflitos, segmentação por sessão/gap (30s) e corte em 64 eventos. Ordena UTC e
source_sequence; empate sem sequência usa ordem de entrada, não UUID aleatório.

Enumera sequências **contíguas** de 2–8 etapas. Contagens exatas usam intervalos
não sobrepostos. Suprime subpadrão fechado só se todas suas ocorrências estiverem
cobertas por um padrão exato maior recorrente. Agrupa variações a distância de
edição <=1, similaridade >=0,7 e mesmas âncoras de início/fim, sem alinhamento
transitivo ilimitado. Dentro de cada família, interval scheduling evita contar
variantes sobrepostas como execuções separadas. Famílias candidatas diferentes
são alternativas: seus totais não devem ser somados como execuções independentes.

O ranking usa frequência e extensão de sequência, depois duração observada. O
span entre primeiro/último evento não é tempo de trabalho efetivo e inclui espera.
Confiança high/moderate/low é **heurística**, baseada em suporte/sessões e semântica
conhecida, não probabilidade calibrada. UIA genérico Invoke/click/toggle recebe
baixa confiança: normalizar papel não descobre significado de botões iguais.
Retornos A-B-A e operações adjacentes repetidas são sinais para revisão, nunca
prova de retrabalho, qualidade ou produtividade individual.

Economia fica `null` por padrão. Se o chamador fornece tempo hipotético de
automação, o relatório calcula somente cenário: soma max(0,span-hipótese), com
scenario_only=true/feasibility_validated=false. Não promete viabilidade ou ganho.

Limites: 10 mil entradas, 50 mil fingerprints, até 200 candidatos revistos e
20 famílias no relatório, etapas de duração <=60s. Limitação de candidatos gera
lacuna explícita. Sem IA, serviço, dependência externa ou captura. Apenas fontes
marcadas sintéticas/demo/laboratório e aliases fixos; relatório não exporta IDs,
nomes, paths, alvos ou timestamps individuais. Rejeitar dados não equivale a
anonimizar qualquer dataset real. Não usar para classificar colaboradores.

## Demonstração

`python -m observador.task_discovery --out /pasta/fora-do-git/candidatos.json`

Opcional: `--scenario-automation-seconds 0.2`. Arquivo exclusivo, fora de qualquer
Git. Corpus: oito rotinas fictícias, 36 eventos, dois tipos de variação (revisão
extra/renomeação repetida), sem informações de clientes. Resultado: primeira
família baixar/renomear/mover/cadastrar com oito ocorrências, oito sessões e três
variantes. Detector legado no mesmo corpus: zero padrões (IDs diferentes por
sessão); novo motor: cinco famílias candidatas, alternativas/não aditivas.
450 eventos/100 rotinas foram processados localmente em cerca de 0,012s; isto é
medição pontual do executor, não SLA nem benchmark Windows/produção.

## Comparação técnica de alternativas livres

| Abordagem | Capacidades | Limite para este caso | Decisão |
| --- | --- | --- | --- |
| N-gramas legados | Contíguos, alvos exatos, mediana | IDs efêmeros impedem ligação entre sessões, sobreposição | Mantidos por compatibilidade |
| Motor desta entrega | Roles/ações, sessões, variantes edit<=1, não sobreposição, lacunas | Sem causalidade, descoberta de modelo de processo ou calibração | Implementação original limitada |
| PrefixSpan-py | Mineração frequente de subsequências/projeções, top-k/closed | Não contíguas podem misturar tarefas; gap/overlap/privacidade exigem camada própria | Não incorporado |
| PM4Py | Descoberta/conformidade de processos, modelos e event logs | Requer conceito de case, dependências científicas e governança; não resolve semântica de controles | Não incorporado |

Consulta verificável ao GitHub em 2026-11-03: PrefixSpan-py MIT, commit
`1c7abd7b4cb24423a850bfa23fc028ba039922bd`; PM4Py AGPL-3.0, commit
`a193a9bd580ff01b3778e37c7d5e0b9021d23c75` (release). Referências:
https://github.com/chuanconggao/PrefixSpan-py e
https://github.com/process-intelligence-solutions/pm4py. Licenças verificadas no
metadata dos repositórios; dependências transitivas não auditadas. Nenhum código,
artefato ou biblioteca incorporado. Comparação é arquitetural/funcional e com
baseline próprio, não benchmark executado dessas bibliotecas. Uma integração
futura exige auditoria de licença/versão/transitivas e comparação quantitativa.
