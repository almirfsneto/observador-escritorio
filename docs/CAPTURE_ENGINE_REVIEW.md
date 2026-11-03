# Avaliacao preliminar de motores — 2026-11-03

Inspecao documental e de manifests, nao auditoria integral de codigo ou teste dos
produtos. Nenhum componente externo foi instalado, executado ou copiado. As
licencas abaixo referem-se aos arquivos consultados, nao a todas as dependencias.

| Candidato | Licenca e manutencao observadas | Compatibilidade e riscos | Decisao / dificuldade |
| --- | --- | --- | --- |
| [OpenAdapt](https://github.com/OpenAdaptAI/OpenAdapt/tree/1a64acd47bf6e60de20b7ac97993bd23122eb697) | MIT; HEAD consultado de 2026-11-03; manifest 1.19.0 | Python >=3.10; extras Windows/capture/privacy. Base inclui Flow, agent e browser; captura e FFmpeg sao opcionais. Adequacao dos redatores e ausencia de transmissao exigem auditoria dos pacotes concretos. | Nao adotar nesta entrega. Integracao alta para um observador minimo: separar captura de execucao/browser/servicos e demonstrar controles de privacidade. |
| [SmartRPA](https://github.com/bpm-diag/smartRPA/tree/d546924b70e1db5dc96d0baf5c6d0db00aa48972) | LICENSE com termos permissivos MIT; HEAD consultado de 2024-11-07 | README anuncia Windows 10/11, Python 3.10 x64, Office, extensoes, screenshots e semantic tagging Gemini. Instrucoes incluem bibliotecas nativas e problemas de instalacao. A branch action_logger e descrita como antiga. | Nao adotar. Integracao alta: retirar caminhos de dados brutos/IA, revisar logger/extensoes e atualizar dependencias. Data antiga aumenta necessidade de verificar suporte atual; nao prova abandono. |
| [Deskmate, sarkar-ai-taken](https://github.com/sarkar-ai-taken/deskmate/tree/dcaba64b4331e630a1baefbac5ab90cb4b8cf345) | MIT; manifest 0.4.1; HEAD consultado de 2026-02-14 | Node >=18; macOS/Linux, Windows via WSL2. README descreve execucao remota com Telegram, CLIs de IA, comandos e screenshots, nao coleta UIA nativa Windows. | Inadequado como motor demonstrado. Adaptacao alta e finalidade distinta; nao usar como coletor. O nome DeskMate e ambiguo: este e um candidato encontrado, nao identidade confirmada do projeto referido no prompt. |
| Win32 + UI Automation / .NET do Windows | APIs do sistema; nenhum codigo de terceiros importado | Consulta restrita a processo permitido, tipo do controle e IsPassword. Compatibilidade Windows 10/11 prevista, ainda sem execucao neste ambiente Linux. | Prototipo proprio pequeno. Ponte PowerShell por consulta tem latencia/overhead e risco de timeout; substituir por provedor persistente antes de piloto. |

Fontes consultadas: README, LICENSE e pyproject.toml de OpenAdapt; README e LICENSE
de SmartRPA; README, LICENSE e package.json do Deskmate acima. Referencias fixadas
nos commits da tabela. Datas de HEAD verificadas pela API GitHub. O pyproject.toml
e requirements.txt na raiz do SmartRPA retornaram 404; nao foi auditada a arvore
completa de dependencias. A pesquisa por DeskMate encontrou tambem projetos de
hardware e mascotes, reforcando a ambiguidade.

SHA-256 dos arquivos de licenca consultados:

- OpenAdapt LICENSE: `7f2bc0ccbf15854bbe46f5fa0e7cb26fe42f88ec9f8c9b151f0f93c4415820f9`.
- SmartRPA LICENSE: `473cd4dc81c71ba29f24303e252551e5866d7e2a43e23f7094682499c942d923`.

Antes de qualquer adocao: fixar versoes, auditar licencas transitivas e codigo de
captura, medir overhead e demonstrar com dados ficticios que valores, senhas,
clipboard e uploads estao ausentes. Nao se conclui que qualquer candidato atende
ao requisito apenas por declaracao de README.
