# PIE Git Publication Checklist

Use this checklist before `git init`, first commit, or publishing to GitHub.

## Must Be Ignored

- [ ] `.env` and `.env.*` files are ignored, except `.env.example`.
- [ ] SQLite data files are ignored: `*.db`, `*.sqlite`, `*.sqlite3`.
- [ ] SQLite sidecars are ignored: `*-wal`, `*-shm`, `*-journal`.
- [ ] Generated `notes/` and `reports/` are ignored.
- [ ] Runtime `logs/` and `*.log` are ignored.
- [ ] Python caches and build artifacts are ignored.
- [ ] IDE folders and temporary files are ignored.

## Must Not Be Present In The Commit

- [ ] Real personal notes, diary entries, summaries, or reports.
- [ ] Real `.env` files, API keys, tokens, passwords, or credentials.
- [ ] Local SQLite databases or WAL/SHM/journal files.
- [ ] Local absolute paths such as `C:\Users\...`, `/home/...`, or project-specific scratch paths.
- [ ] Real e-mail addresses, phone numbers, IDs, addresses, or third-party names not needed by the project.
- [ ] Logs from local runs.

## Expected Safe Content

- [ ] `examples/` contains synthetic data only.
- [ ] `tests/` contains synthetic fixtures only.
- [ ] README files say PIE is experimental alpha software.
- [ ] README files explain local-first behavior and privacy risks.
- [ ] `docs/privacy.md` explains `.env`, local databases, notes, reports, logs, and optional local LLM risks.
- [ ] `docs/troubleshooting.md` contains no real machine paths or secrets.

## Suggested Commands

Run these before the first commit:

```bash
python -m pytest -q
python -m compileall personal_intelligence_engine
ruff check .
```

Search for common sensitive patterns:

```bash
rg -n --hidden -S "api[_-]?key|secret|password|token|bearer|authorization|sk-|ghp_|xox|AKIA"
rg -n --hidden -S "C:\\Users\\|/home/|/Users/"
rg -n --hidden -S "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}"
```

After `git init`, check what Git would include:

```bash
git status --short
git check-ignore -v .env pie.db notes reports logs
```

## License

MIT is a good fit for a small developer-facing local-first tool. Add a `LICENSE` file only after confirming that choice.
