# Issue29 / AI03B — Job na criação, experimento isolado

Base imutável PR28: 508c38ad0996e7854c788cf08f655c8b65225707.
Branch filha codex/job-at-creation-study. Ler Issue29 integral, Issue22 e parecer
PR28. Somente tests/ e CI/desenho; zero alterações dos launchers, NativeSession,
WindowsObserver, canais ativos ou adapter. Não inicia Issue30.

## Contrato de API e memória

STARTUPINFOEXW embute STARTUPINFOW e ponteiro opaco. cb usa sizeof da estrutura
estendida. Assinaturas Win32 tipadas: BOOL/HANDLE, DWORD_PTR/SIZE_T com largura
de ponteiro, DeleteProcThreadAttributeList VOID. Primeiro Initialize(NULL,1,0)
exige false + ERROR_INSUFFICIENT_BUFFER e tamanho limitado; alocar buffer e
inicializar antes de Update. JOB_LIST=0x2000D, lista HANDLE[1] do Job anônimo próprio
KILL_ON_JOB_CLOSE, não herdável. Buffer e lpValue permanecem vivos até Delete.
Delete normal libera referências Python; API VOID não oferece confirmação BOOL
nem observação independente do heap do kernel. Exceção injetada conserva storage,
marca failed, tenta Job/processo/ambos os handles e não repete delete incerto.

CreateProcessW usa executável Python do teste -I -S -B, script inerte embutido,
SystemRoot/TEMP/TMP mínimos, diretório do interpretador, stdio NULL,
bInheritHandles=FALSE, CREATE_SUSPENDED|CREATE_NO_WINDOW|CREATE_UNICODE_ENVIRONMENT|
EXTENDED_STARTUPINFO_PRESENT. Sem HANDLE_LIST, parent spoofing, breakaway, ambiente
normal, rede ou captura. Nenhum AssignProcessToJobObject no caminho da criação.
IsProcessInJob(handle retido, Job próprio) deve provar membership antes de Resume;
ResumeThread exige contagem anterior1. Não há fallback Popen→assign.

Falhas de tamanho/init/update/create retornam job_at_creation_unavailable com dono
anexado e diagnóstico fechado. Membership/resume falhos não liberam execução.
Cleanup tenta Delete, término/zero/close do Job, sinalização do processo e closes
de thread/processo independentemente. Reutiliza política e orçamento2s do estudo
PR28; não aceita erro de close como limpeza confirmada. Snapshot separa criação
indisponível de cleanup comprovado, com fases/enums/contagens, sem PID/slots/
paths/valores privados/exceções livres. Slots trafegam somente por controle local
de testes e arquivo sintético temporário, nunca são encaminhados a logs.

## Provas preparadas e interpretação

- Positivo: filho suspenso sem marker; recusa resume antecipado; membership sem
  assign; decoy/Job não herdados por comparação de objetos; descendant membership
  e lista completa limitada de membros contendo ambos os handles próprios; cleanup com zero membros/saída e todos closes.
- Crash real do launcher após criação ANTES de verify, após verify ANTES de resume
  e após resume. Handshake para raiz duplicar só capacidade de processo é barreira
  controlada nesse ponto: não é fault espontâneo no interior do kernel.
  Launcher é morto sem finally; raiz espera sinal de saída, não mata filho para
  satisfazer assert. Raiz não duplica/abre/herda Job alvo; imagem/tempo/sessão são
  verificados sobre capacidades, sem OpenProcess(pid). Depois de resume, raiz
  duplica também o único descendant inerte conhecido e exige sinalização dos dois.
- Nested controlado: launcher colocado em Job externo antes de criar; raiz retém
  somente esse Job externo, aberto durante prova do fechamento do Job interno.
  Filho pertence também ao externo; morte pré-verify deve sair; consulta externo
  confirma zero ANTES de fechá-lo. Snapshot informa Job ambiente do launcher.
