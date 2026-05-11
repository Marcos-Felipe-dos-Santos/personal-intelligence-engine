# PIE — Roadmap

## Phase 1: Foundation ✅ (Current)

- [x] Project structure and packaging
- [x] SQLite database with migrations
- [x] Pydantic schemas with validation
- [x] FakeExtractor (deterministic, no LLM)
- [x] Full pipeline: ingest → extract → validate → markdown → audit
- [x] CLI: `pie add` and `pie report daily`
- [x] Markdown notes with YAML frontmatter
- [x] Daily reports with entry citations
- [x] Audit logging for all pipeline events
- [x] Low confidence detection and review flagging
- [x] Test suite covering all pipeline stages
- [x] Documentation: architecture, privacy, data model

## Phase 2: Local LLM Integration

- [x] Phase 2A: Add optional Ollama-backed LocalLLMExtractor
- [x] Implement extractor interface/protocol for swappable adapters
- [x] Add prompt versioning and audit tracking
- [x] Phase 2B: Add health check, retry/backoff, and troubleshooting docs
- [ ] Compare FakeExtractor vs LLM results
- [ ] Add confidence calibration
- [ ] Add model-quality regression suite

## Phase 3: Enhanced Input Sources

- [ ] File-based input (drag-and-drop text files)
- [ ] Clipboard capture
- [ ] Multi-line input mode in CLI
- [ ] Batch import from JSON
- [ ] Input deduplication via content_hash

## Phase 4: Search and Query

- [ ] Full-text search in SQLite (FTS5)
- [ ] Query by entry type, date range, project
- [ ] Tag-based filtering
- [ ] `pie search` CLI command

## Phase 5: Enhanced Reports

- [ ] Weekly and monthly reports
- [ ] Project-specific reports
- [ ] Trend analysis (entry type distribution over time)
- [ ] Export to PDF

## Phase 6: Review Workflow

- [ ] `pie review` command for needs_review entries
- [ ] Manual reclassification
- [ ] Confidence override
- [ ] Feedback loop for extractor improvement

## Phase 7: Integrations (Optional)

- [ ] ActivityWatch integration
- [ ] Wakapi integration
- [ ] Calendar integration
- [ ] Browser extension for web captures

## Non-Goals

The following are explicitly **out of scope**:

- Cloud synchronization
- Mobile applications
- Dashboard / Web UI (in early phases)
- Email or messaging integration
- Autonomous agents
- Passive computer monitoring
