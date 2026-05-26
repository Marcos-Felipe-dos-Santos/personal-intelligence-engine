# PIE Roadmap

PIE is experimental alpha software. The roadmap now separates the durable memory engine, called **PIE Core**, from a possible future **Assistant Layer**.

Core comes first. The Assistant Layer should only build on top of Core after review, search, traceability, and approval rules are mature.

## Block A: Repository And Docs Stabilization

Status: mostly complete.

- [x] Package, CLI, tests, and CI are in place.
- [x] Privacy documentation and Git publication checklist exist.
- [x] README files describe alpha status and local-first privacy risks.
- [x] Synthetic extraction quality fixtures exist.
- [x] Deterministic scoring, runner, Markdown report, and CLI evaluation exist.
- [x] Current state, Core v1 gaps, vision, and future assistant architecture are documented.
- [ ] Keep documentation aligned as Core v1 evolves.

## Block B: Finish PIE Core v1

Goal: make PIE Core reliable as a local memory, validation, review, search, and reporting system.

- [ ] Phase 2D: Human-in-the-loop review workflow for `needs_review` entries.
- [x] Add entries list/show commands.
- [x] Add local textual search.
- [ ] Add safe reprocessing for existing raw entries.
- [ ] Add weekly reports.
- [ ] Add project-specific reports.
- [ ] Add backup/export guidance or command.
- [ ] Strengthen source citation in every memory-like output.
- [ ] Expand tests for review, search, reprocessing, and reporting.

See [Core v1 Gap Analysis](core_v1_gap_analysis.md).

### Phase 2D: Human-In-The-Loop Review

Design: [Human Review Design](human_review_design.md).
Edit design: [Review Edit Design](review_edit_design.md).

Planned first implementation:

- [ ] `pie review list`
- [ ] `pie review show <id>`
- [ ] `pie review approve <id>`
- [ ] `pie review reject <id>`
- [ ] audit actions for `review_approved` and `review_rejected`
- [ ] keep review local-only with no external actions

Deferred:

- [ ] `pie review edit <id>` using a revision/snapshot model
- [ ] batch review actions
- [ ] assistant-assisted review

## Block C: Assistant Foundation

Goal: design the Assistant Layer as a separate interaction layer that uses PIE Core as memory and tooling.

- [ ] Define assistant intent categories.
- [ ] Define tool contracts for safe Core access.
- [ ] Prototype read-only assistant queries against Core data.
- [ ] Require source citations in assistant answers.
- [ ] Keep the assistant separate from the Core source of truth.
- [ ] Document limits and user expectations.

See [Vision](vision.md) and [Assistant Architecture](assistant_architecture.md).

## Block D: Approval Layer

Goal: require explicit user approval before writes, external actions, or sensitive operations.

- [ ] Define action risk levels.
- [ ] Add preview-before-write behavior.
- [ ] Require confirmation for database writes.
- [ ] Require confirmation for file creation, export, or deletion.
- [ ] Audit approved actions.
- [ ] Block prohibited actions by default.

## Block E: External Read-Only Integrations

Goal: allow carefully scoped read-only context after Core and approval rules are mature.

- [ ] Define read-only connector policy.
- [ ] Start with local files or exports, not live external writes.
- [ ] Keep integrations opt-in.
- [ ] Show what data was read.
- [ ] Avoid storing unnecessary sensitive content.
- [ ] Add tests with synthetic data only.

## Block F: Controlled Write Integrations

Goal: support write-capable tools only after the Approval Layer is reliable.

- [ ] Require explicit confirmation for every write.
- [ ] Show clear action previews.
- [ ] Record audit events for approved writes.
- [ ] Provide undo or recovery guidance where possible.
- [ ] Keep dangerous or irreversible actions out of scope until proven safe.

## Block G: Optional Voice Or Local UI

Goal: improve interaction only after Core and approval foundations are stable.

- [ ] Explore local UI options.
- [ ] Explore optional local voice input/output.
- [ ] Avoid voice cloning or character cloning.
- [ ] Keep microphone behavior explicit and opt-in.
- [ ] Keep text interface fully usable without voice.

## Non-Goals For The Current Horizon

- No autonomous external actions.
- No voice cloning.
- No fictional character cloning.
- No cloud-first architecture.
- No external write integrations before the Approval Layer.
- No RAG or embeddings before Core v1 search and review are complete.
- No dashboard until Core workflows are mature enough to justify it.
