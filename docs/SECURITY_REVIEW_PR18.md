# Pacote para revisão independente de segurança do PR18

## Identidade e estado

Alvo congelado: PR18, codex/verified-owned-channel,
233b3011cba6a9647bcf5e98d0a18e551b29fe3c; base PR16/294cb390a17b.
CI final original: https://github.com/almirfsneto/observador-escritorio/actions/runs/41814854038
Código runtime anterior0588d8a/CI41814049436, mesmas provas descritas em PROGRESS.
A nova branch codex/acceptance-stabilization contém uma correção incremental de
cleanup; revisar seu diff separado, sem alterar PR18 ou presumir aprovação dele.

**REVISÃO INDEPENDENTE PENDENTE.** Este pacote e a análise do próprio implementador
não são assinatura externa. Não foi enviado convite/mensagem a terceiros. Pessoa
independente deve registrar identidade funcional, data, SHAs efetivamente lidos,
ambientes, casos executados, achados, severidade e decisão em canal autorizado.
Não publicar chaves, frames, nomes de usuário ou JSON do operador no repositório.

## Distribuição proposta de trabalho

| Responsável a designar | Escopo | Saída exigida |
| --- | --- | --- |
| Revisor de segurança independente do autor | threat model, protocolo, capacidade/herança e dados | Checklist com achados e decisão por SHA, sem alegar isolamento não provado |
| Revisor Windows independente | reproduzir Win32/kill/cancelamento e testes entre contas/sessões autorizadas | Comandos, OS/Python, contagens e falhas; distinguir CI de desktop humano |
| Mantenedor | relacionar achados a correções revisáveis e matriz de aceite | Pendências priorizadas, sem merge/ativação automática |

A designação depende de pessoa autorizada disponível; não foi simulada. Revisores
podem trabalhar em paralelo em checkouts descartáveis, sem modificar branches.

## Leitura e reprodução

Ler AGENTS, SPEC, SECURITY, OWNED_CHANNEL.md, SOURCE_AUTHENTICATION.md,
OFFLINE_BRIDGE.md, INBOX_RETENTION.md, STACK_REVIEW_PLAN.md e os testes associados.
Usar diff PR18 contra PR16 e snapshot completo: owned_channel.py,
owned_channel_win32.py, owned_channel_child.py e módulos de protocolo relacionados
(ver nomes reais com rg --files src/observador). Ler também a correção filha.

```
git fetch origin codex/verified-owned-channel
git switch --detach 233b3011cba6a9647bcf5e98d0a18e551b29fe3c
PYTHONPATH=src python -m unittest discover -s tests -v
```

PowerShell: `$env:PYTHONPATH='src'`, depois `python -m unittest discover -s tests -v`.
Usar checkout separado para testar a entrega filha no SHA fixado no PR. Não executar
reset/rebase/merge para compor versões. Preparar dependências/build conforme CI
em máquina dedicada; não instalar o observador na equipe. CI Windows não é teste
humano Win10/11. Skips exigem motivo e cobertura alternativa explícita.

## Checklist de decisão, todos ainda sujeitos à revisão independente

- [ ] Quatro handles explícitos, identidades kernel/Popen retido, flags de herança
  limpas e probes descendente/decoy comparando objetos, não números de handles.
- [ ] Chave efêmera criada após spawn/verificação, só bootstrap32+EOF; nenhuma
  chave em argv/env/arquivo/log. Limites da memória Python e mesmo token/admin.
- [ ] Wire fechado/canônico, limites de tamanho/capacidade, HMAC direcional e
  epoch/sessão/geração/nonce/sequência; replay/adulteração falham fechados.
- [ ] Cancelamento, kill do parent, job lifetime, exceções de cleanup e drenagem
  de futures; erro de CloseHandle não permite declarar shutdown confirmado.
- [ ] Janela de herança concorrente e risco de processo com mesmo privilégio
  explicitados; não presumir proteção contra injeção/duplicação por administrador.
- [ ] Reproduzir em outra conta/sessão autorizada; não criar contas/elevar ou
  contornar política sem autorização. Provas atuais não fecham esse gate.
- [ ] ACK IPC não significa pausa UIA nem commit de inbox. Adapter permanece OFF;
  modelo PR16 e fixture Python não autenticam WindowsObserver C# legado.
- [ ] Retenção/replay e limites persistentes revisados sem resetar DB; SQLite
  ativo em claro, quota lógica e ausência de apagamento forense reconhecidos.
- [ ] Sanitização dos relatórios/companion: enums/contagens, ausência de motivos
  livres e dados pessoais, hash não é assinatura nem prova de procedência.
- [ ] Falha histórica de prontidão Windows3.12/CI41811218903 registrada; rodadas
  seguintes aprovadas não provam causa original nem eliminam análise de flakiness.

## Achado incremental da autorrevisão

**SR-01: erro ao fechar um recurso podia interromper o restante do cleanup.**
No PR18, OSError de job.close/CloseHandle/cancelamento podia pular outros handles,
futures ou join. Impacto: término incompleto e diagnóstico insuficiente. Não é
causa demonstrada de dropped=1 do PR6: componente e protocolo são distintos.

Correção filha: tentar todos os fechamentos, concluir futures, tentar join mesmo
com cancelamento falho; shutdown_confirmed=false, cleanup_errors agregado e
cleanup_unconfirmed. Slot numérico de handle retido não é reutilizado após falha.
Testes portáveis injetam OSError em múltiplos recursos e cancelamento. São FALHAS
INJETADAS; os testes normais Win32 reais permanecem exigidos na CI. O revisor deve
avaliar possíveis handles não liberados quando o próprio kernel falha, risco que
o código agora expõe e não promete resolver por retry de ownership incerto.

## Encerramento da revisão

Exigir decisão independente por SHA e disposição de cada achado; casos obrigatórios
executados, falhas corrigidas e CI do candidato aprovada. Bloqueios de conta/sessão
ou desktop humano permanecem abertos se não houver ambiente autorizado. Revisão
concluída não autoriza merge, adapter, transmissão, coleta real ou piloto. Plano
de consolidação é somente documental em STACK_REVIEW_PLAN.md.
