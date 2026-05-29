# PIE Current State

This document records the current state of PIE Core. PIE remains experimental alpha software: it is useful as a local-first memory engine, but it is not a finished privacy product and it is not an autonomous assistant.

## Project Summary

PIE is a local-first Personal Intelligence Engine. It captures raw text entries, extracts structured data, validates it with Pydantic, stores everything in SQLite, writes Markdown projections, generates reports, and records audit logs.

SQLite remains the source of truth. Markdown notes, reports, exports, and backups are local plaintext artifacts and must be treated as sensitive.

## Current Status

PIE Core has a practical CLI workflow for capture, inspection, search, human review, safe reprocessing, backup/export, and daily/weekly/project reports.

The future Assistant Layer is documented but not implemented. There is no RAG, embeddings, voice interface, external integration, autonomous agent, or external action system in the current codebase.

## Available Commands

- `pie add "text"` captures a raw entry, extracts structured data, validates it, writes a Markdown note, and records audit events.
- `pie doctor` checks the configured extractor backend without creating entries.
- `pie entries list` lists structured entries with optional filters.
- `pie entries show <structured_entry_id>` shows details for one structured entry.
- `pie entries reprocess <structured_entry_id> --dry-run` previews reprocessing changes.
- `pie entries reprocess <structured_entry_id>` applies safe reprocessing for one entry.
- `pie entries reprocess --status <status> --dry-run` previews batch reprocessing by status.
- `pie entries reprocess --status <status> --limit <n>` applies batch reprocessing with per-entry transactions.
- `pie search "<query>"` runs local textual search across stored entries.
- `pie review list` lists entries waiting for human review.
- `pie review show <structured_entry_id>` shows one review entry.
- `pie review approve <structured_entry_id>` approves a review entry.
- `pie review reject <structured_entry_id>` rejects a review entry.
- `pie review history <structured_entry_id>` shows audit history for the related raw entry.
- `pie report daily --date YYYY-MM-DD` generates a daily report for the configured local day.
- `pie report weekly --date YYYY-MM-DD` generates a Monday-to-Sunday weekly report for the local week containing the date.
- `pie report project --project <name>` generates a project-specific report.
- `pie backup create` creates a local SQLite backup.
- `pie export json` exports core database tables to JSON.
- `pie export markdown` exports structured entries as grouped Markdown summaries.
- `pie evaluate extraction --backend fake` runs synthetic extraction quality evaluation and prints Markdown.
- `pie evaluate extraction --backend fake --output reports/evaluation/fake.md` saves the evaluation report to Markdown.

## Main Modules

- `app/cli/commands.py`: Click commands and user-facing error handling.
- `app/main.py`: `PIEApp` facade and application wiring.
- `app/config.py`: environment-backed configuration, including local timezone and optional extractor settings.
- `app/domain/`: Pydantic schemas, enums, and validation constants.
- `app/adapters/`: deterministic `FakeExtractor`, optional `LocalLLMExtractor`, and Markdown writer.
- `app/services/`: ingestion, extraction, validation, Markdown, reports, audit, backup/export, and reprocessing workflows.
- `app/repositories/`: SQLite database access, entries, reports, audit logs, and structured entry revisions.
- `app/evaluation/`: synthetic extraction evaluation scoring, runner, report rendering, and CLI support.
- `app/prompts/extraction_prompt.md`: versioned prompt for optional local LLM extraction.

## Existing Migrations

- `001_initial_schema.sql`: creates the initial SQLite schema, including raw entries, structured entries, audit logs, generated files, and reports.
- `002_add_review_audit_actions.sql`: adds audit action support for human review actions.
- `003_create_structured_entry_revisions.sql`: adds `structured_entry_revisions` for before/after structured snapshots.

## Implemented Functionality

- Local-first capture through `pie add`.
- Raw entry preservation before extraction.
- Structured entries linked to raw entries.
- Pydantic validation for entry type, confidence, JSON fields, and revision snapshots.
- Deterministic `FakeExtractor` as the default extractor.
- Optional Ollama-compatible local LLM extractor.
- Markdown notes as projections in `notes/`.
- Daily, weekly, and project Markdown reports in `reports/`.
- Local timezone handling for daily and weekly report ranges.
- Audit logs for pipeline events, report generation, review actions, and reprocessing.
- Entries list/show and local textual search.
- Human review list/show/approve/reject/history.
- Safe reprocessing with dry-run, per-entry transactions, rollback on failure, and structured revision snapshots.
- Backup/export commands.
- Synthetic extraction quality fixtures, deterministic scoring, runner, Markdown report, and CLI.
- CI workflow for tests, Ruff, and compileall.

## Partially Prepared But Not Implemented

- `structured_entry_revisions` prepares the data model for future `pie review edit`, but the edit command itself is not implemented.
- The Assistant Layer is documented as a future layer, but no assistant runtime, intent router, tool registry, approval layer, or external integration exists in code.
- Approval policies are documented for future assistant/external actions, but there is no general approval framework yet.

## Not Implemented Yet

- `pie review edit <id>`.
- Recommended real-use workflow documentation from capture through review, reprocessing, reports, backup, and export.
- Polished UX for longer real-world usage sessions.
- External integrations such as calendar, email, messaging, ActivityWatch, Wakapi, MCP, or browser automation.
- RAG, embeddings, vector database, semantic search, or model benchmarking.
- Voice input/output, local UI, dashboard, or mobile app.
- Autonomous actions or external write actions.

## Current Limitations

- PIE is alpha software and still needs controlled real-world usage before Core v1 can be considered mature.
- Reports are grounded in local captured entries only; they do not know about uncaptured work or external systems.
- Batch reprocessing is transactional per entry, not all-or-nothing for the whole batch; users must review partial-success summaries.
- Markdown notes are projections and can become stale after reprocessing or future edits.
- Project reports require exact project-name matches.
- Optional Ollama extraction is experimental and depends on local model behavior.
- Extraction evaluation is synthetic and lexical; it does not prove real-world semantic quality.
- Local files are plaintext unless protected by the operating system.

## Technical Risks

- SQLite is simple and portable, but future concurrent workflows will need careful transaction boundaries.
- Confidence scores are extractor-specific and not calibrated across extractors.
- Optional local LLM output can vary by model, prompt, and machine.
- Reprocessing updates structured entries and records revisions, but does not regenerate Markdown automatically.
- Reports rely on entry timestamps and configured timezone; timezone assumptions must remain tested.
- Search is local textual search, not semantic retrieval.

## Privacy Risks

- Raw entries, structured entries, audit logs, generated notes, reports, backups, and exports may contain sensitive personal data.
- Optional Ollama extraction sends raw entry text to the configured local endpoint.
- Generated reports can reveal sensitive patterns even without full raw content.
- Real `pie.db`, `.env`, `notes/`, `reports/`, `backups/`, `exports/`, logs, and local scratch files must never be committed.

## Validation Commands

Run these before publishing or continuing feature work:

```bash
python -m pytest -q
python -m compileall personal_intelligence_engine
.venv\Scripts\ruff.exe check .
python -m ruff check .
```
