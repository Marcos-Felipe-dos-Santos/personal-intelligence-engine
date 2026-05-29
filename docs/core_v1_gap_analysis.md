# PIE Core v1 Gap Analysis

PIE Core is the memory and evidence layer of the project. Before building an Assistant Layer, Core v1 should make capture, review, lookup, reprocessing, reporting, backup, and export reliable enough for controlled real use.

## Implemented

### Capture, Extraction, And Validation

- `pie add "text"` captures raw entries locally.
- Raw entry content is preserved before extraction.
- `FakeExtractor` is the default deterministic extractor.
- `LocalLLMExtractor` is optional and Ollama-compatible.
- Pydantic validates structured extraction output.
- Low-confidence entries are marked as `needs_review`.
- Markdown notes are generated as local projections.
- Audit logs record capture, extraction, validation, low-confidence warnings, and Markdown generation.

### Human Review

- `pie review list` lists entries waiting for review.
- `pie review show <id>` shows review details.
- `pie review approve <id>` marks a reviewed entry as processed/valid.
- `pie review reject <id>` marks a reviewed entry as processed/invalid.
- `pie review history <id>` shows audit history for the related raw entry.
- Review actions remain local-only and do not trigger external actions.

### Entries And Search

- `pie entries list` supports `--type`, `--project`, `--status`, and `--limit`.
- `pie entries show <structured_entry_id>` shows structured details with safe raw snippets.
- `pie search "<query>"` searches raw content, summary, project, and structured JSON with filters.
- Search is local textual search and does not call an LLM.

### Backup And Export

- `pie backup create` creates local SQLite backups in `backups/`.
- `pie export json` exports core database tables to JSON in `exports/`.
- `pie export markdown` exports structured entries grouped by entry type.
- `backups/` and `exports/` are ignored by Git and treated as sensitive plaintext artifacts.

### Safe Reprocessing

- `pie entries reprocess <structured_entry_id> --dry-run` previews changes.
- `pie entries reprocess <structured_entry_id>` applies changes for one entry.
- `pie entries reprocess --status <status> --dry-run` previews batch reprocessing.
- `pie entries reprocess --status <status> --limit <n>` applies batch reprocessing with a safe default limit.
- Apply mode uses one transaction per entry. The batch is not all-or-nothing.
- Partial success can happen: successful entries remain applied, failed entries roll back completely.
- Batch output reports total selected, total applied, total failed, applied IDs, failed IDs, and a short error for each failed ID.
- Revision snapshots are stored in `structured_entry_revisions` without duplicating raw content.
- `raw_entries.content` remains immutable during reprocessing.
- Reprocessing audit logs use existing `extraction_completed` and `validation_completed` actions with reprocess-specific methods.

### Reports

- `pie report daily --date YYYY-MM-DD` generates daily reports for the configured local day.
- `pie report weekly --date YYYY-MM-DD` generates Monday-to-Sunday weekly reports using local timezone boundaries.
- `pie report project --project <name>` generates project-specific reports using exact project-name matching.
- Reports are saved in `reports/`, record rows in the `reports` table, and cite source structured/raw entry IDs.
- Weekly and project reports include counts by entry type, validation/needs-review counts, source IDs, and limitations warnings.
- Reports do not call an LLM and do not include full raw content.

### Evaluation CLI

- Synthetic extraction fixtures exist.
- Deterministic scoring exists.
- Local evaluation runner exists.
- Markdown evaluation report rendering exists.
- `pie evaluate extraction --backend fake` runs evaluation without touching the main memory database.

## Prepared But Not Implemented

### Review Edit

`structured_entry_revisions` prepares a safe before/after snapshot model for future human edits, but `pie review edit <id>` is not implemented.

The current design decision is to keep `raw_entries.content` immutable and edit only structured fields in a future command.

### Assistant Layer

The vision and architecture documents describe a future Assistant Layer, Intent Router, Tool Registry, and Approval Layer. None of that exists in code yet.

### Approval Framework

Human approval rules are documented for future writes and external actions, but there is no general approval framework outside current explicit CLI commands.

## Still Missing For Core v1

- `pie review edit <id>` using the existing revision/snapshot model.
- A recommended real-use workflow: capture, review, search, reprocess, report, backup, and export.
- UX polish for longer sessions and clearer operator guidance.
- Stronger end-to-end documentation for how to recover from stale Markdown after reprocessing or future edits.
- Continued hardening of report source citation across every memory-like output.
- Controlled real-world usage to validate performance, privacy ergonomics, and edge cases.

## Current Risks

- PIE remains alpha software and should be used carefully with real personal data.
- Markdown notes and reports are projections and can become stale after reprocessing.
- Backups, exports, notes, reports, and SQLite databases are plaintext local files.
- Optional Ollama extraction sends raw entry text to the configured local endpoint.
- Search is textual, not semantic.
- The future Assistant Layer must not bypass Core, source citations, or human approval.

## Core v1 Success Criteria

Core v1 is ready when:

- users can capture, inspect, review, search, reprocess, report, back up, and export entries locally;
- every memory-like output cites source entry IDs;
- review edit is implemented safely or explicitly deferred with a usable workflow;
- reports remain grounded in stored entries and explain their limits;
- backup/export and privacy guidance are clear;
- tests cover the main user workflows;
- controlled real use confirms the workflow is practical;
- no external service is required for default operation.

## Out Of Scope For Core v1

- Assistant Layer implementation.
- Autonomous agents.
- Voice interface.
- External write actions.
- Cloud sync.
- RAG, embeddings, vector database, or semantic search.
- Dashboard or mobile app.
- Email, calendar, contacts, or messaging integrations.
