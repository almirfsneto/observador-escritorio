# Fila local do laboratorio — opt-in e somente eventos ficticios

O controlador mantem memoria por padrao. Marcar **Salvar eventos ficticios locais**
antes de iniciar habilita `lab-data/events.sqlite3` no checkout. O diretorio e
ignorado pelo Git; nao ha upload, sincronizacao ou exportacao automatica.

Parametros conservadores desta entrega:

- Banco principal limitado a 4 MiB por `max_page_count`, com teto de 10.000 eventos.
- Retencao de 1 hora: expurgo ao abrir, escrever e enquanto a thread esta ativa.
  Com o aplicativo fechado nao existe servico de expurgo; ao reabrir, registros
  vencidos sao removidos antes de continuar. Nao alegar exclusao no horario exato
  enquanto o programa esta desligado.
- `secure_delete` habilitado; paginas livres sao reutilizadas. Isso nao garante
  apagamento forense em SSD, backups ou snapshots, nem reduz automaticamente o
  arquivo. Banco nao e cifrado; ACL Windows ainda requer revisao antes de piloto.
- Cota refere-se ao arquivo principal, nao ao disco inteiro: journal de rollback,
  metadados do filesystem e espaco livre requerem margem adicional. Nao ha WAL.
- Uma thread e dona de SQLite; UI so entrega lotes de ate 100 eventos, em fila de
  16 lotes. Buffer cheio descarta entrada e conta perdas. Banco cheio/ocupado nao
  bloqueia a UI; erro de armazenamento pausa o ensaio. Lotes nao commitados podem
  se perder em queda; transacoes preservam integridade do banco.
- Fechar sinaliza encerramento, drena lotes ja aceitos por ate 3s e fecha conexao.
  Timeout e mostrado no estado. Pausa impede novas observacoes; lotes aceitos antes
  da pausa podem terminar a gravacao, mantendo seu timestamp original.

A projecao persistida aceita apenas alias/dispositivo fixos de laboratorio,
UUIDs, UTC, acoes foco/Invoke/Toggle, papeis enumerados e ID hexadecimal efemero.
Rejeita nomes livres, outros aplicativos, screenshot, metadata arbitraria e eventos
fora da retencao. Nao e um sanitizador generico de fontes externas.

Para inspecao offline de ensaios ficticios ja gravados:

```powershell
python -m observador analyze --db lab-data/events.sqlite3 --out analise-laboratorio.json
```

O relatorio e um candidato temporal, nao prova causalidade nem produtividade.
IDs efemeros mudam a cada sessao; correlacao entre sessoes ainda nao implementada.
UTC do evento e o instante de observacao no callback UIA, sujeito a atraso; nao e
um timestamp de origem garantido pelo aplicativo.

Testes exercitam idempotencia, recuperacao apos reinicio/expurgo, banco cheio,
rollback/integridade, lock externo, TTL, limites de linhas e buffer, rejeicao de
payloads e encerramento da thread. O ensaio CI Windows acrescenta caminho
fixture → UIA real → projecao → SQLite → detector de padroes, quando ha desktop.
Continuam pendentes ensaio humano, ACL/cifragem e politicas de incidente antes de
qualquer uso com colaboradores.
