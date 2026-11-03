# Como iniciar no Codex com participacao minima

1. Crie um repositorio GitHub privado `observador-escritorio`. Nao adicione dados pessoais ou credenciais.
2. Extraia este ZIP e publique **a pasta do projeto por dentro**, mantendo `AGENTS.md` na raiz.
3. Conecte esse repositorio ao Codex, em uma configuracao que permita modificar codigo e rodar testes no repositorio.
4. Copie `PROMPT_INICIAL_CODEX_OBSERVADOR.txt` na primeira tarefa do Codex.
5. Oriente o agente a criar PRs e prosseguir pelas etapas permitidas sem solicitar escolhas de implementacao rotineiras. Tarefas na nuvem podem necessitar novas execucoes ou agendamentos configurados no produto; o prompt sozinho nao garante trabalho perpetuo ou independente de execucao ativa.
6. Nao forneca acesso real as maquinas ate o Codex produzir artefato de laboratorio e relatorio de seguranca.

Para validar localmente sem instalar observadores: `python -m unittest discover -s tests -v` e `python -m observador demo --db demo.sqlite3`.

**Cuidado:** a instalacao nos computadores exige comunicacao aos colaboradores, politica de coleta e autorizacao do responsavel. O Codex nao deve implantar sozinho em maquinas de empregados.
