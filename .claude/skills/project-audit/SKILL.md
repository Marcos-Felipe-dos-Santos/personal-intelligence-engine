---
name: project-audit
description: Audita o estado atual do PIE antes de qualquer trabalho.
context: fork
---

Audite o projeto com foco em: $ARGUMENTS

1. Rode `git status` e `git log --oneline -10`
2. Leia CLAUDE.md (secao "Gargalos conhecidos") e pyproject.toml
3. Rode `python -m pytest -q` e confirme o numero de testes passando
4. Liste os modulos relevantes ao foco do audit
5. NAO leia notes/, reports/, backups/, exports/ ou pie.db (dados pessoais)
6. NAO altere nenhum arquivo

Saida obrigatoria:
- Resumo executivo (3 linhas)
- Estado dos testes (passando/falhando)
- Gargalo(s) relevante(s) ao foco, confirmado(s) no codigo
- Arquivos que precisariam mudar
- Proxima acao mais segura
