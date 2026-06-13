---
name: safe-commit
description: Revisa, valida testes e prepara commit seguro no PIE. Invoke manualmente.
disable-model-invocation: true
context: fork
agent: senior-reviewer
argument-hint: [tipo-ou-escopo-opcional]
---

Prepare commit com escopo: $ARGUMENTS

1. Rode `git status` e `git diff --staged`
2. CRITICO: confirme que NENHUM destes vai entrar no commit:
   .env, pie.db, notes/, reports/, backups/, exports/, __pycache__, *.db, *.log
3. Confirme testes: `python -m pytest -q`
4. Confirme lint: `ruff check .`
5. Sugira mensagem (feat/fix/test/docs/refactor/chore)
6. Execute `git commit` SOMENTE se aprovado explicitamente
7. NUNCA execute git push

Saida:
- Arquivos que entrarao
- ALERTA se algum dado pessoal estiver staged
- Resultado dos testes e lint
- Mensagem de commit sugerida
- Comando exato a executar
