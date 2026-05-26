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

PIE can mark low-confidence entries as `needs_review`, but there is no user workflow for reviewing them.

This is the next planned Core implementation block. See [Human Review Design](human_review_design.md).

Needed:

- list entries that need review
- show raw and structured data side by side
- accept, edit, or reject structured extraction
- preserve review actions in audit logs

Minimum first implementation:

- `pie review list`
- `pie review show <id>`
- `pie review approve <id>`
- `pie review reject <id>`
- defer `pie review edit <id>` until the revision model is implemented

Design decision for future edit: use a dedicated revision/snapshot model before updating structured data. See [Review Edit Design](review_edit_design.md).

### Entries List And Show

There is no direct way to inspect stored entries from the CLI.

Needed:

- `pie entries list`
- filters by date, type, status, and project
- `pie entries show <id>`
- clear display of structured entry ID, raw entry ID, status, source, timestamps, tags, and summary

### Textual Search

PIE does not yet expose search over captured memory.

Needed:

- local text search over raw and structured entries
- no external search service
- basic filters by date, entry type, status, project, and tag
- source IDs shown with every result

### Reprocessing

There is no safe way to re-run extraction for an existing raw entry.

Needed:

- reprocess one raw entry
- optionally reprocess entries matching a filter
- preserve old structured output or record replacement clearly
- audit extractor backend, model, prompt version, and reason for reprocessing

### Weekly And Project Reports

Daily reports exist, but Core v1 needs more practical reporting.

Needed:

- weekly report
- project-specific report
- clear source entry citations
- no invented information
- local timezone behavior documented and tested

### Backup And Export

There is no supported backup/export command.

Needed:

- export SQLite database and generated projections safely
- optional JSON export of selected entries
- warning for plaintext sensitive data
- documentation for encrypted backup locations

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
