# Canal herdado privativo — Issue 17, Etapa A isolada

Implementação inicial em owned_channel.py/protocol.py/win32.py/child.py. **Não há
adapter de captura nem ligação ao NativeSession, WindowsObserver ou OfflineBridge.**
Chamar start() é opt-in explícito e inicia somente fixture IPC Python (-I -S -B),
sem UIA/DOM/conteúdo/rede. O código ainda precisa de evidência Windows no PR atual.

## Argumento de autenticação e limites

O parent lança um único comando fixo: seu interpretador e o entrypoint IPC próprio.
Pipes anônimos CreatePipe, sem endpoint descobrível, usam lista de herança explícita
com exatamente quatro handles: leitura de comandos, escrita de respostas, leitura
de bootstrap e handle do parent limitado a QUERY_LIMITED_INFORMATION|SYNCHRONIZE.
Std handles são NULL: não há os três handles extras de redirecionamento stdio.
O parent fecha suas cópias dos extremos do filho imediatamente após vincular o
processo. Cada handle restante é não herdável. Job kill-on-close não é herdado.

Antes de entregar chave, o launcher retém Popen._handle, consulta PID/criação/
caminho exato do interpretador/sessão no kernel e aplica Job Object próprio. O
filho consulta a identidade de si e do parent pelo handle herdado, e confere pin
SHA256 dos quatro arquivos do canal. Isso é pin de código confiável, não atestação
contra adulteração local. Imagens homônimas por outro caminho são recusadas.
A chave aleatória de32 bytes só é escrita no pipe de bootstrap, que é fechado;
o filho exige32 bytes+EOF e fecha esse handle antes de criar qualquer descendente.
Nunca chave em CLI/env/arquivo/stdio/relatório. Flags de handles são limpas no filho.

O HMAC com chave entregue SOMENTE ao processo possuído, identidades kernel,
nonces/direções/epoch/sessão e lista restrita associa a prova ao fluxo herdado.
Não se usa ready.pid declarado nem sign_for_test do simulador PR16 como prova.
Pipes anônimos não fornecem API de PID de peer como um servidor named pipe: a
associação aqui depende da posse dos handles/bootstrap e do Popen retido, não de
uma alegada consulta GetNamedPipeClientProcessId em pipe anônimo.

Limites: código no parent/filho, processo com mesmo token capaz de DuplicateHandle/
ReadProcessMemory/injeção, administrador e adulteração de checkout/interpreter
não são isolados. ACL do token padrão dos objetos privados não é prova adversarial
entre contas/sessões. -I/-S/-B evita PYTHONPATH/sitecustomize/bytecode em disco no
filho, mas Python/OS/pagefile/crash dumps não têm zeroização/cifragem garantida.
O lock cobre lançamentos deste módulo; outro código no MESMO parent que crie
processos com herança irrestrita durante o lançamento precisa cooperar. Não alegar
proteção contra código arbitrário no mesmo processo/token. Nenhuma enumeração de
processos/handles globais, socket, serviço, host, instalação ou captura é usada.

## Wire e ciclo de vida

Prefixo big-endian de4 bytes, body entre1 e16384 bytes; validar tamanho ANTES de
alocar/parse. JSON ASCII canônico, chaves fechadas, sem duplicatas/float/NaN/campos
extras. HMAC-SHA256 constant-time, domínio próprio e direção parent/child separada.
Identidade, código, epoch/session UUID, generation, nonce, sequência e payload
são todos cobertos pelo MAC. Contexto contém clocks locais separados/TTL<=900s;
não presume relógio global. Challenges5s, IO de operação<=5s, uma operação pendente,
64 mensagens totais sem reset por resume. Não aceitar MAC truncado/reflexão.

Começa disabled. start(): handshake/proof e ativa APENAS a fixture IPC. sample()
retorna contador sintético monotônico; pause() ACK da fixture para transporte.
resume() exige nova geração/nonce/prova, sem estender TTL, então ACK de retomada.
ACK tem scope owned_ipc_fixture_transport_not_inbox_or_uia_ack. Nunca ACK de fila,
commit, operação de negócio ou pausa UIA. Stop/EOF/erro/timeout fecham o canal.

