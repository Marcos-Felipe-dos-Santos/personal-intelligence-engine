# PIE Roadmap

PIE is experimental alpha software. The roadmap separates the durable memory engine, called **PIE Core**, from a possible future **Assistant Layer**.

Core comes first. The Assistant Layer should only build on top of Core after review, search, reporting, traceability, and approval rules are mature enough for real use.

## Block A: Repository And Documentation Stabilization

Status: mostly complete.

- [x] Package, CLI, tests, and CI are in place.
- [x] Privacy documentation and Git publication checklist exist.
- [x] README files describe alpha status and local-first privacy risks.
- [x] Current state, Core v1 gaps, vision, and future assistant architecture are documented.
- [x] Synthetic extraction quality fixtures, scoring, runner, Markdown report, and CLI evaluation exist.
- [ ] Keep documentation aligned as Core evolves.

## Block B: Controlled Real Use Of PIE Core

Goal: validate the current Core workflow with careful local usage before broadening scope.

- [x] Capture entries with `pie add`.
- [x] Inspect entries with `pie entries list` and `pie entries show`.
- [x] Search entries with `pie search`.
- [x] Review uncertain entries with `pie review list/show/approve/reject/history`.
- [x] Reprocess entries safely with per-entry rollback and revisions.
- [x] Generate daily, weekly, and project reports.
- [x] Back up and export local data.
- [ ] Document a recommended real-use workflow.
- [ ] Identify rough edges from controlled usage.
- [ ] Polish CLI messages where they affect trust or safety.

See [Current State](current_state.md) and [Core v1 Gap Analysis](core_v1_gap_analysis.md).

## Block C: Finish PIE Core v1

Goal: close the remaining Core gaps without starting the Assistant Layer.

- [ ] Decide whether `pie review edit <id>` is required for Core v1 or can remain deferred.
- [ ] If implemented, use the existing `structured_entry_revisions` snapshot model.
- [ ] Improve stale-Markdown guidance after reprocessing or future edits.
- [ ] Strengthen source citation in every memory-like output.
- [ ] Keep backup/export and privacy warnings visible.
- [ ] Add tests for any UX polish or recovery flow changes.

Design references:

- [Human Review Design](human_review_design.md)
- [Review Edit Design](review_edit_design.md)

## Block D: Assistant Foundation

Goal: design the Assistant Layer as a separate interaction layer that uses PIE Core as memory and tooling.

- [ ] Define assistant intent categories.
- [ ] Define tool contracts for safe Core access.
- [ ] Prototype read-only assistant queries against Core data.
- [ ] Require source citations in assistant answers.
- [ ] Keep the assistant separate from the Core source of truth.
- [ ] Document limits and user expectations.

See [Vision](vision.md) and [Assistant Architecture](assistant_architecture.md).

## Block E: Approval Layer

Goal: require explicit user approval before writes, external actions, or sensitive operations.

- [ ] Define action risk levels.
- [ ] Add preview-before-write behavior.
- [ ] Require confirmation for database writes.
- [ ] Require confirmation for file creation, export, or deletion.
- [ ] Audit approved actions.
- [ ] Block prohibited actions by default.

## Block F: External Read-Only Integrations

Goal: allow carefully scoped read-only context only after Core and approval rules are mature.

- [ ] Define read-only connector policy.
- [ ] Start with local files or exports, not live external writes.
- [ ] Keep integrations opt-in.
- [ ] Show what data was read.
- [ ] Avoid storing unnecessary sensitive content.
- [ ] Add tests with synthetic data only.

## Block G: Controlled Write Integrations

Goal: support write-capable tools only after the Approval Layer is reliable.

- [ ] Require explicit confirmation for every write.
- [ ] Show clear action previews.
- [ ] Record audit events for approved writes.
- [ ] Provide undo or recovery guidance where possible.
- [ ] Keep dangerous or irreversible actions out of scope until proven safe.

## Block H: Optional Voice Or Local UI

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
- No RAG or embeddings before Core v1 workflows are practical.
- No dashboard until Core workflows are mature enough to justify it.
