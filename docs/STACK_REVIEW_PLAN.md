# Plano de consolidação e revisão independente — Issue 17

**Somente plano. Nenhum merge, rebase, squash, retarget ou reescrita de PR anterior executado.**
PR6 permanece congelado para aceite humano. O trabalho atual altera somente a nova
branch codex/verified-owned-channel, filha de PR16/294cb390a17b.

## Inventário capturado para revisão

Todos os PRs abaixo foram consultados pela API GitHub e estavam em rascunho.
O SHA de PR18 na tabela é a primeira entrega; consultar seu HEAD final/CI no PR.
Os demais devem permanecer exatamente nesses commits durante esta execução.

| PR | Branch | SHA consultado | Base |
| --- | --- | --- | --- |
| #1 | `codex/windows-lab-foundation` | `15e1e6dd25a4` | `main` |
| #2 | `codex/visible-windows-laboratory` | `598e8e6ee42b` | `codex/windows-lab-foundation` |
| #3 | `codex/persistent-laboratory` | `8c76fb9acce1` | `codex/visible-windows-laboratory` |
| #4 | `codex/bounded-laboratory-queue` | `b06b624dfc86` | `codex/persistent-laboratory` |
| #6 | `codex/guided-windows-acceptance` | `3d4a77052b3d` | `codex/bounded-laboratory-queue` |
| #7 | `codex/storage-reliability` | `fa04785b932c` | `codex/guided-windows-acceptance` |
| #8 | `codex/windows-coverage-probe` | `805c7913353b` | `codex/storage-reliability` |
| #9 | `codex/synthetic-browser-extension` | `fdec952a015a` | `codex/windows-coverage-probe` |
| #10 | `codex/task-discovery` | `502d6d36b33a` | `codex/synthetic-browser-extension` |
| #12 | `codex/closed-lab-diagnostics` | `b9cb6ec77d79` | `codex/task-discovery` |
| #13 | `codex/offline-source-bridge` | `cf90de6fd596` | `codex/closed-lab-diagnostics` |
| #15 | `codex/inbox-retention` | `cb16d85d3a0f` | `codex/offline-source-bridge` |
| #16 | `codex/synthetic-source-auth-model` | `294cb390a17b` | `codex/inbox-retention` |
| #18 | `codex/verified-owned-channel` | `22f99e5b9603` | `codex/synthetic-source-auth-model` |

Cadeia: #1→#2→#3→#4→#6→#7→#8→#9→#10→#12→#13→#15→#16→#18.
Ausência de números intermediários não representa dependência extra.
Não rebasear nem retargetar PR6 para simplificar a cadeia. Seu commit completo
é3d4a77052b3dc9cf77805dd73f0bfd6d5dae674c. Preservar branch e artefatos de aceite.

## Pacotes de revisão propostos, sem alterar branches

| Unidade conceitual | PRs | Foco do revisor independente |
| --- | --- | --- |
| Fundação/captura/fila | 1–4 | Schema, allowlist, PID/criação/caminho, callback UIA, gerações, EOF, limites |
| Aceite humano congelado | 6 | Roteiro Win10/11, hashes/versões, pausa/fim/15min, relatório v1 sanitizado |
| Armazenamento e saúde | 7,12,15 | ACL, plaintext/DPAPI de arquivo, quota lógica, invariantes, commit incerto e replay após purge |
| Cobertura/web/mineração | 8–10 | WPF vs WinForms, MV3/CSP/allowlist, worker real, sem conteúdo/causalidade/economia inventada |
| Contratos e autenticação sintética | 13,16,18 | Arquivos declarativos vs modelo vs capacidade de processo real, entrega de chave, herança, wire e threat boundary |

Essas unidades são leituras agrupadas dos diffs existentes, NÃO novos PRs nem um
squash executado. O revisor usa o diff de cada PR contra sua base, evitando revisar
a mesma dependência como mudança nova. Revisão de integração lê também o snapshot
final completo e contratos cruzados, porque diffs isolados podem perder invariantes.

## Ordem de gates antes de qualquer convergência futura

1. Fixar SHAs/manifesto/CI final de cada unidade, checar cadeia e integridade dos
   arquivos; guardar apenas evidência sanitizada, nunca chaves/frames/dados reais.
2. Revisão independente de segurança/runtime: marcar afirmações como comprovada
   em processos reais, contrato/modelo, fault injection, lacuna ou teste humano.
   Exigir explicação do limite de mesmo token/admin e ausência de adapter no PR18.
3. Reproduzir testes portáveis, Win32 real e Chromium em checkout descartável. Os
   skips são lacunas por plataforma; caso obrigatório não executado não ganha PASSOU.
4. Operador executa PR6 em Windows10/11 dedicados e conserva relatório v1 fora de
   Git. Não transferir automaticamente o aceite daquele SHA para PR18. Repetir
   manualmente a versão candidata depois de revisada, se futuramente autorizada.
5. Revisão adversarial em outra conta/sessão Windows autorizada, sem criar contas,
   elevar, instalar ou contornar políticas nesta execução. Verificar ACL/handle
   theft/parent crash, limites do token e cancelamento. Não afirmar isolamento de
   mesmo privilégio a partir de testes negativos de JSON/HMAC.
6. Só com revisão explícita, definir estratégia de convergência futura: preservar
   histórico original, aprovar dependências em ordem e elaborar candidato separado
   e revisável. Qualquer merge/retarget/squash/rebase futuro exige autorização; este
   documento NÃO a fornece. Depois de cada mudança aprovada de composição, reexecutar
   CI e revisar conflitos/manifesto, nunca apenas confiar em CIs de componentes.
7. Liberação de adapter e eventual piloto são decisões separadas: canal da fixture
   não autentica WindowsObserver C# antigo, fila ativa continua em claro e quota
   não é física. Gate humano/LGPD, cobertura por app e segurança ainda pendentes.

## Matriz mínima de evidências do canal

| Afirmação | Evidência / natureza | Limite |
| --- | --- | --- |
| Canal/segredo chegam ao filho pretendido | Popen retido + identidades kernel + lista4 + chave criada após spawn + HMAC de ida/volta, Windows real | Capacidade herdada; não GetNamedPipeClientProcessId nem isolamento de mesmo token/admin |
| Descendente/decoy não herdam handles | Probes Win32 reais com herança irrestrita fora da janela controlada | Flags/casos exercitados; código concorrente arbitrário no parent não é isolado |
| Wire fecha em adulteração/replay | Portáveis + processos adversariais reais no Windows | Sem prova formal ou fuzz exaustivo |
| Pause/TTL/kill/cancelamento | Fixture IPC real, curta expiração natural; fases/ACK fechados | Não ACK UIA nem teste humano15min |
| Receipts24h/markers permanentes | SQLite real + relógio INJETADO, limites1024/10000/32 reais e reabertura | Não24h físicas, não exactly-once distribuído nem quota OS |
| WindowsObserver/UIA real | Ensaios anteriores WPF30/30 e WinForms0/30 | Não foi autenticado por este canal novo |
| PR16 HMAC em memória | Modelo e negativos portáveis | Não autenticação de processo |
| Outra conta/Win10/11 humano | PENDENTE, sem credenciais/desktop humano nesta execução | Nenhuma aprovação inferida do CI Server2025 |

Consultar PROGRESS.md e OWNED_CHANNEL.md para hashes/runs e resultados exatos do
HEAD, inclusive as primeiras falhas/correções que eventualmente ocorram. Não usar
o plano como autorização de merge, instalação, transmissão, coleta ou piloto.

