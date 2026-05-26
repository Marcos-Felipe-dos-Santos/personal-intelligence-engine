# Phase 2D: Review Edit Design

This document defines a safe design for a future `pie review edit <structured_entry_id>` command. It is documentation only. No schema, migration, command, service, repository, or Markdown behavior is implemented here.

PIE is experimental alpha software. Editing structured memory must preserve traceability before it becomes a user-facing feature.

## Goals

- Allow a human to correct structured extraction fields.
- Preserve raw entry content permanently.
- Preserve previous structured values before any edit.
- Record what changed, who changed it, when it changed, and why if a reason is provided.
- Make `pie review history <id>` able to show `review_edited` events.
- Avoid silent memory rewrites.

## Non-Goals

- No editing `raw_entries.content`.
- No batch editing.
- No interactive UI in the first implementation.
- No automatic regeneration of all notes.
- No LLM rewrite without explicit user approval.
- No external actions.
- No Assistant Layer.
- No RAG or embeddings.

## Immutable Raw Entry Rule

`raw_entries.content` must never be edited by `review edit`.

The raw entry is the evidence source. Human edits may correct structured interpretation, but they must not rewrite the original observation.

## Editable Structured Fields

Future review edit may allow changes to structured fields such as:

- `entry_type`
- `project`
- `summary`
- `tags`
- `confidence`
- `structured_json`

All edited values must pass the same Pydantic/domain validation rules as extractor output.

## Alternatives Compared

### Alternative A: Edit `structured_entries` Directly

Description: update the existing `structured_entries` row in place and record a `review_edited` audit event.

| Concern | Evaluation |
|---------|------------|
| Simplicity | Highest. Small update query and audit log. |
| Auditability | Weak unless before/after values are stored somewhere else. |
| Risk of history loss | High. The prior structured interpretation can be overwritten. |
| Markdown impact | Existing Markdown may become stale without clear link to old values. |
| Report impact | Future reports may silently use edited values without showing what changed. |
| Search impact | Search would see only the latest values, which is simple but hides history. |
| Migration needed | Possibly none if only current columns are edited. |
| Implementation complexity | Low, but safety is poor. |

Assessment: not recommended for PIE Core because it violates the "no memory without traceable source" principle unless paired with a separate revision log.

### Alternative B: Create `structured_entry_revisions`

Description: keep `structured_entries` as the current view, but create a revision table that stores before/after snapshots for each human edit.

Possible revision fields:

- `id`
- `structured_entry_id`
- `raw_entry_id`
- `actor`
- `reason`
- `fields_changed_json`
- `before_json`
- `after_json`
- `created_at`

| Concern | Evaluation |
|---------|------------|
| Simplicity | Moderate. Requires a migration and revision repository. |
| Auditability | Strong. Before/after values and changed fields are preserved. |
| Risk of history loss | Low if every edit writes a revision before updating current values. |
| Markdown impact | Can mark existing Markdown stale or cite revision IDs later. |
| Report impact | Reports can use current values while history remains inspectable. |
| Search impact | Search can default to current values and optionally include revisions later. |
| Migration needed | Yes. |
| Implementation complexity | Moderate and well-contained. |

Assessment: recommended. It keeps current queries simple while preserving edit history and future audit/report/search options.

### Alternative C: Create A New Derived `structured_entry` With `parent_id`

Description: each edit creates a new structured entry derived from the previous one. The previous row remains immutable, and the new row becomes the current interpretation.

Possible fields:

- `parent_structured_entry_id`
- `is_current`
- or a separate pointer to the current structured entry

| Concern | Evaluation |
|---------|------------|
| Simplicity | Lower. Current-entry resolution becomes more complex. |
| Auditability | Strong. Old structured rows remain intact. |
| Risk of history loss | Low if parent links are enforced. |
| Markdown impact | Existing notes may point to old structured IDs unless regenerated or redirected. |
| Report impact | Reports must know which derived entry is current. |
| Search impact | Search must avoid duplicate historical entries unless explicitly requested. |
| Migration needed | Yes, likely more invasive than Alternative B. |
| Implementation complexity | Higher because many reads need current-version semantics. |

Assessment: viable later, but too disruptive for the first human edit implementation.

## Recommended Design

Use **Alternative B: `structured_entry_revisions`**.

Recommended behavior:

1. Load the current structured entry and raw entry.
2. Validate proposed edits.
3. Compute changed fields.
4. Write one revision row with before/after snapshots.
5. Update the current `structured_entries` row.
6. Add audit log action `review_edited`.
7. Mark the entry as reviewed/current according to the review status model chosen for implementation.

This keeps `structured_entries` useful as the current projection while preserving a complete edit trail.

## Required Revision Data

Each edit must preserve:

- previous values
- new values
- fields changed
- actor
- timestamp
- optional reason
- `raw_entry_id`
- `structured_entry_id`

The audit log should record `review_edited`, but the detailed before/after payload should live in the revision table, not in `audit_logs.error_message`.

## Audit Model

Future `review edit` must create:

- `audit_logs.action`: `review_edited`
- `audit_logs.status`: `success`
- `audit_logs.method`: `human_review`
- `audit_logs.actor`: `user`
- `audit_logs.raw_entry_id`: associated raw entry ID
- `audit_logs.error_message`: `null`

The audit event should be concise. Detailed before/after data belongs in `structured_entry_revisions`.

## Markdown Policy

Recommended first implementation:

- Do not automatically regenerate Markdown notes.
- Mark generated Markdown as potentially stale in the command output.
- Add enough revision metadata for a later regeneration command to know what changed.

Rationale: automatic regeneration can overwrite user-edited Markdown projections or create surprising file changes. A later explicit command can handle note regeneration safely.

Future option:

- `pie review edit <id> ... --regenerate-note`
- or `pie notes regenerate <structured_entry_id>`

## Review History Policy

`pie review history <id>` should show `review_edited` events once edit is implemented.

Future `review show <id>` should indicate:

- whether the structured entry has human edits
- latest edit timestamp
- latest editor/actor
- whether generated Markdown may be stale

## Future CLI Shape

Possible first command forms:

```bash
pie review edit <id> --field summary --value "Corrected synthetic summary"
pie review edit <id> --field project --value "PIE"
pie review edit <id> --json edits.json
```

Possible later interactive mode:

```bash
pie review edit <id> --interactive
```

The first implementation should prefer explicit non-interactive edits because they are easier to test, audit, and document.

## Privacy Requirements

- Do not store raw content in edit audit messages.
- Do not send edit data to external services.
- Treat before/after snapshots as sensitive personal data.
- Keep revision tables in the local SQLite database.
- Keep `pie.db`, notes, reports, logs, and `.env` out of Git.

## First Implementation Boundaries

The first implementation should not include:

- raw content editing
- batch editing
- interactive UI
- automatic Markdown regeneration
- LLM rewriting
- external actions
- assistant-assisted editing

## Success Criteria

Review edit is ready when:

- raw content remains immutable
- every edit has a revision snapshot
- every edit records `review_edited`
- edited values pass validation
- history shows edit events
- generated Markdown staleness is visible
- tests use synthetic data only
- no external action is triggered
