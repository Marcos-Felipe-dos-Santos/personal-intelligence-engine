# PIE Core v1 Gap Analysis

PIE Core is the memory and evidence layer of the project. Before building an Assistant Layer, Core v1 should make capture, review, lookup, reprocessing, and reporting reliable enough to use as a trusted local foundation.

## What Core Already Provides

- Local-first capture through `pie add`
- SQLite source of truth
- Raw entry preservation before extraction
- Structured entries linked to raw entries
- Pydantic validation
- Markdown notes and daily reports
- Audit logging
- Deterministic default extraction
- Optional local LLM extraction
- Synthetic extraction quality evaluation

## Gaps Before Core v1

### Human-In-The-Loop Review

**Implemented.** Available via `pie review`.

- `pie review list` lists entries that need human review.
- `pie review show <id>` shows raw and structured data side by side.
- `pie review approve <id>` approves the structured entry.
- `pie review reject <id>` rejects the structured entry.
- `pie review history <id>` shows the audit history.
- Preserve review actions in audit logs.
- Defer `pie review edit <id>` until the revision model is implemented. (Design decision for future edit: use a dedicated revision/snapshot model before updating structured data. See [Review Edit Design](review_edit_design.md)).

### Entries List And Show

**Implemented.** Available via `pie entries list` and `pie entries show <id>`.

- `pie entries list` with `--type`, `--project`, `--status`, and `--limit` filters
- `pie entries show <structured_entry_id>` with full detail including tags, raw content snippet, and structured JSON

### Textual Search

**Implemented.** Available via `pie search "<query>"`.

- `pie search "<query>"` with `--type`, `--project`, `--status`, and `--limit` filters
- searches across raw content, summary, project, and structured JSON (including tags)
- shows match source and short snippet per result
- no external search service required

### Reprocessing

**Implemented.** Available via `pie entries reprocess`.

- `pie entries reprocess <structured_entry_id>` re-runs extraction and validation safely.
- Batch reprocessing supported via `--status needs_review` with a default limit of 20 entries.
- Batch reprocessing uses one transaction per entry. It is not all-or-nothing for the whole batch.
- Partial success can happen: successful entries remain applied, and failed entries are rolled back completely.
- Batch output reports total selected, total applied, total failed, applied IDs, failed IDs, and a short error for each failed ID.
- A `--dry-run` flag allows previewing before/after field differences.
- Revision snapshots (omitting raw content to prevent duplication) are stored in `structured_entry_revisions`.
- `raw_entries.content` remains immutable during reprocessing.
- Standard audit logs (`extraction_completed` and `validation_completed`) track execution details.

### Weekly And Project Reports

**Implemented.** Available via `pie report weekly` and `pie report project`.

- `pie report weekly --date YYYY-MM-DD` generates weekly summaries from Monday to Sunday.
- `pie report project --project <name>` filters and summarizes entries for a specific project.
- Excludes full raw content to avoid leaking sensitive information.
- Includes structured and raw source entry citations.
- Timezone conversions run on configured local timezone.

### Backup And Export

**Implemented.** Available via `pie backup create`, `pie export json`, and `pie export markdown`.

- `pie backup create` creates a secure SQLite copy in `backups/` using SQLite's backup API.
- `pie export json` exports all database tables (raw/structured entries, audit logs, generated files, reports, and revisions) to a single file in `exports/`.
- `pie export markdown` exports structured entries grouped by entry type with safe snippets to a summaries file in `exports/`.
- All backup and export files are local and ignored by Git to prevent sensitive plaintext exposure.

## Success Criteria For Core v1

Core v1 is ready when:

- users can capture, inspect, review, search, and reprocess entries locally
- every memory-like output cites source entry IDs
- review and reprocessing actions are audit logged
- reports remain grounded in stored entries
- backup/export guidance is clear
- tests cover the main user workflows
- privacy documentation warns against committing real runtime data
- no external service is required for default operation

## Out Of Scope For Core v1

- Assistant Layer implementation
- autonomous agents
- voice interface
- external write actions
- cloud sync
- RAG and embeddings
- dashboard
- email, calendar, contacts, or messaging integrations
