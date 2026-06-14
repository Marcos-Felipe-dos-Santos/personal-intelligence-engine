# PIE — Personal Intelligence Engine

Engine local-first de inteligência pessoal: captura, estrutura, revisa, busca,
reprocessa, exporta e transforma informações pessoais em memória auditável.
Python + Click + SQLite + Pydantic. Sem nuvem obrigatória.

## Comandos
- Testes: `python -m pytest -q`
- Teste único: `python -m pytest tests/test_arquivo.py::test_nome -v`
- Lint: `ruff check .`
- Format: `ruff format .`
- CLI: `pie doctor`, `pie add`, `pie entries list`, `pie search`, `pie review`,
  `pie review edit`, `pie report`, `pie report decisions`, `pie report tasks`,
  `pie backup create`, `pie export`, `pie entries reprocess`

## Arquitetura (camadas)
CLI (cli/commands.py) -> PIEApp (main.py) -> Services -> Repositories -> SQLite
                                                      Adapters (extractor, markdown)

Modulos principais:
- app/cli/commands.py — entrypoint Click (945 linhas, god module a dividir)
- app/main.py — PIEApp, orquestrador (809 linhas)
- app/domain/schemas.py — contratos Pydantic
- app/services/ — ingestion, extraction, validation, report, reprocess, backup_export, audit
- app/repositories/ — database, entries, audit, reports, revisions
- app/adapters/ — fake_extractor, local_llm_extractor (Ollama), markdown_writer
- app/config.py — Config a partir de env vars
- app/evaluation/ — avaliacao sintetica de extracao

## Principios inegociaveis
- local-first, privacy-first
- raw_entries.content e IMUTAVEL — nunca editar
- SQLite e fonte de verdade; Markdown e PROJECAO (saida humana)
- human-in-the-loop — sem automacao silenciosa
- auditabilidade — toda acao relevante gera audit log
- sem acao externa silenciosa

## Estado atual
- 379 testes passando, ruff limpo
- PIE Core alpha funcional, pronto para uso real controlado
- Proporcao teste/producao ~1.2:1

## Gargalos conhecidos (abertos)
5. FakeExtractor e heuristico — confidence nao e qualidade real. Usar --project/--type/--tag.
   Aviso documentado no codigo (fake_extractor.py), comportamento esperado.

## Gargalos resolvidos (PRs 7-10)
1. Ollama remoto bloqueado por padrao — PIE_ALLOW_REMOTE_OLLAMA=true como override.
   Implementado em local_llm_extractor._validate_base_url (PR 7).
2. PIE_HOME implementado — raiz fixa configuravel, todos os paths resolvidos sob ela.
   Sem PIE_HOME, comportamento original (CWD) preservado (PR 9).
3. Purge remove .md do disco — generated_files consultado antes do DELETE,
   unlink(missing_ok=True) por arquivo, falhas reportadas sem abortar (PR 8).
4. pie review edit implementado — structured_entry_revisions com snapshot before/after,
   audit log REVIEW_EDITED, transacao atomica (PR 10).

## Dados sensiveis — NUNCA tocar
- .env, pie.db, notes/, reports/, backups/, exports/ contem dados pessoais reais
- Nunca ler, imprimir ou commitar esses caminhos
- backups/ e exports/ ja estao no .gitignore

## Git
- Conventional commits: feat/fix/test/docs/refactor/chore
- Um commit por mudanca logica
- Testes devem passar antes de qualquer commit
- Nunca git push sem aprovacao explicita
