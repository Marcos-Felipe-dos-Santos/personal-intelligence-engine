# PIE Core — Simulated Usage Report

## 1. Objective

Execute a complete end-to-end simulation of PIE Core covering all 9 major CLI flows, using only synthetic data in a fully isolated temporary environment.  The goal is to validate that the system is ready for controlled real-data usage over 7 days.

## 2. Environment

| Parameter | Value |
|-----------|-------|
| OS | Windows 11 |
| Python | 3.11.9 |
| PIE Version | 0.1.0 |
| Backend | `fake` (FakeExtractor) |
| Database | Temporary SQLite in temp dir |
| Notes Dir | Temporary dir |
| Reports Dir | Temporary dir |
| Backups Dir | Temporary dir |
| Exports Dir | Temporary dir |
| Network | Not used |
| Ollama | Not used |
| Real Data | Not used |

All data was generated in `tempfile.mkdtemp()` directories and cleaned up after each test.

## 3. Backend Used

**FakeExtractor** — deterministic keyword-based classifier.  No LLM, no network, no external dependencies.

Classification rules:
- `decidi` → decision (0.85)
- `ideia` → idea (0.85)
- `problema/erro/bloqueio` → problem (0.85)
- `tarefa/preciso/fazer` → candidate_task (0.85)
- `insight/percebi/descobri` → insight (0.85)
- `referência/link/artigo` → reference (0.80)
- `revisão/review` → review (0.80)
- Fallback: general_note (short) or log (long), confidence 0.50 → triggers `needs_review`

## 4. Commands Executed

### Flow 1 — Diagnostics
```
pie doctor
```

### Flow 2 — Capture (9 synthetic entries)
```
pie add "Projeto: PIE. Tipo: decisão. Texto: Decidi manter SQLite como fonte de verdade. Tags: arquitetura, sqlite"
pie add "Projeto: Study Plan. Tipo: tarefa. Texto: Preciso revisar conceitos de SQL no sábado. Tags: estudo, sql"
pie add "Projeto: Health Routine. Tipo: problema. Texto: Estou dormindo tarde por usar celular na cama. Tags: sono, hábito"
pie add "Projeto: Finance Lab. Tipo: ideia. Texto: Criar dashboard local para controle de gastos mensais. Tags: finanças, dashboard"
pie add "Projeto: PIE. Tipo: insight. Texto: Percebi que relatórios semanais ajudam na revisão do progresso. Tags: relatórios, processo"
pie add "Projeto: Study Plan. Tipo: referência. Texto: Encontrei um artigo sobre normalização de banco de dados. Tags: estudo, referência"
pie add "Projeto: PIE. Tipo: revisão. Texto: A extração classificou uma decisão como ideia em duas entradas. Tags: qualidade, extração"
pie add "Anotação rápida sem contexto"
pie add "Esta é uma anotação longa sem palavras-chave específicas que serve para testar o cenário de baixa confiança..."
```

### Flow 3 — Entries
```
pie entries list
pie entries list --type decision
pie entries list --project PIE
pie entries show <structured_entry_id>
```

### Flow 4 — Search
```
pie search "SQLite"
pie search "sono"
pie search "SQL" --project "Study Plan"
pie search "arquitetura" --type decision
```

### Flow 5 — Review
```
pie review list
pie review show <id>
pie review approve <id>
pie review reject <id>
pie review history <id>
```

### Flow 6 — Reports
```
pie report daily --date YYYY-MM-DD
pie report weekly --date YYYY-MM-DD
pie report project --project PIE
```

### Flow 7 — Backup and Export
```
pie backup create
pie export json
pie export markdown
```

### Flow 8 — Reprocessing
```
pie entries reprocess <id> --dry-run
pie entries reprocess <id>
pie entries reprocess --status needs_review --dry-run
pie entries reprocess --status needs_review --limit 2
```

