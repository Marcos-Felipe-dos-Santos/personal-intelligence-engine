# PIE — Architecture

## Overview

PIE (Personal Intelligence Engine) is a **local-first** knowledge capture and structuring engine. All data stays on your machine, in a SQLite database.

## Layers

```
┌──────────────────────────┐
│        CLI (Click)       │  ← User-facing commands
├──────────────────────────┤
│       PIEApp (main)      │  ← Orchestrator / Facade
├──────────────────────────┤
│       Services           │  ← Business logic
│  ┌──────────┬──────────┐ │
│  │Ingestion │Extraction│ │
│  │Validation│ Markdown │ │
│  │  Audit   │  Report  │ │
│  └──────────┴──────────┘ │
├──────────────────────────┤
│      Repositories        │  ← Data access (SQLite)
│  ┌──────────┬──────────┐ │
│  │ Entries  │  Audit   │ │
│  │ Reports  │ Database │ │
│  └──────────┴──────────┘ │
├──────────────────────────┤
│       Adapters           │  ← Swappable implementations
│  ┌──────────┬──────────┐ │
│  │  Fake    │ Markdown │ │
│  │Extractor │  Writer  │ │
│  └──────────┴──────────┘ │
├──────────────────────────┤
│     Domain (Pydantic)    │  ← Schemas, types, enums
└──────────────────────────┘
```

## Key Principles

1. **Local-first**: No cloud, no external APIs required.
2. **SQLite as source of truth**: All data lives in a single `.db` file.
3. **Markdown as projection**: Notes in `notes/` are human-readable projections, NOT the source of truth.
4. **Services don't touch sqlite3**: All DB access goes through repositories.
5. **Adapters are swappable**: `FakeExtractor` can be replaced with a real LLM adapter without changing services.
6. **Pydantic for validation**: All data flowing through the system is validated.
7. **Audit trail**: Every pipeline action is logged for traceability.

## Data Flow

```
User Input (text)
    │
    ▼
┌─────────────┐
│  Ingestion  │ → raw_entries table
│  Service    │ → audit_logs (entry_created)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Extraction │ → ExtractionResult (Pydantic)
│  Service    │ → audit_logs (extraction_completed)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Validation  │ → structured_entries table
│  Service    │ → audit_logs (validation_completed)
└──────┬──────┘ → audit_logs (low_confidence) if applicable
       │
       ▼
┌─────────────┐
│  Markdown   │ → notes/*.md files
│  Service    │ → generated_files table
└──────┬──────┘ → audit_logs (markdown_generated)
       │
       ▼
   Done ✅
```

## Future: LLM Integration

The `ExtractionService` accepts any extractor that implements `extract(content: str) -> ExtractionResult`. To add a real LLM:

1. Create `adapters/llm_extractor.py` implementing the same interface.
2. Pass it to `ExtractionService(extractor=LLMExtractor(...))`.
3. No service layer changes needed.

## Phase 2A: Optional Local LLM Adapter

PIE can optionally use `LocalLLMExtractor` with an Ollama-compatible local server. This is experimental and opt-in.

- `PIE_EXTRACTOR_BACKEND=fake` keeps the deterministic default.
- `PIE_EXTRACTOR_BACKEND=ollama` selects the local LLM adapter.
- Ollama must be configured with `PIE_OLLAMA_BASE_URL`, `PIE_OLLAMA_MODEL`, and `PIE_LLM_TIMEOUT_SECONDS`.
- The adapter returns the same `ExtractionResult` schema as `FakeExtractor`.
- LLM output is parsed as JSON and validated with Pydantic before persistence.
- Invalid JSON, schema errors, timeouts, unavailable Ollama, and missing model configuration fail with controlled errors.
- PIE does not silently fall back to `FakeExtractor` when `ollama` is selected explicitly.

## Phase 2B: Reliability and Diagnostics

The optional Ollama backend now includes a lightweight health check through `pie doctor`.

- `fake` health check confirms the deterministic extractor is available.
- `ollama` health check validates the base URL, model configuration, server availability, and model presence.
- Transient connection and timeout failures use a small retry/backoff policy.
- Invalid JSON, empty responses, and schema errors are not retried.
- Extraction audit logs include backend method, model name, prompt version, status, and a short sanitized error summary.
- Health checks do not create raw entries or structured entries.
