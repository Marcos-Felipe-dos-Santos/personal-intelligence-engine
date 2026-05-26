# Future Assistant Architecture

This document describes a possible future Assistant Layer for PIE. It is not implemented yet.

The Assistant Layer should run in parallel with PIE Core. PIE Core remains the memory and evidence system; the assistant is an interaction and orchestration layer that uses Core through explicit tools.

## Target Shape

```text
CLI / Local UI
    -> Assistant Layer
    -> Intent Router
    -> Tool Registry
    -> Approval Layer
    -> PIE Core
    -> SQLite / Markdown / Audit
```

## Layer Responsibilities

### CLI / Local UI

The user-facing surface for asking questions, reviewing suggestions, and approving actions. This may start as CLI and only later become a local UI.

### Assistant Layer

Maintains conversational context for the current session, prepares tool calls, and presents grounded answers. It must not become the memory source of truth.

### Intent Router

Classifies requests into categories such as:

- ask about memory
- capture new memory
- review pending entries
- search entries
- generate report
- propose an external action
- explain system status

### Tool Registry

Defines available tools and their permissions. Tools should be explicit, typed, and testable.

Future internal tools may include:

- add raw entry
- list entries
- show entry
- search entries
- list review queue
- approve or edit reviewed extraction
- reprocess entry
- generate daily, weekly, or project report
- run extraction evaluation

Future external tools may include read-only connectors first, such as:

- read local calendar data
- read exported notes
- read local task files
- read local browser exports

Write-capable external tools should come later and only after the Approval Layer exists.

### Approval Layer

The Approval Layer decides whether an action can run automatically, must ask for confirmation, or is prohibited.

It should enforce:

- read-only before write
- local-only before external
- preview before mutation
- explicit confirmation for destructive actions
- audit records for approved actions

### PIE Core

Core remains responsible for raw entries, structured entries, validation, search, reports, Markdown projections, and audit logs.

### SQLite / Markdown / Audit

SQLite remains the source of truth. Markdown remains a projection. Audit logs record important transformations and actions.

## Read-Only Before Write Policy

The assistant should first learn to answer questions using read-only access to PIE Core.

Examples of allowed early behavior:

- search memory
- summarize entries with citations
- show review queue
- explain why an entry needs review
- generate a draft report without saving it

Examples that require later approval support:

- create a new entry
- edit a structured entry
- reprocess an entry
- save a report
- call an external write tool

## Human Approval Policy

Human approval should be required for:

- writing to the database
- changing review status
- replacing structured extraction output
- creating or deleting files
- sending data to any external service
- triggering external actions
- deleting or exporting personal data

Approval prompts should show what will happen, what data will be used, and how the action will be audited.

## Prohibited Actions For Now

The following should not be implemented until the Core and approval model are mature:

- autonomous external actions
- sending messages or emails
- modifying calendars
- contacting people
- spending money
- deleting data automatically
- voice cloning
- always-on microphone capture
- passive monitoring without explicit opt-in
- external write integrations
- RAG or embeddings as a substitute for Core v1 search and review

## Privacy Requirements

- The assistant must not hide the source of memory.
- Sensitive text should not be logged unnecessarily.
- External integrations must be opt-in.
- Local files such as `pie.db`, `.env`, `notes/`, `reports/`, and logs must remain out of Git.
- Users should be able to inspect what the assistant read before approving write actions.
