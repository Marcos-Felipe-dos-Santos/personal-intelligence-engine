---
name: review-diff
description: Revisa o diff atual com foco em privacidade e correcao. Use antes de qualquer commit.
context: fork
agent: senior-reviewer
---

Revise o diff com foco em: $ARGUMENTS

1. Rode `git diff` e `git diff --staged`
2. Para cada arquivo alterado avalie:
   - Bug logico ou regressao?
   - Vazamento de dado pessoal (log, export, prompt de LLM, mensagem de erro)?
   - Respeita imutabilidade de raw_entries.content?
   - Mantem SQLite como fonte de verdade?
   - Toda acao nova gera audit log?
   - Migration consistente se schema mudou?
   - Teste cobre o caso novo?
3. NAO altere arquivos

Saida:
- Veredito: PODE COMMITAR / NAO PODE COMMITAR
- Riscos de privacidade (bloqueiam commit)
- Problemas criticos
- Problemas medios
- Mensagem de commit sugerida (Conventional Commits)