- Negativos REAIS planejados: tamanho de atributo zero, Job NULL e imagem própria
  inexistente; API deve recusar sem filho/fallback; close de processo protegido
  realmente recusado, cleanup continua false e teste desfaz proteção/libera seu
  handle conhecido no finally. Não são falhas espontâneas observadas em campo.
- Sete contratos portáveis: ordem/flags/lifetime, falhas tamanho/init/update/create,
  setup, membership/resume, Delete que lança, Job/wait/closes, diagnóstico fechado.
  São simulações de retorno/exceção, não prova de Win32. Testes Windows de guardas
  também injetam somente retornos enquanto recursos/cleanup são nativos reais.

Não consultar ActiveProcesses do Job alvo depois de perder seu último handle:
essa consulta exigiria mantê-lo aberto e invalidaria o experimento. Crash comprova
saída de todos os processos conhecidos da fixture; positivo e nested externo
comprovam contagem zero por consulta real. Emergency cleanup no finally da raiz
é somente contenção de teste falho; não satisfaz a prova de sucesso.

## Falhas de teste preservadas e contagem de membros

CI41958864997/2839ab8 falhou em ambos Windows por esperar exatamente2 e observar3.
CI41959187379/4130c29 descartou a explicação de console isoladamente: observou3
mesmo com NO_WINDOW e4 no positivo. NÃO identificada a origem dos membros extras.
Não chamar de conhost/redirector sem prova. O flag NO_WINDOW limita a fixture,
mas não fundamenta suposição sobre quantidade total de membros do Job.

A verificação exige QueryInformationJobObject(ProcessIdList) do próprio Job com
lista completa (cap16, sem truncamento), ambos os IDs correspondentes aos handles
retidos presentes, contagem agregada>=2 e ZERO obrigatório após teardown. Nenhum
PID adicional é aberto ou inspecionado. Crash pós-resume aninhado também exige
zero de todo Job externo, mantido aberto até a prova; isso cobre os membros extras
sem presumir identidade. Crash sem Job externo só comprova diretamente saída de
todos os processos conhecidos retidos, não consulta Job alvo depois do último close.

Um teste Windows adicional injeta recusa de terminate/query/close, conserva false e
tenta todos os recursos. Erro de CloseHandle injetado é distinto do handle realmente
protegido. Exceções de wrapper e rejeição semântica não recebem GetLastError velho.

## Limites e retomada

Até CI verde por SHA, dez casos Windows preparados; rodadas iniciais falharam
na premissa de cardinalidade. Não transferir os passes parciais para aprovação. Skips Linux/plataforma não
são passe; job Chromium mantém duas provas dedicadas. Windows-latest é runner
Server, não aceite Windows10/11 interativo. Suporte documentado Windows10+/Server
2016+ não garante qualquer hierarquia/direitos: restrição deve falhar fechado,
sem breakaway para contornar políticas. Uma lista de um Job e um descendant por
fixture não cobre todos criadores/processos, WMI/brokers, hierarquias incompatíveis,
mesmo token/admin, injeção, checkout/loader hostil ou IPC herdado do PR18.

Revisão independente deste SHA é o próximo gate. Nenhuma migração runtime, aceite
humano ou liberação de piloto. Issue30/cleanup liveness não iniciada. Não alterar
branches anteriores ou PR6. Executar novamente apenas após alteração justificável:

    PYTHONPATH=src python -m unittest discover -s tests -p 'test_job_at_creation*.py' -v
    PYTHONPATH=src python -m unittest discover -s tests -v

No Windows PowerShell: definir $env:PYTHONPATH='src' antes dos comandos python.

## Referências Microsoft consultadas

- [Update / JOB_LIST / lifetime lpValue](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-updateprocthreadattribute)
- [Initialize e sizing](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-initializeprocthreadattributelist)
- [Delete VOID](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-deleteprocthreadattributelist)
- [STARTUPINFOEXW / cb](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-startupinfoexw)
- [Job lifetime / kill on last close](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)
- [Nested Jobs e limitações](https://learn.microsoft.com/en-us/windows/win32/procthread/nested-jobs)
