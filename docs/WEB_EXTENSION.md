# MV3 — protótipo web somente sintético e local

Manifest V3 para avaliação em **perfil descartável de laboratório**, inicialmente
inativo. Não instalar em navegadores da equipe. Não publicar em loja nem usar em
sites reais. O protocolo é experimental, ainda sem integração ao agente Windows.

Em máquina/VM dedicada, servir `tests/fixtures/web` apenas em loopback:
`python -m http.server 8765 --bind 127.0.0.1 --directory tests/fixtures/web`.
Abrir `http://127.0.0.1:8765/synthetic-lab/index.html`. Se a política do navegador
permitir extensões de teste, carregar a pasta browser-extension como unpacked
pelo modo desenvolvedor Chrome/Edge. **Não alterar políticas administrativas**
para contornar bloqueios; usar ambiente dedicado autorizado. A política deste
executor bloqueou extensões unpacked: a execução local real não foi aprovada.
CI independente usa Chromium descartável para verificar carregamento MV3.

Abrir o popup da extensão na aba fictícia e clicar Iniciar ensaio explícito.
Indicador na página identifica estado; popup permite pausar/retomar/encerrar.
Prazo 15 minutos, máximo duas abas/sessões por perfil, 20 eventos/s, buffer 256,
sequência até 1000. Nova sessão substitui o buffer encerrado; **exportar antes**.
Fechar aba/perfil remove a sessão; nada é salvo automaticamente em arquivo.
Exportação por botão baixa JSON sintético local, a revisar antes de compartilhar.

## Minimização e contrato

Permissão somente storage; host loopback 127.0.0.1, content match somente
/synthetic-lab/*. Host permissions do Chrome não restringem caminho/porta:
código exige **origem exata
http://127.0.0.1:8765** e caminho permitido, top frame e marcador sintético v1.
Nenhuma permissão tabs/scripting/downloads/cookies/webRequest/all_urls. Consultas
de aba ativa acessam URL apenas da origem permitida para autorização, nunca
exportam URL/query/hash. Popup protegido por CSP self, object/connect none.

Listeners de click/submit/popstate/hashchange; nunca teclado, clipboard, valores,
texto de mensagens, cookies ou cabeçalhos. Apenas eventos DOM confiáveis e
atributos de ação/papel em allowlists fechadas; IDs aleatórios efêmeros em WeakMap.
Exclui input/textarea/contenteditable e senha integralmente, sem ler valores.
Abas são tabs HTML da fixture, não vigilância de abas globais do navegador.

Worker valida sender/origem/tipos, serializa processamento e persiste somente em
chrome.storage.session (memória do navegador) para suspensão do MV3. Pausa muda
geração: mensagens antigas são rejeitadas e não reaparecem ao retomar. Timestamp
UTC/ordem são da recepção no worker, não do servidor nem garantia causal. Mudança
de relógio para trás encerra sessão; prazo rechecado em cada mensagem e pelo
indicador. Suspensão/fechamento abrupto pode perder mensagens, especialmente
navegação/unload. Há contadores de rejeição/rate/buffer, sem promessa de entrega
exatamente uma vez ou de custo zero. O background não faz fetch/XHR/WebSocket.
Não auditamos todo tráfego interno do browser/OS.

`observador.web_events.read_web_export` faz importação fechada para Event v1 sem
mudar schema legado. Somente synthetic-web, ações/papéis enumerados, sem texto
livre, URLs ou campos extras. Exportação <=256 eventos/256 KiB; sem upload.
Testes de contrato em Linux/Windows e job Chromium real separado (Playwright
1.62.0, Apache-2.0, dependência **apenas de teste**; nenhuma biblioteca embutida na
extensão). Chrome/Edge Windows em sessão humana ainda não validados. A CI não
substitui consentimento, gates LGPD, segurança e aceite humano.