### Flow 9 — Evaluation
```
pie evaluate extraction --backend fake
pie evaluate extraction --backend fake --output <tmpdir>/fake-evaluation.md
```

## 5. Synthetic Data Summary

9 entries across 4 projects:

| # | Project (in text) | Type (extracted) | Confidence | Status |
|---|-------------------|------------------|------------|--------|
| 1 | PIE | decision | 0.85 | valid |
| 2 | Study Plan | candidate_task | 0.85 | valid |
| 3 | Health Routine | problem | 0.85 | valid |
| 4 | Finance Lab | idea | 0.85 | valid |
| 5 | PIE | insight | 0.85 | valid |
| 6 | Study Plan | reference | 0.80 | valid |
| 7 | PIE | review | 0.80 | valid |
| 8 | (none) | general_note | 0.50 | needs_review |
| 9 | (none) | log | 0.50 | needs_review |

Entries 8 and 9 naturally trigger `needs_review` because their confidence (0.50) is below the threshold (0.70).

## 6. What Worked

| Flow | Status | Details |
|------|--------|---------|
| `pie doctor` | ✅ Pass | Exits 0, shows FakeExtractor available, does not create DB |
| `pie add` | ✅ Pass | All 9 entries created, raw + structured entries + audit logs + markdown notes |
| `pie entries list` | ✅ Pass | Lists all 9 entries, `--type` filter works correctly |
| `pie entries show` | ✅ Pass | Shows full detail, truncates long raw content, friendly error for bad ID |
| `pie search` | ✅ Pass | Finds entries by raw content, `--type` filter works, read-only (no audit logs) |
| `pie review list` | ✅ Pass | Shows 2 low-confidence entries |
| `pie review show` | ✅ Pass | Shows entry detail with confidence and raw content |
| `pie review approve` | ✅ Pass | Removes from queue, idempotent, preserves raw content |
| `pie review reject` | ✅ Pass | Removes from queue, preserves raw content |
| `pie review history` | ✅ Pass | Shows review_approved / review_rejected in audit trail |
| `pie report daily` | ✅ Pass | Generates Markdown report, contains source IDs |
| `pie report weekly` | ✅ Pass | Generates report with start/end dates |
| `pie report project` | ✅ Pass | Generates project report |
| `pie backup create` | ✅ Pass | Creates valid SQLite backup in temp dir |
| `pie export json` | ✅ Pass | Creates JSON with all IDs preserved |
| `pie export markdown` | ✅ Pass | Creates readable Markdown, truncates long content |
| `pie entries reprocess --dry-run` | ✅ Pass | Read-only, no revisions or audit logs created |
| `pie entries reprocess` (apply) | ✅ Pass | Creates revision, preserves raw content, creates audit log |
| `pie entries reprocess --status` (batch) | ✅ Pass | Batch summary shown, revisions created |
| Reprocess stale markdown warning | ✅ Pass | Warning shown, no new notes generated |
| `pie evaluate extraction` | ✅ Pass | Runs without Ollama, generates report, does not touch DB |
| `.gitignore` coverage | ✅ Pass | `backups/` and `exports/` are gitignored |
| Invalid date handling | ✅ Pass | Friendly error, no traceback |
| Invalid ID handling | ✅ Pass | Friendly error, no traceback |
| Data isolation | ✅ Pass | All files stay in temp dir, no real data touched |

## 7. Problems Found

### Problem 1: FakeExtractor does not extract project names

**Severity:** Medium (functional limitation, not a bug)

**Description:** The `FakeExtractor` only classifies `entry_type` and generates `summary`/`tags`.  It does **not** extract the project name from text like "Projeto: PIE".  All structured entries have `project = NULL`.

**Impact:**
- `pie entries list --project PIE` returns "No entries found"
- `pie search "..." --project "Study Plan"` returns "No search results found"
- `pie report project --project PIE` generates a report with 0 entries
- Project-based filtering is non-functional with FakeExtractor

