# RETOMADA AUTÔNOMA

## Checkout e dependências

Repositório almirfsneto/observador-escritorio. Não usar main isolado.
Sequência de rascunhos: PR1 → PR2 → PR3 → PR4 → PR6 → PR7 → PR8 → PR9 → PR10.
Branches novas:
- PR7: codex/storage-reliability (base codex/guided-windows-acceptance).
- PR8: codex/windows-coverage-probe (base codex/storage-reliability).
- PR9: codex/synthetic-browser-extension (base codex/windows-coverage-probe).
- PR10: codex/task-discovery (base codex/synthetic-browser-extension).

Para continuidade integrada, buscar codex/task-discovery e criar outra branch
sobre seu HEAD, conferindo PR/CI atuais. Não atualizar PRs anteriores nem integrar
PRs sem instrução. Ler AGENTS/SPEC/SECURITY/ROADMAP/PROGRESS/DECISIONS completos,
STORAGE_HARDENING/WINDOWS_COVERAGE/WEB_EXTENSION/TASK_DISCOVERY e questões Pro.

## Reproduzir sem coleta real

`PYTHONPATH=src python -m unittest discover -s tests -v`

Windows CI compila três csproj .NET 8 e executa a mesma suite. Native UIA e
ACL/DPAPI exigem Windows real; testes Linux ignorados não os substituem.
Browser real: Playwright 1.62.0 (somente teste) e Chromium descartável instalado
no job web-synthetic, OBS_BROWSER_TEST=1; no executor a política bloqueia unpacked,
não alterar política nem contorná-la. Núcleo não precisa Playwright para operar.

`python -m observador.task_discovery --out /pasta/fora-do-git/candidatos.json`

Use nome novo (criação exclusiva). `VALIDAR_LABORATORIO.cmd` permanece entrada
compatível do operador, sempre desativado até ação explícita. Não instalar
agentes/extensões em navegadores/computadores de colaboradores.

## Evidências e limites para não reinterpretar

PR7: CI 41741273177 (ACL/DPAPI Windows reais, quota/rollback/corrupção); revisão
posterior recusa WAL/SHM e tenta symlink real. PR8: 41741819622 (WPF30/30,
WinForms0/30, probe conservador sem ganho de cobertura). PR9: 41742054304
(cinco jobs, Chromium151 real com 27 eventos sanitizados). PR10: conferir CI do
HEAD atual antes de declarar sucesso; registros atualizados em PROGRESS/PR.

SQLite ativo NÃO cifrado. Arquivo DPAPI não cifra origem, pagefile ou backups.
Orçamento/reserva não é quota física de volume contra admin/outro programa.
Sem callback a latência é null, não zero. Submissão após shutdown é descarte
contado. WAL/SHM legado não é migrado silenciosamente. Corrupção não reseta DB.
WinEvent STATECHANGE não é Invoke nem clique; não alimentar ui_action com isso.
Minerador não soma famílias como execuções independentes, não exporta alvos e
não transforma span em tempo de trabalho/ganho. Economia é cenário opcional.

## Próxima tarefa autônoma recomendada

Adicionar contrato de diagnóstico fechado para saúde/filas/storage (incluindo
orçamento e amostras indisponíveis), sem alterar schema de aceite v1; testar
consistência de contagens em falhas e picos de journal por fault injection.
Depois planejar integração web/agente com ACK/deduplicação/proveniência e teste
sintético de suspensão/reinício real do worker MV3. Para WinForms, investigar um
adapter explícito de API/semântica; não ativar hooks globais ou inferir cliques.
Para mineração, ampliar corpus de casos negativos e revisar falsos agrupamentos,
ordenação multi-canal, benchmark e calibração antes de qualquer interpretação.

Não aguardar aceite humano para tarefas independentes; também não declarar esse
aceite feito. Sem dados reais, screenshots reais, telemetria, servidores externos,
autostart, custos, deploy, merge ou piloto. Windows10/11 e Chrome/Edge humanos,
revisão independente/ACL outra conta e governança permanecem gates necessários.
