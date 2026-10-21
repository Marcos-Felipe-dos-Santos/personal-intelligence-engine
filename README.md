# PIE — Personal Intelligence Engine

![CI](https://github.com/Marcos-Felipe-dos-Santos/personal-intelligence-engine/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

A **local-first** engine for capturing, structuring, and projecting personal knowledge.

PIE captures unstructured text entries, extracts structured data, validates it, persists everything in a local SQLite database, and generates human-readable Markdown notes and reports.

## Status

PIE Core is experimental alpha software with a local CLI workflow for capture, human review, search, reports, and recovery. It is ready to begin a controlled pilot with synthetic data. The Assistant Layer is not implemented yet.

Local validation on Windows with Python 3.13 passed **405 tests**, Ruff, compilation, and an installed-wheel smoke test outside the repository. CI is configured for Windows and Ubuntu with Python 3.10 through 3.13. A real Ollama model and the seven-day pilot still need validation. Start with the [controlled test checklist (Portuguese)](docs/test_readiness.pt-BR.md).

## Privacy First

PIE can store sensitive personal data in local SQLite databases, generated Markdown notes, reports, and audit logs. Do not commit real `pie.db`, `notes/`, `reports/`, `.env`, logs, or local generated data to Git. The repository examples are synthetic only.

## ✨ Features

- 📝 **Capture** — Add text entries via CLI
- 🔍 **Extract** — Heuristic keyword classification and an optional local Ollama adapter
- ✅ **Validate** — Pydantic schema validation with confidence scoring
- 💾 **Persist** — SQLite as the single source of truth
- 📄 **Project** — Markdown notes with YAML frontmatter
- 📊 **Report** — Daily, weekly, project, decisions, and candidate-task reports
- ✅ **Human review** — Approval, rejection, and editing with revision history
- 🛠️ **Recovery** — Resume failed captures and rebuild notes from the database
- 🔒 **Audit** — Full pipeline traceability via audit logs
- 🏠 **Local-first** — No required cloud or telemetry; remote Ollama endpoints blocked by default
- 🔎 **Search** — Local text search across all entries

## 🚀 Quick Start

### Installation

Requires Python 3.10 or later. On Windows, installation includes `tzdata` for IANA timezones. Create the virtual environment on the current machine; recreate environments copied from another installation.

```bash
# Clone the repository
git clone https://github.com/Marcos-Felipe-dos-Santos/personal-intelligence-engine.git
cd personal-intelligence-engine

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Linux/macOS)
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"
```

Before capturing entries, configure a fixed data directory as described under [Configuration](#configuration), or use the [isolated test checklist](docs/test_readiness.pt-BR.md). Verify the paths with `pie doctor`.

### Usage

#### Add an entry

```bash
pie add "Eu decidi usar SQLite para o projeto"
```

Output:
```
✅ Entry created successfully!
   Entry ID:      a1b2c3d4-...
   Structured ID: e5f6g7h8-...
   Type:          decision
   Confidence:    60%
   Validation:    needs_review
   Note:          notes/e5f6g7h8-....md
```

`FakeExtractor` confidence reflects deterministic rules, not the probability of a correct classification. Use `--project`, `--type`, and `--tag` for explicit fields, and review entries marked `needs_review`.

#### Review entries

```bash
pie review list
pie review show <structured_entry_id>
pie review approve <structured_entry_id>
pie review reject <structured_entry_id>
pie review history <structured_entry_id>
```

Approval and rejection update the Markdown note as well as the database. Raw text remains unchanged.

#### Generate a daily report

```bash
pie report daily --date 2026-05-09
```

`--date` is interpreted as a local calendar day. Timestamps remain stored in UTC, and the default local timezone is `America/Sao_Paulo`. Set `PIE_LOCAL_TIMEZONE` to another IANA timezone if needed.

Output:
```
📊 Daily report generated!
   Report ID:    i9j0k1l2-...
   Date:         2026-05-09
   Entries:      3
   File:         reports/daily_2026-05-09.md
```

#### Generate a weekly report

```bash
pie report weekly --date 2026-05-26
```

Generates a Markdown report of the local week containing the specified date (Monday to Sunday), grouping entries by type and validation status.

Output:
```
[OK] Weekly report generated!
   Report ID:    w3x4y5z6-...
   Start Date:   2026-05-25
   End Date:     2026-05-31
   Entries:      8
   File:         reports/weekly_2026-05-25_to_2026-05-31.md
```

#### Generate a project report

```bash
pie report project --project PIE
```

Generates a Markdown report of entries associated with the exact project name.

Output:
```
[OK] Project report generated!
   Report ID:    p7q8r9s0-...
   Project:      PIE
   Entries:      12
   File:         reports/project_PIE.md
```

#### Generate a decisions report

```bash
pie report decisions
pie report decisions --project PIE
pie report decisions --since 2026-01-01
```

Generates a Markdown list of all `decision` entries, grouped by project. Supports optional `--project` and `--since YYYY-MM-DD` filters. Output file: `decisions_all.md` or `decisions_<project>.md`.

#### Generate a tasks report

```bash
pie report tasks
pie report tasks --project PIE
```

Generates a Markdown list of `candidate_task` entries with status `valid` or `needs_review`. Excludes invalid and soft-deleted entries. Output file: `tasks_pending.md` or `tasks_pending_<project>.md`.

Task completion is not tracked yet; the report uses validation status to select candidate tasks.

Reports are saved in `reports/`, cite structured/raw source entry IDs, and are ignored by Git.

#### Edit an entry under review

```bash
pie review edit <structured_entry_id> --summary "New summary"
pie review edit <structured_entry_id> --project PIE
pie review edit <structured_entry_id> --entry-type decision
```

Edits one or more structured fields (`summary`, `project`, `entry_type`) while preserving `raw_entries.content` unchanged. Records a before/after revision in `structured_entry_revisions` and writes an audit log entry. Regenerates the Markdown note after a successful edit.

To clear the project, use `--project " "`; whitespace also works in shells that discard empty arguments.

#### List entries

```bash
pie entries list
pie entries list --type decision
pie entries list --project PIE --limit 10
pie entries list --status needs_review
```

#### Show entry details

```bash
pie entries show <structured_entry_id>
```

#### Search entries

```bash
pie search "SQLite"
pie search "SQLite" --type decision
pie search "pipeline" --project PIE
pie search "review" --status needs_review
```

Search looks for text in raw content, summary, project, and structured JSON (including tags). Results show a short snippet and the match source.

#### Backup and Export

```bash
# Create a local database backup
pie backup create

# Export all database tables into a single JSON file
pie export json

# Export structured entries grouped by entry type as a Markdown summary
pie export markdown
```

Backups are saved in `backups/` and exports in `exports/` (both directories are ignored by Git). These directories are configurable via `PIE_BACKUP_DIR` and `PIE_EXPORT_DIR`.

SQLite backups and JSON exports are full database snapshots and may include soft-deleted entries. Markdown export is a human-readable active-entry summary and excludes soft-deleted entries.

#### Delete and restore entries

```bash
pie entries delete <structured_entry_id>
pie entries restore <structured_entry_id>
pie entries purge --older-than 30
```

Deletion is reversible until purged. Purge permanently removes entries soft-deleted more than the specified number of days ago and asks for confirmation. Older backups, exports, and reports may retain copies.

#### Recover failed captures and notes

```bash
pie entries failed
pie entries retry <raw_entry_id>
pie entries rebuild-note <structured_entry_id>
```

`failed` lists recoverable pending/error raw IDs without showing content. `retry` resumes extraction while preserving the original text and raw ID. `rebuild-note` reconstructs a note from SQLite without rerunning extraction.

If editing, reviewing, or reprocessing commits the database change but fails to write the note, the CLI displays a warning and a rebuild command. Batch summaries count that entry as applied with a note needing recovery.

SQL migrations are transactional, including version recording and foreign-key verification. `pie doctor` reports pending migrations without applying them; normal operations apply migrations during initialization.

#### Reprocessing Stored Entries

```bash
# Preview changes for a specific entry (dry-run)
pie entries reprocess <structured_entry_id> --dry-run

# Reprocess a specific entry and apply changes
pie entries reprocess <structured_entry_id>

# Preview changes for entries with needs_review status (dry-run)
pie entries reprocess --status needs_review --dry-run --limit 5

# Reprocess entries with needs_review status and apply changes
pie entries reprocess --status needs_review
```

> [!IMPORTANT]
> Always create a backup (e.g. `pie backup create`) before running reprocessing to protect your SQLite database. Reprocessing saves revisions to the database and regenerates the Markdown note for each reprocessed entry. The note regeneration occurs after the database commit; if the file write fails, the CLI reports the database change as applied, warns that the note is stale, and provides a `pie entries rebuild-note <id>` recovery command.
>
> Batch reprocessing is transactional per entry, not all-or-nothing for the whole batch. If an entry fails before the database commit, its changes are rolled back while earlier successful entries remain applied. A subsequent note write failure is reported separately and does not undo committed data. The command output reports total selected, total applied, total failed, applied IDs, failed IDs, and a short error per failed ID. `raw_entries.content` is never edited by reprocessing.

### Optional Local LLM Extraction

PIE uses the deterministic `FakeExtractor` by default. It does not require Ollama, cloud APIs, or any external service.

To keep the default behavior:

```bash
export PIE_EXTRACTOR_BACKEND=fake
```

Experimental Ollama support is available as an optional local adapter:

```bash
export PIE_EXTRACTOR_BACKEND=ollama
export PIE_OLLAMA_BASE_URL=http://localhost:11434
export PIE_OLLAMA_MODEL='your-installed-model'
export PIE_LLM_TIMEOUT_SECONDS=30
export PIE_LLM_MAX_RETRIES=2
export PIE_LLM_RETRY_BACKOFF_SECONDS=1
```

For PowerShell, use `$env:PIE_EXTRACTOR_BACKEND = 'ollama'`, `$env:PIE_OLLAMA_MODEL = 'your-installed-model'`, and the same `$env:NAME = 'value'` syntax for the other settings.

Then run:

```bash
pie add "Eu decidi testar a extracao local com Ollama"
```

If Ollama is not running or the model is not configured, PIE reports a clear error and does not silently fall back to `FakeExtractor`.

Check the configured extractor without creating an entry:

```bash
pie doctor
```

Run the synthetic extraction quality evaluation without creating database entries:

```bash
pie evaluate extraction --backend fake
pie evaluate extraction --backend fake --output reports/evaluation/fake.md
pie evaluate extraction --backend fake --min-score 0.8
```

`--min-score` exits with an error if the synthetic average falls below the threshold, keeping the report when `--output` is supplied. The current fake backend averages approximately 52.26%, with 0/9 cases meeting the 80% passing score, so the last command is expected to fail. The lexical score includes confidence expectations that differ from the heuristic calibration and does not measure semantic accuracy.

See [docs/troubleshooting.md](docs/troubleshooting.md) for Ollama health checks, retry settings, and common error messages.

### Configuration

#### PIE_HOME — fixed data root (recommended)

```bash
export PIE_HOME="$HOME/.pie"   # recommended before real use
```

In PowerShell:

```powershell
$env:PIE_HOME = Join-Path $env:USERPROFILE '.pie'
pie doctor
```

When `PIE_HOME` is set, all runtime paths (`pie.db`, `notes/`, `reports/`, `backups/`, `exports/`) are resolved under that directory. Without `PIE_HOME`, paths are resolved from the current working directory — running PIE from different directories creates separate databases.

Individual paths can still be overridden via their own env vars (`PIE_DATABASE_PATH`, `PIE_NOTES_DIR`, etc.), and an absolute path always wins over the `PIE_HOME`-relative default.

### Run Tests

```bash
python -m pytest -q
python -m ruff check .
python -m compileall -q personal_intelligence_engine
```

Tests use temporary directories and disable local configuration loading. To validate the installed package too:

```bash
python -m pip wheel . --no-deps --wheel-dir dist
python tests/smoke_installed_wheel.py dist/personal_intelligence_engine-0.1.0-py3-none-any.whl
```

The wheel includes SQL migrations, the versioned prompt, and synthetic evaluation fixtures. The smoke exercises capture, search, reports, backup, export, and evaluation outside the source checkout.

## 📁 Project Structure

```
personal-intelligence-engine/
├── personal_intelligence_engine/
│   └── app/
│       ├── main.py           # Application orchestrator
│       ├── config.py         # Configuration management
│       ├── cli/              # Click CLI commands
│       ├── domain/           # Pydantic schemas and enums
│       ├── services/         # Business logic
│       ├── repositories/     # SQLite persistence
│       ├── adapters/         # Extractors and Markdown writer
│       ├── migrations/       # Packaged SQL migrations
│       ├── prompts/          # Versioned LLM prompt
│       └── evaluation/       # Scoring, reports and synthetic fixtures
├── tests/                    # Unit, integration and wheel smoke tests
├── docs/                     # Architecture, privacy and test playbooks
├── examples/                 # Synthetic examples
└── pyproject.toml
```

## 🔑 Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| SQLite | Simple, portable, no server needed |
| Pydantic | Strong validation with clear error messages |
| Click | Clean CLI framework with good UX |
| FakeExtractor | Deterministic testing without LLM dependency |
| Markdown as projection | Human-readable output, not the source of truth |
| UUID strings | Portable, collision-resistant identifiers |
| Audit log | Full traceability for debugging and trust |

## 🔒 Privacy

All runtime data stays on your machine by design, but local files are plaintext unless protected by your OS. See [docs/privacy.md](docs/privacy.md) before using real personal data.

## 📋 Roadmap

See [docs/roadmap.md](docs/roadmap.md) for the full development plan.

## 📖 Documentation

- [Architecture](docs/architecture.md)
- [Current State](docs/current_state.md)
- [Controlled Test Checklist (Portuguese)](docs/test_readiness.pt-BR.md)
- [7-Day Usage Playbook](docs/usage_playbook.md)
- [Vision](docs/vision.md)
- [Assistant Architecture](docs/assistant_architecture.md)
- [Data Model](docs/data_model.md)
- [Core v1 Gap Analysis](docs/core_v1_gap_analysis.md)
- [Privacy](docs/privacy.md)
- [Roadmap](docs/roadmap.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Git Publication Checklist](docs/git_publication_checklist.md)

## 🌍 Português

Documentação em português disponível em [README.pt-BR.md](README.pt-BR.md).

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