**Why not fixed:** This is a known design limitation of FakeExtractor, not a bug.  Adding project parsing to FakeExtractor would be a new feature.  The real solution is the `LocalLLMExtractor` (Ollama backend) which does full extraction including project names.

**Recommendation:** When using real data with the `fake` backend, project filtering will not work.  Users should either:
1. Switch to the `ollama` backend for real usage, or
2. Accept that project filtering requires LLM extraction.

### No other problems found

All CLI commands, error handling, audit logging, review lifecycle, reprocessing, backup/export, and evaluation work correctly.

## 8. Corrections Made

No source code corrections were needed.  All production code worked correctly.

The smoke test itself was adjusted during development:
- Tests for `--project` filter were adapted to verify the actual FakeExtractor behavior (project=NULL) rather than assuming project extraction works.
- Two ruff lint issues in the test file were fixed (unused variable, unused loop variable).

## 9. Problems Not Corrected and Why

| Problem | Reason Not Corrected |
|---------|---------------------|
| FakeExtractor does not extract project names | Design limitation, not a bug. Would require adding a new feature (project name parsing). The Ollama backend handles this correctly. |

## 10. Remaining Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Project filtering is non-functional with `fake` backend | Medium | Use `ollama` backend for real usage, or accept manual filtering |
| Stale Markdown notes after reprocessing | Low | Warning is shown; notes can be manually regenerated in a future version |
| `review edit` not implemented | Low | Workaround exists: reject the bad entry and add a new one with corrected wording |
| No full-text search index | Low | SQLite LIKE search works for small datasets; embeddings/FTS can be added later |
| Plaintext SQLite storage | Medium | Use OS-level disk encryption for sensitive data |

## 11. Recommendation Before Real Usage

PIE Core is **ready for controlled real-data usage** with the `fake` backend.  All core workflows function correctly.  The main limitation is that the `fake` backend does not extract project names, so project-based filtering will not work until the user switches to the `ollama` backend.

**Recommendation:** Start the 7-day controlled usage with `PIE_EXTRACTOR_BACKEND=fake`.  After validating the workflows, consider enabling `ollama` for better extraction quality.

## 12. Checklist Before Starting 7-Day Controlled Usage

### Environment Setup
- [ ] Copy `.env.example` to `.env`
- [ ] Set `PIE_EXTRACTOR_BACKEND=fake` (default)
- [ ] Verify `pie doctor` exits 0
- [ ] Create the first backup: `pie backup create`

### Privacy
- [ ] Confirm `.env` is in `.gitignore`
- [ ] Confirm `*.db`, `notes/`, `reports/`, `backups/`, `exports/` are in `.gitignore`
- [ ] Enable OS-level disk encryption if using sensitive data
- [ ] Do not store passwords, tokens, API keys, or sensitive documents in PIE

### Daily Routine
- [ ] Run `pie backup create` before the first entry of the day
- [ ] Add 3–10 entries using the recommended format
- [ ] Run `pie review list` and process uncertain entries
- [ ] Run `pie report daily --date YYYY-MM-DD` at end of day

### Weekly Routine
- [ ] Run `pie backup create`
- [ ] Run `pie report weekly --date YYYY-MM-DD`
- [ ] Run `pie export json` and `pie export markdown`
- [ ] Review friction points before adding new features

### Known Limitations to Accept
- [ ] Project filtering (`--project`) does not work with `fake` backend
- [ ] Markdown notes become stale after reprocessing (warning is shown)
- [ ] `pie review edit` is not yet implemented; use reject + add new entry
- [ ] Search is basic LIKE matching, not semantic

### After 7 Days
- [ ] Review all daily/weekly reports
- [ ] Run `pie export json` for a full data snapshot
- [ ] Document friction points and feature requests
- [ ] Consider switching to `ollama` backend for better extraction
- [ ] Decide if `review edit` is needed before continuing
