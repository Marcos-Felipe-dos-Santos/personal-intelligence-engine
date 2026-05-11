# PIE — Personal Intelligence Engine

![CI](https://github.com/Marcos-Felipe-dos-Santos/personal-intelligence-engine/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

A **local-first** engine for capturing, structuring, and projecting personal knowledge.

PIE captures unstructured text entries, extracts structured data, validates it, persists everything in a local SQLite database, and generates human-readable Markdown notes and reports.

## Status

PIE is experimental alpha software. It is intended for local development and synthetic examples at this stage, not as a finished privacy product.

## Privacy First

PIE can store sensitive personal data in local SQLite databases, generated Markdown notes, reports, and audit logs. Do not commit real `pie.db`, `notes/`, `reports/`, `.env`, logs, or local generated data to Git. The repository examples are synthetic only.

## ✨ Features

- 📝 **Capture** — Add text entries via CLI
- 🔍 **Extract** — Automatic classification using keyword-based extraction (LLM-ready architecture)
- ✅ **Validate** — Pydantic schema validation with confidence scoring
- 💾 **Persist** — SQLite as the single source of truth
- 📄 **Project** — Markdown notes with YAML frontmatter
- 📊 **Report** — Daily reports with entry summaries
- 🔒 **Audit** — Full pipeline traceability via audit logs
- 🏠 **Local-first** — No cloud, no external APIs, no telemetry

## 🚀 Quick Start

### Installation

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
   Confidence:    85%
   Validation:    valid
   Note:          notes/e5f6g7h8-....md
```

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

### Optional Local LLM Extraction

PIE uses the deterministic `FakeExtractor` by default. It does not require Ollama, cloud APIs, or any external service.

To keep the default behavior:

```bash
PIE_EXTRACTOR_BACKEND=fake
```

Experimental Ollama support is available as an optional local adapter:

```bash
PIE_EXTRACTOR_BACKEND=ollama
PIE_OLLAMA_BASE_URL=http://localhost:11434
PIE_OLLAMA_MODEL=<your-local-model>
PIE_LLM_TIMEOUT_SECONDS=30
PIE_LLM_MAX_RETRIES=2
PIE_LLM_RETRY_BACKOFF_SECONDS=1
```

Then run:

```bash
pie add "Eu decidi testar a extracao local com Ollama"
```

If Ollama is not running or the model is not configured, PIE reports a clear error and does not silently fall back to `FakeExtractor`.

Check the configured extractor without creating an entry:

```bash
pie doctor
```

See [docs/troubleshooting.md](docs/troubleshooting.md) for Ollama health checks, retry settings, and common error messages.

### Run Tests

```bash
python -m pytest -q
```

## 📁 Project Structure

```
personal_intelligence_engine/
├── app/
│   ├── main.py              # Application orchestrator
│   ├── config.py             # Configuration management
│   ├── domain/
│   │   ├── schemas.py        # Pydantic models
│   │   └── types.py          # Enums and constants
│   ├── services/             # Business logic layer
│   ├── adapters/             # Swappable implementations
│   │   ├── fake_extractor.py # Deterministic extractor
│   │   └── markdown_writer.py
│   ├── repositories/         # Data access layer
│   │   └── database.py       # SQLite management
│   └── cli/
│       └── commands.py       # Click CLI commands
├── migrations/
│   └── 001_initial_schema.sql
├── tests/
├── docs/
│   ├── architecture.md
│   ├── privacy.md
│   ├── data_model.md
│   └── roadmap.md
└── examples/
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
- [Data Model](docs/data_model.md)
- [Privacy](docs/privacy.md)
- [Roadmap](docs/roadmap.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Git Publication Checklist](docs/git_publication_checklist.md)

## 🌍 Português

Documentação em português disponível em [README.pt-BR.md](README.pt-BR.md).

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
