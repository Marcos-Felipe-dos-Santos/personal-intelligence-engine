# PIE — Privacy Policy

## Philosophy

PIE is designed as a **local-first** application. Your data never leaves your machine unless you explicitly choose to share it.

PIE is experimental software. Treat the local database, generated notes, generated reports, and audit logs as sensitive personal-data artifacts.

## Data Storage

| Data Type | Location | Versioned? | Notes |
|-----------|----------|-----------|-------|
| SQLite database | `pie.db` (configurable) | ❌ No | Contains all raw and structured entries |
| Markdown notes | `notes/` | ❌ No | Human-readable projections |
| Reports | `reports/` | ❌ No | Generated summaries |
| Audit logs | Inside SQLite | ❌ No | Pipeline event trail |
| Configuration | `.env` | ❌ No | Local settings |

## Git Safety Rules

Never commit real runtime data to Git:

- `.env` or any `.env.*` file with local secrets or paths.
- SQLite databases such as `pie.db`, `*.db`, `*.sqlite`, and `*.sqlite3`.
- SQLite sidecar files such as `*-wal`, `*-shm`, and `*-journal`.
- Generated `notes/` and `reports/`.
- Runtime logs and local scratch files.

Only commit synthetic examples under `examples/` and synthetic fixtures under `tests/`.

## Privacy Risks

### Current Risks (Phase 1)

1. **SQLite is unencrypted**: The database file is a plain SQLite file. Anyone with file system access can read it.
   - *Mitigation*: Use OS-level disk encryption (BitLocker, FileVault, LUKS).

2. **Markdown files are plaintext**: Notes in `notes/` are human-readable.
   - *Mitigation*: Ensure `notes/` and `reports/` are in `.gitignore` (already configured).

3. **Content hashes are stored**: SHA-256 hashes of content are stored for deduplication.
   - *Risk level*: Low — hashes cannot be reversed to reconstruct content.

4. **Audit logs may contain metadata**: Action names, timestamps, and method names are logged.
   - *Risk level*: Low — no content is stored in audit logs.

### Optional Local LLM Risks

5. **Local LLM memory usage**: Running a local LLM can consume significant RAM/VRAM.
   - *Mitigation*: This is a resource concern, not a privacy concern.

6. **Prompt exposure to local services**: When `PIE_EXTRACTOR_BACKEND=ollama`, raw entry text is sent to the configured local Ollama server.
   - *Mitigation*: Use only trusted local models and endpoints. Do not point PIE at remote or shared servers unless you understand the privacy impact.

7. **Model output in structured_json**: Extracted data may contain sensitive interpretations.
   - *Mitigation*: All data stays local. Review `structured_entries` periodically.

8. **Cloud LLM risk**: Cloud APIs are not required by PIE. If a user adds one in the future, prompts and raw entries could leave the machine.
   - *Mitigation*: Keep cloud APIs out of the default path and document any opt-in integration separately.

## Recommendations

1. **Enable disk encryption** on the machine running PIE.
2. **Never commit** `pie.db`, `notes/`, `reports/`, `.env`, or logs to version control.
3. **Back up** your SQLite database regularly to an encrypted location.
4. **Review** entries marked as `needs_review` — they may contain misclassified data.
5. **Do not use** cloud LLM APIs with PIE without understanding the privacy implications.
6. **Run a publication check** before creating a public repository. See [git_publication_checklist.md](git_publication_checklist.md).

## Data Deletion

To delete all PIE data:

1. Delete the SQLite database file (default: `pie.db`).
2. Delete the `notes/` directory.
3. Delete the `reports/` directory.

There is no cloud sync, no telemetry, and no analytics.
