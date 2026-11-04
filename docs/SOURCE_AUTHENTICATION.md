# Autenticação de fontes — análise e modelo sintético / Issue 14 P2

Atualização Issue17: existe canal IPC isolado de processos reais descrito em
OWNED_CHANNEL.md. Este documento descreve o MODELO de PR16; não promover suas
premissas a evidência de canal. Provider C#/adapter e bridge de arquivos continuam
sem autenticação integrada. Plano de revisão: STACK_REVIEW_PLAN.md.

**Estado deste modelo PR16: especificação, simulador e preflight de identidade.
O canal real ISOLADO de PR18 está em OWNED_CHANNEL.md; nenhum adaptador
controlador→inbox foi ligado.** Modelar HMAC
não autentica arquivos/processos. A alternativa segura da Issue14/P2.6 é aplicada:
sem prova integrada de origem do peer, não habilitar transporte. P1/PR15 permanece
independente e funcional, com testes de durabilidade/anti-replay próprios.

## Ameaças e fronteiras

| Ator / falha | Risco no bridge de arquivos | Tratamento / lacuna |
| --- | --- | --- |
| Processo sem ACL do diretório | Ler/adulterar inbox/tickets | Diretório privado/DACL usuário+SYSTEM e recusa de links; adversarial entre contas Windows ainda pendente |
| Outro processo do mesmo usuário | Forjar source, ticket, ACK; SHA recalculável; ler memória/chaves | Hash não é MAC. ACL/DPAPI usuário não isolam mesmo token. NÃO alegar proteção contra esse ator |
| Administrador/debugger/código injetado | Trocar binário, handles, tempo, banco, chave | Fora da garantia; não há defesa provada |
| Arquivo adulterado/versão incorreta | Autorizar origem inventada ou misturar sessão/slot | Schema fechado evita campos extras, não autentica emissor; transferência manual ainda requer confiança local |
| Replay/receipt expirado | Reinserir histórico ou inventar inexistência de commit | Markers/high-water P1; ACK só dentro de 24h, após isso erro fechado |
| PID reciclado / executável homônimo | Aceitar processo de outra vida | Handle próprio + PID/criação/caminho/sessão; lookup baseado no PID recebido é insuficiente |
| Path/reparse/hardlink / corrida | Trocar fonte/armazenamento | Recusa de links; sem solução TOCTOU contra mesmo privilégio, assinatura/código confiável ainda requer revisão |
| Pipe squatting / remoto / outra sessão | Endpoint falso, confusão de servidor/cliente | FIRST_PIPE_INSTANCE, REJECT_REMOTE_CLIENTS, DACL por logon SID; verificar ambos peers no kernel antes de negociar |
| Cache/restart/clock/pause | Reusar prova antiga, key persistida, ACK confundido | Epoch/challenge efêmeros, gerações, sessão monotônica, novo pareamento explícito; ACKs têm escopos separados |
| Flood, frames truncados, silêncio | CPU/memória/handles ilimitados, thread UI presa | Framing e limites antes de parse, bounded queue, timeout/cancelamento; simulador não demonstra limites físicos de IPC |

## Alternativas e decisão conservadora

1. **Arquivos + SHA atual:** nenhuma autenticação de origem. Acrescentar HMAC em
   arquivo sem canal privado para pareamento apenas move o segredo para outro
   arquivo; rejeitado como integração segura.
2. **Pipes anônimos herdados de filho próprio:** melhor primeiro caminho para o
   provider já iniciado pelo controlador (NativeSession). Sem endpoint público,
   parent possui Popen/handles, stdin/stdout são privados à árvore controlada.
   Ainda provar herança mínima, EOF/cancelamento e associação entre mensagens,
   geração e identidade do mesmo handle; processo de mesmo usuário pode atacar.
3. **Named pipes Windows nativos:** opção para componentes separados, com mais
   superfície e testes. Exige peer PID/sessão do kernel nos dois lados, DACL por
   logon SID, recusa de remoto/colisão e restrições de impersonation. Não basta
   aceitar PID/source do JSON nem token passado por argumento/arquivo público.
4. **Loopback TCP:** rede/firewall/portas e autenticação adicional desnecessárias
   nesta fase; rejeitado. Sem serviço, autostart ou transmissão externa.
5. **Browser NativeMessaging:** avaliar só depois de host/manifest/extension ID,
   política allowlist e instalação revisados. Não instalar host; MV3 continua só
   origem fictícia e permissão storage. Arquivo/ACK browser continua não autenticado.

