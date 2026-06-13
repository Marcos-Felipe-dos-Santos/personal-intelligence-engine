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
  `pie report`, `pie backup create`, `pie export`, `pie entries reprocess`

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
- 347 testes passando, ruff limpo
- PIE Core alpha funcional, pronto para uso real controlado
- Proporcao teste/producao ~1.2:1

## Gargalos conhecidos (prioridade de correcao)
1. Ollama remoto NAO bloqueado — _validate_base_url so valida http(s),
   nao impede endpoint externo. Dados pessoais podem vazar via PIE_OLLAMA_BASE_URL.
   FIX: bloquear remoto por padrao, PIE_ALLOW_REMOTE_OLLAMA=true como override.
2. PIE_HOME nao existe — paths relativos (pie.db, notes/) resolvidos do CWD,
   rodar de pastas diferentes cria bancos diferentes. FIX: raiz fixa configuravel.
3. Soft delete/purge pode nao remover .md de notes/ do disco — verificar e,
   se confirmado, mover para trash/ no delete e unlink no purge.
4. review edit nao existe — so approve/reject/history. FIX: pie review edit com
   structured_entry_revisions, before/after.
5. FakeExtractor e heuristico — confidence nao e qualidade real. Usar --project/--type/--tag.

## Dados sensiveis — NUNCA tocar
- .env, pie.db, notes/, reports/, backups/, exports/ contem dados pessoais reais
- Nunca ler, imprimir ou commitar esses caminhos
- backups/ e exports/ ja estao no .gitignore

## Git
- Conventional commits: feat/fix/test/docs/refactor/chore
- Um commit por mudanca logica
- Testes devem passar antes de qualquer commit
- Nunca git push sem aprovacao explicita
