# PIE Current State

This document records the current project state before planning the next feature phase. PIE remains experimental alpha software and should be treated as a local-first personal data system, not as a finished assistant product.

## Existing Capabilities

- Python package: `personal_intelligence_engine`
- Click CLI entry point: `pie`
- SQLite as the local source of truth
- SQL migrations in `migrations/`
- Pydantic schemas for validation
- UUID strings as public identifiers
- Deterministic `FakeExtractor` as the default extractor
- Optional `LocalLLMExtractor` for Ollama-compatible local extraction
- Markdown notes written to `notes/`
- Daily Markdown reports written to `reports/`
- Audit logs for pipeline events
- Entries list/show commands for local inspection
- Local textual search across stored entries
- Safe reprocessing workflow and revisions history
- Human review commands for list/show/approve/reject/history
- Local backup and export commands
- Synthetic extraction evaluation fixtures
- Deterministic extraction quality scoring
- Local extraction evaluation runner
- Markdown evaluation report renderer
- CI workflow for tests, Ruff, and compileall

## Existing Commands

- `pie add "text"` captures a raw entry, extracts structured data, validates it, writes Markdown, and records audit events.
- `pie entries list` lists structured entries with optional filters.
- `pie entries show <structured_entry_id>` shows details for one structured entry.
- `pie entries reprocess <structured_entry_id>` re-runs extraction and updates structured entries safely.
- `pie search "<query>"` runs local textual search across stored entries.
- `pie review list` lists entries waiting for human review.
- `pie review show <structured_entry_id>` shows a review entry.
- `pie review approve <structured_entry_id>` approves a review entry.
- `pie review reject <structured_entry_id>` rejects a review entry.
- `pie review history <structured_entry_id>` shows audit history for the related raw entry.
- `pie report daily --date YYYY-MM-DD` generates a daily report for the configured local day.
- `pie backup create` creates a local SQLite backup.
- `pie export json` exports core database tables to JSON.
- `pie export markdown` exports structured entries as grouped Markdown summaries.
- `pie doctor` checks the configured extractor backend without creating entries.
- `pie evaluate extraction --backend fake` runs synthetic extraction quality evaluation and prints Markdown.
- `pie evaluate extraction --backend fake --output reports/evaluation/fake.md` saves the evaluation report to Markdown.

## Main Modules

- `app/cli/commands.py`: Click commands and user-facing error handling.
- `app/main.py`: `PIEApp` facade and application wiring.
- `app/config.py`: environment-backed configuration.
- `app/domain/`: Pydantic schemas, enums, and validation constants.
- `app/services/`: ingestion, extraction, validation, Markdown, report, and audit workflows.
- `app/repositories/`: SQLite database access and repositories.
- `app/adapters/`: `FakeExtractor`, optional local LLM extractor, and Markdown writer.
- `app/evaluation/`: synthetic extraction evaluation scoring, runner, and report rendering.
- `app/prompts/extraction_prompt.md`: versioned extraction prompt for optional local LLM usage.

## Current Tests

The test suite covers the current pipeline and evaluation utilities, including:

- database schema constraints
- Pydantic schema validation
- ingestion
- fake extraction
- local LLM adapter behavior with fake HTTP clients
- extractor selection
- CLI errors and health checks
- Markdown generation
- audit logging
- daily reports
- timezone behavior for daily reports
- entries list/show
- local textual search
- human review list/show/approve/reject/history
- local backup and export commands
- prompt contract checks
- extraction quality fixtures
- extraction quality scoring
- extraction quality runner
- extraction evaluation Markdown reports
- extraction evaluation CLI

Local validation is expected to run with:

- `python -m pytest -q`
- `python -m compileall personal_intelligence_engine`
- `.venv\Scripts\ruff.exe check .`

## Current Limitations

- Reports are limited; weekly, monthly, and project-specific reports are not implemented.
- Human review edit is not implemented yet.
- Backup/export files are plaintext local artifacts and must be protected by the user.
- Optional Ollama extraction is experimental and depends on the user's local setup.
- Extraction evaluation is synthetic and lexical; it does not prove real-world semantic quality.
- There is no Assistant Layer implementation.

## Technical Risks

- SQLite is simple and portable, but future concurrent workflows will need careful transaction handling.
- Optional local LLM output can vary by model, prompt, and machine.
- Confidence scores are extractor-specific and not calibrated across models.
- Markdown files are projections and can drift if generated files are edited manually.
- Evaluation fixtures are small and synthetic, so they should guide development but not be treated as a benchmark.

## Privacy Risks

- Raw entries, structured entries, audit logs, generated notes, and reports may contain sensitive personal data.
- Local SQLite databases and Markdown files are plaintext unless the operating system protects them.
- Optional local LLM extraction sends raw entry text to the configured local endpoint.
- Generated reports can summarize sensitive patterns even when they do not include full raw text.
- Local backups and exports may contain sensitive data.
- Real `pie.db`, `.env`, `notes/`, `reports/`, `backups/`, `exports/`, logs, and local scratch files must never be committed.
