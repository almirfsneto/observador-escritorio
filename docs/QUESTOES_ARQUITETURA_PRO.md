# Questões para revisão arquitetural aprofundada

Não existe ferramenta de consulta a um modelo Pro nesta sessão. A ausência não
bloqueia protótipos reversíveis; abaixo estão decisões/evidências para revisão.

## Cota física e confidencialidade da fila

Alternativas: (1) SQLite padrão + diretório privado + admissão/reserva, (2) VFS
próprio com quota e cifragem, (3) SQLCipher, (4) arquivos append-only DPAPI com
índice reconstruível, (5) volume dedicado com quota/cifragem do OS.

Recomendação atual: (1) para laboratório exclusivamente sintético e protótipo
DPAPI de arquivo exportado; não afirmar SQLite cifrado. VFS é complexo para
rollback/locks e requer auditoria nativa; SQLCipher adiciona manutenção/binários
Windows e revisão de licença/dependências; DPAPI por registro expõe índices e
requer migração/chaves/performance/retenção; volume depende de administração.

Evidências reproduzíveis: testes de quota/lock/corrupção/queda e recuperação,
contagem de perdas, ACL e DPAPI reais em CI Windows quando aprovados. Faltam
ameaças com outra conta, energia/SSD real, picos físicos e recuperação de chaves.
Perguntas: orçamento físico estrito é requisito de piloto? Quem administra as
chaves e backups? Que metadados podem permanecer em claro? Não há autorização
para resolver isso usando dados reais ou serviços externos.
