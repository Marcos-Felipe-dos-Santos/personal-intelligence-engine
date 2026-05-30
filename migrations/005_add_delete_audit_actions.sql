-- PIE -- Personal Intelligence Engine
-- Migration 005: Add delete/restore/purge audit actions
-- SQLite cannot alter CHECK constraints in place, so this recreates audit_logs
-- while preserving all existing rows.

PRAGMA foreign_keys=OFF;

CREATE TABLE audit_logs_new (
    id TEXT PRIMARY KEY,
    raw_entry_id TEXT,
    action TEXT NOT NULL
        CHECK (action IN (
            'entry_created',
            'extraction_completed',
            'validation_completed',
            'structured_entry_created',
            'markdown_generated',
            'report_generated',
            'low_confidence',
            'validation_failed',
            'review_approved',
            'review_rejected',
            'review_edited',
            'entry_deleted',
            'entry_restored',
            'entries_purged'
        )),
    actor TEXT NOT NULL CHECK (length(trim(actor)) > 0),
    method TEXT,
    model_name TEXT,
    prompt_version TEXT,
    input_hash TEXT,
    output_hash TEXT,
    status TEXT NOT NULL CHECK (status IN ('success', 'warning', 'error')),
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (raw_entry_id) REFERENCES raw_entries(id)
);

INSERT INTO audit_logs_new (
    id,
    raw_entry_id,
    action,
    actor,
    method,
    model_name,
    prompt_version,
    input_hash,
    output_hash,
    status,
    error_message,
    created_at
)
SELECT
    id,
    raw_entry_id,
    action,
    actor,
    method,
    model_name,
    prompt_version,
    input_hash,
    output_hash,
    status,
    error_message,
    created_at
FROM audit_logs;

DROP TABLE audit_logs;
ALTER TABLE audit_logs_new RENAME TO audit_logs;

PRAGMA foreign_keys=ON;
