---
name: test-runner
description: Executa o menor conjunto de testes relevante para a mudanca atual no PIE.
context: fork
agent: junior-dev
---

Execute testes com foco em: $ARGUMENTS

1. Identifique arquivos alterados com `git diff --name-only`
2. Mapeie o modulo alterado para seu teste em tests/:
   - app/services/X.py -> tests/test_X*.py
   - app/repositories/X.py -> tests/test_X*.py ou test_database_schema
   - app/adapters/X.py -> tests/test_X*.py
   - app/cli/commands.py -> tests/test_*_cli.py
3. Rode o menor conjunto: `python -m pytest tests/test_arquivo.py -v --tb=short`
4. Se a mudanca for transversal (schema, config), rode a suite completa
5. NAO altere arquivos

Saida:
- Comandos executados
- Resultado (passou/falhou) e contagem
- Falhas com causa provavel
- Se faltou cobertura para a mudanca, aponte qual teste criar
