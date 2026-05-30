# PIE Troubleshooting

## Extractor Health Check

Run:

```bash
pie doctor
```

With the default backend, the command should report:

```text
[OK] Extractor backend: fake
```

With Ollama enabled, `pie doctor` checks that the local server is reachable and that the configured model is installed. It does not create entries in the database.

`pie doctor` also prints the absolute paths currently used for the SQLite database, notes, reports, backups, and exports. Before real controlled use, confirm that the database path is the one you expect.

## Relative Path Warning

If `pie doctor` reports:

```text
Relative path detected. Running PIE from a different working directory may create/use a different database.
```

then one or more configured paths are relative. This is valid, but it can be confusing because running `pie` from another directory may point to a different `pie.db` or output folder. For real data, prefer absolute paths in `.env` when needed:

```env
PIE_DATABASE_PATH=C:\path\to\private\pie.db
PIE_NOTES_DIR=C:\path\to\private\notes
PIE_REPORTS_DIR=C:\path\to\private\reports
PIE_BACKUP_DIR=C:\path\to\private\backups
PIE_EXPORT_DIR=C:\path\to\private\exports
```

`PIE_HOME` is not implemented yet; keep path configuration explicit for now.

## Default FakeExtractor

`FakeExtractor` remains the default and needs no external service:

```env
PIE_EXTRACTOR_BACKEND=fake
```

## Optional Ollama Backend

Ollama is experimental and opt-in:

```env
PIE_EXTRACTOR_BACKEND=ollama
PIE_OLLAMA_BASE_URL=http://localhost:11434
PIE_OLLAMA_MODEL=<your-local-model>
PIE_LLM_TIMEOUT_SECONDS=30
PIE_LLM_MAX_RETRIES=2
PIE_LLM_RETRY_BACKOFF_SECONDS=1
```

## Common Errors

| Message | Meaning | Suggested action |
|---------|---------|------------------|
| `Invalid extractor backend` | `PIE_EXTRACTOR_BACKEND` is not `fake` or `ollama` | Set it to `fake` or `ollama` |
| `Ollama model is not configured` | `PIE_OLLAMA_MODEL` is empty | Set it to an installed local model |
| `Ollama base URL is invalid` | URL is missing `http://` or `https://` | Use `http://localhost:11434` |
| `Ollama is unavailable` | The local server cannot be reached | Start Ollama and run `pie doctor` again |
| `timed out` | Ollama did not answer before the timeout | Increase timeout or check local load |
| `not valid JSON` | The model returned text that is not JSON | Try a stronger local model or revise the prompt |
| `schema is invalid` | JSON was valid but did not match PIE's schema | Check `entry_type`, `confidence`, and required fields |

## Retry Behavior

PIE retries only transient transport failures such as timeout and local connection errors. It does not retry invalid JSON, schema errors, or empty responses because those are model/prompt output problems rather than transport problems.

Retries are intentionally small:

```env
PIE_LLM_MAX_RETRIES=2
PIE_LLM_RETRY_BACKOFF_SECONDS=1
```

## Privacy Notes

Audit logs record backend, model name, prompt version, status, and a short error summary. They do not store the full raw entry as an error message.
