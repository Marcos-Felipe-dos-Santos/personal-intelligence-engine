# Phase 2D: Human-In-The-Loop Review Design

This document defines the technical design for Phase 2D.

Implementation status:

- `pie review list` is implemented as read-only.
- `pie review show <id>` is implemented as read-only.
- `pie review approve <id>` is implemented as the first controlled write action.
- `pie review reject <id>` and `pie review edit <id>` are not implemented.

## Objective

Human review makes uncertain extraction output explicit, inspectable, and correctable before it is treated as reliable memory.

The first implementation should let the user:

- list entries that need review
- inspect raw and structured data side by side
- approve an acceptable extraction
- reject an extraction that should not be trusted
- leave editing for a later step

## Why This Comes Before The Assistant Layer

The future Assistant Layer should rely on PIE Core as a trustworthy memory source. If low-confidence or uncertain entries can silently become trusted context, an assistant could summarize or act on weak information.

Human review comes first because it establishes:

- a clear boundary between unreviewed and trusted memory
- source visibility for uncertain entries
- auditability for approval and rejection decisions
- safer foundations for future assistant answers

## Which Entries Enter Review

The current extraction confidence threshold is:

```text
confidence < 0.70
```

Rule:

- Entries with `confidence < 0.70` enter `needs_review`.
- No uncertain entry should be treated as reliable memory without review.
- Reports and future assistant answers should distinguish reviewed memory from unreviewed memory when possible.

Future implementations may also route entries to review for other reasons, such as schema validation issues, extractor errors, ambiguous project assignment, or user-requested manual review.

## Planned Status Model

Current code already uses `needs_review` and `processed`. Phase 2D documents the minimum review state vocabulary before implementation.

| State | Meaning |
|-------|---------|
| `needs_review` | Extraction is uncertain and needs human decision. |
| `reviewed` | Human has approved or edited the structured interpretation. |
| `rejected` | Human rejected the structured interpretation as unreliable or not useful. |
| `processed` | Entry was processed without requiring review, or remains the existing non-review success state. |

Implementation note: `reviewed` and `rejected` are planned states, not current enum values. The implementation phase must decide whether they belong in `EntryStatus`, `ValidationStatus`, a dedicated review field, or a future review table.

## Planned Commands

### `pie review list`

Lists entries in `needs_review`.

Expected output should include:

- raw entry ID
- structured entry ID, if available
- entry type
- confidence
- created timestamp
- short summary

### `pie review show <id>`

Shows review details for one entry.

The command should display:

- raw entry content
- structured summary
- entry type
- project
- tags
- confidence
- validation status
- related IDs
- audit history summary, if available

### `pie review approve <id>`

Approves the current structured extraction.

Status: implemented.

Rules:

- approval is local-only
- no external actions are triggered
- the entry leaves the review queue
- the action is audit logged
- approval does not rewrite raw content

### `pie review reject <id>`

Rejects the current structured extraction as not trustworthy.

Rules:

- rejection is local-only
- no external actions are triggered
- rejected entries should not be treated as reliable memory
- the action is audit logged
- raw content remains preserved

### `pie review edit <id>` Future

Editing is intentionally not part of the first implementation unless the data model is explicitly designed first.

Future edit rules:

- edits must preserve raw entry content
- previous structured values should remain auditable
- edited structured values must pass Pydantic validation
- the edit action must be audit logged
- the user should see a before/after preview

## Approval Rules

Approval means the user accepts the current structured interpretation as usable memory.

Approval should:

- require explicit user intent
- operate on a single entry at first
- mark the entry as reviewed or otherwise remove it from the review queue
- keep structured entry ID and raw entry ID visible
- record `review_approved` in audit logs

Approval should not:

- call external tools
- create assistant actions
- send data outside the machine
- hide low-confidence history

## Rejection Rules

Rejection means the user does not trust the current structured interpretation.

Rejection should:

- require explicit user intent
- preserve raw entry content
- prevent the structured output from being treated as reliable memory
- record `review_rejected` in audit logs

Rejection should not:

- delete raw data automatically
- delete audit history
- call external tools
- permanently destroy evidence without a separate deletion workflow

## Future Edit Rule

Editing should wait until the data model can preserve review history clearly.

Minimum future requirement:

- edited data must be validated
- prior extracted values must remain traceable
- edited entries must be distinguishable from model-only extractions
- `review_edited` must be audit logged

## Future Audit Actions

Planned review audit actions:

- `review_approved`
- `review_rejected`
- `review_edited`

Audit records should include:

- raw entry ID
- structured entry ID, if available
- actor
- timestamp
- review action
- short sanitized reason, if provided

Audit records should not store unnecessary raw personal content.

## Privacy Risks

Human review surfaces raw entries and structured interpretations together. This is useful but sensitive.

Risks:

- raw text may contain personal information
- summaries may expose sensitive inferences
- rejected entries may still remain in the database
- terminal output can be copied or logged by the shell environment

Mitigations:

- keep review local-only
- do not send review data to external services
- avoid storing raw content in audit error messages
- remind users not to commit `pie.db`, `notes/`, `reports/`, logs, or `.env`
- prefer explicit IDs and short summaries in list views

## Success Criteria

Phase 2D succeeds when:

- `pie review list` shows entries that need review
- `pie review show <id>` displays raw and structured data clearly
- `pie review approve <id>` removes an entry from the review queue and records an audit event
- `pie review reject <id>` prevents the structured output from being treated as reliable memory and records an audit event
- entries with `confidence < 0.70` enter review
- uncertain entries are not treated as trusted memory without review
- tests use synthetic data only
- no external action is triggered by review commands
- implementation remains local-first and auditable

## Out Of Scope For First Implementation

- editing structured data
- batch approval
- batch rejection
- assistant integration
- email, calendar, or external actions
- RAG
- embeddings
- new UI
- deletion workflows