Não há licença/dependência externa nova nem código copiado. Referências de APIs:
[Named pipe security](https://learn.microsoft.com/windows/win32/ipc/named-pipe-security-and-access-rights),
[CreateNamedPipeW](https://learn.microsoft.com/windows/win32/api/winbase/nf-winbase-createnamedpipew),
[GetNamedPipeClientProcessId](https://learn.microsoft.com/windows/win32/api/winbase/nf-winbase-getnamedpipeclientprocessid),
[GetNamedPipeServerProcessId](https://learn.microsoft.com/windows/win32/api/winbase/nf-winbase-getnamedpipeserverprocessid),
[QueryFullProcessImageNameW](https://learn.microsoft.com/windows/win32/api/winbase/nf-winbase-queryfullprocessimagenamew),
[GetProcessTimes](https://learn.microsoft.com/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocesstimes).
São referências da especificação; não alegar implementação de named pipe.

## Protocolo proposto antes de qualquer integração

- Inicialmente desativado; operador abre fixture WPF e autoriza apenas seu
  processo próprio. Pin do provider e fixture por handles/PID/criação/caminho
  absoluto esperado + sessão Windows. Mesmo nome de exe não basta. Hash de
  release revisado não substitui isolamento de administrador/mesmo token.
- Endpoint suportado Windows deve verificar identidade **do peer do canal**,
  comparando-a com os handles previamente possuídos. Para named pipe verificar
  PID do client/server com API do kernel e ProcessIdToSessionId; não confiar no
  handshake. DACL restrita ao logon SID e SYSTEM; servidor rejeita clientes
  remotos. Cliente recusa servidor inesperado; colisão de endpoint fecha, sem
  fallback a nome genérico. Impersonation limitada e sempre RevertToSelf em finally.
- Chave aleatória efêmera de 32 bytes entregue só por handle herdado específico
  ao filho possuído, nunca arquivo/CLI/environment/log. Herança explicitamente
  limitada; nenhum filho não autorizado recebe handle. Chave não serializada,
  não exportada nem confundida com chave do inbox. Não promete zeroização Python.
- Challenge aleatório 32 bytes, epoch UUID novo, identity completa, fonte Windows
  sintética, geração e prazo 5s; prova HMAC-SHA256 com domínio separado, canonical
  ASCII JSON. Uma tentativa inválida fecha imediatamente; sem fallback anônimo.
- Frame inclui epoch/challenge/generation/sequence, identidade e fonte vinculadas,
  batch fechado; MAC cobre tudo. Sequência estritamente crescente até 64 frames
  no modelo; restart fecha chaves/desconecta e exige novo consentimento/pareamento.
  Replay de transporte falha; retry durável de lote pertence ao inbox/receipt,
  em NOVO frame válido. Não repetir ações de UI automaticamente.
- Sessão <=900s monotônica, regression/EOF/timeout/identidade alterada fecham;
  pausa invalida frames pendentes, resume exige novo challenge/proof sem estender
  prazo. Controle de transporte **não** confirma pausa do producer. Só ACK do
  provider para geração solicitada, recebido pelo canal autenticado, poderia fazê-lo.
- Antes de parse: comprimento <=256KiB+4KiB envelope; batch <=100 eventos/256KiB.
  Buffer de um frame, fila limitada, três fontes no máximo, timeout5s, cancelamento
  fora da thread UI e encerramento de filhos próprios. Frame truncado/oversize/
  JSON duplicado fecha. JSON de wire precisa parser estrito; modelo recebe objetos
  Python já construídos e não implementa parser/timeout/IO do transporte.
- ACK de inbox continua `durable_local_inbox_not_business_completion`, gerado só
  após commit; controle bridge continua `bridge_admission_only_producers_not_confirmed`.
  ACK modelo é `model_transport_only_no_inbox_or_producer_ack`. Nenhum deles
  estabelece ordem global, causalidade, conclusão de negócio ou aceite humano.

## O que está implementado e testado

`observador.source_auth_simulator.SyntheticAuthModel`: **modelo em memória** com
simulation_only obrigatório. Sem socket/pipe, CLI, arquivos de chave, host nativo,
integração OfflineBridge ou coleta. arm_for_test/sign_for_test são oráculos de
ambiente confiável: assumem identidade e entrega de chave, não as provam. Não usar
para chamar authorize(source). Não distribuir segredo do modelo a outro processo.

Testes: default off, origem/identidade/sessão/PID-criação/aliases incompatíveis,
MAC/epoch/challenge/generation/sequence adulterados, pausa/retomada com nova prova,
replay/restart/segundo dono, deadline/regressão, limite64, frame inválido/extra,
100 mutações seed1402. Scope/flags não permitem chamar resultado de ACK de inbox.
Benchmark64 frames é apenas custo do modelo Python num processo, não overhead de
Windows/UIA/IPC nem SLA. Limites de parsing/alocação de objetos externos não provados.

`observador.windows_peer_probe.inspect_owned_child`: preflight **desconectado**
do controlador; consulta GetProcessId/GetProcessTimes/QueryFullProcessImageNameW
no MESMO handle Popen próprio e confere sessão esperada via kernel. Não enumera
processos nem lê nomes de controles/valores. Erros estáticos não expõem paths.
Teste Windows abre apenas fixture WPF própria, aceita identidade correta, recusa
caminho/criação/sessão errados e processo terminado; encerra filho em finally.
Isso prova consulta de identidade do filho, **não vinculação ao peer de um IPC**.
Linux pula esse teste explicitamente; não é aprovação. Native/UIA e Chromium
anteriores continuam sendo ensaios distintos. Sem nenhum host instalado.

## Bloqueio técnico e próxima implementação

Ainda faltam backend nativo com verificação bidirecional do peer do canal,
pareamento privado/handles mínimos, testes de DACL com outra sessão/conta,
colisão real/EOF/truncamento/cancelamento/duplo escritor e integração opt-in com
ACK efetivo do provider. O probe isolado e o HMAC simulado não atendem esses gates.
A ausência dessa prova integrada é o motivo técnico para NÃO ligar adaptação,
conforme P2.6; não depende de escolha técnica rotineira do responsável.

Próxima execução pode implementar primeiro pipes herdados do NativeSession em
branch filha do PR deste modelo, com testes negativos reais Windows e revisão
adversarial antes do opt-in. Preservar PR6; sem coleta/instalação real. Somente
quando o canal estiver provado, adicionar adapter worker limitado que recebe a
projeção já permitida do controlador fictício; não consumir a UI nem mudar schema
de aceite para isso. Nunca ligar navegador profissional/NativeMessaging para
contornar o gate. Windows10/11/Chrome/Edge humanos e gates LGPD continuam pendentes.