Worker único executa IO e verificação; API de laboratório bloqueante NÃO deve ser
chamada em Tk. Não existe integração com Tk. CancelSynchronousIo + kill do filho
possído + Job Object liberam IO bloqueado; fechamento aguarda worker/filho com
prazo e registra shutdown_confirmed, sem declarar sucesso de teardown incompleto.
Watchdog do filho verifica vida do parent/deadline. Expiração não é renovada.
Sem retry de ações, reconexão/reauth automáticos, nem anexação a PID externo.

## Evidências inicialmente a conferir

Testes portáveis verificam wire/negativos, não autenticação de processo. Testes
Windows lançam processos e usam handles reais; devem passar em CI para qualquer
alegação de canal autenticado. Marcar skips Linux explicitamente. Casos iniciais:
handshake/contador/pausa/nonce novo/cleanup, chave/identidade falsos, MAC truncado,
JSON duplicado/NaN, oversize/truncamento/flood/EOF, timeout e expiração natural curta.
O próprio filho cria descendente com close_fds=False APÓS limpar flags e exige
que os três handles restantes sejam inválidos ali; bootstrap já está fechado.
Decoy herdável fora da lista também precisa ser negado. Não é enumeração completa
nem prova contra outro processo do mesmo token/admin. Outra conta e Windows10/11
humanos ainda são lacunas, não skips promovidos a aprovação.

Etapa B (adapter WPF) permanece OFF até prova/revisão integrada. Mesmo Etapa A
aprovada não demonstra auth do provider C# antigo nem cobertura UIA nova.

## Primeira prova executada e auditoria ampliada

22f99e5 / CI41809413254: cinco jobs aprovados; Windows3.11/3.12 executaram os três
novos testes reais, incluindo handshake/proof, limpeza de flags/descendente,
pausa/reproof, dez modos adversariais do filho, timeout e expiração real de3s.
Núcleo155 descobertos, Windows153 executados/2 browsers separados skipped,
Linux139/16 skips; Chromium2 reais no job dedicado. Isso comprova o canal da
fixture IPC sob as premissas descritas, NÃO o provider UIA C# ou um piloto.

Ampliação no próximo commit testa: decoy herdável fora da lista e unrelated
child com herança irrestrita; foreign Popen recusado sem matá-lo; frames reais
repetidos e de outra geração/nonce/sessão/direção; duas instâncias com pause,
restart e chaves distintas; kill real do parent, recursos/mensagem64, cancelamento
de operação pendente e nenhuma chave em argv/env. Erros têm fase estática e exit
code da própria fixture, sem conteúdo livre/chave/frame. Não chamar PID reuse
forçado de algo provado: alteração de creation ticks é fault injection.

Harness end-to-end de testes, sem adapter runtime: contador da fixture autenticada
é convertido pelo TESTE em Event fictício e gravado com API de OfflineBridge.
Confere ACK/retry/pausa e marker após24h por CLOCK INJETADO. Não são24h observadas,
nem captura WPF integrada, nem autorização de fonte automaticamente concedida.

Capacidade: testes normais de admissão atingem1024 batch IDs (1024 reaberturas),
10000 event IDs em100 lotes e32 fontes em32 aberturas, sem monkeypatch de caps.
Expiração/purge/restart não liberam markers. SQLite integrity_check e nova admissão
fechada verificam limite persistente. Prazos avançam por relógio injetado; orçamento
continua lógico, não quota física. Nenhum reset/rotação automática foi implementado.

Política futura de rotação deve ser revisada: metadados mínimos permanentes ou
índice de revogação externo DURÁVEL e autenticado, epoch/cadeia de arquivos
fechados, fonte explicitamente aposentada incapaz de voltar com ID/seq velhos,
ACK detalhado limitado e tratamento receipt_expired_or_unknown. Arquivar/apagar
markers sem uma fronteira persistente de revogação reabre replay e é proibido.
Enquanto não houver esse projeto/revisão, saturação encerra novas admissões.

Teste adicional inicia a fixture WPF real com close_fds=True, sem passar chave ou
handles. Verifica que os valores dos endpoints do parent não designam os mesmos
objetos no WPF por DuplicateHandle/CompareObjectHandles (número de handle pode ser
reutilizado para outro objeto). Não modifica o executável WPF ou lê seus controles.
A chave é gerada APÓS Popen; argv e lista de herança são conferidos em teste sem
imprimir segredo. Ausência de env override + geração pós-spawn exclui passar essa
chave no environment inicial do peer. Não há alegação de isolamento de memória.
