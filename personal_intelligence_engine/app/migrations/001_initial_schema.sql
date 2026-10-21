-- PIE — Personal Intelligence Engine
-- Migration 001: Initial schema
-- Applied via personal_intelligence_engine.app.repositories.database

CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS raw_entries (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL CHECK (length(trim(content)) > 0),
    source TEXT NOT NULL CHECK (length(trim(source)) > 0),
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'processed', 'needs_review', 'error')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    metadata_json TEXT,
    content_hash TEXT NOT NULL CHECK (length(content_hash) = 64)
);

CREATE TABLE IF NOT EXISTS structured_entries (
    id TEXT PRIMARY KEY,
    raw_entry_id TEXT NOT NULL,
    entry_type TEXT NOT NULL
        CHECK (entry_type IN (
            'log',
            'idea',
            'insight',
            'candidate_task',
            'reference',
            'decision',
            'problem',
            'review',
            'general_note'
        )),
    project TEXT,
    summary TEXT NOT NULL CHECK (length(trim(summary)) > 0),
    confidence REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    structured_json TEXT NOT NULL CHECK (length(trim(structured_json)) > 0),
    validation_status TEXT NOT NULL DEFAULT 'valid'
        CHECK (validation_status IN ('valid', 'needs_review', 'invalid')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (raw_entry_id) REFERENCES raw_entries(id)
);

CREATE TABLE IF NOT EXISTS audit_logs (
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
            'validation_failed'
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

CREATE TABLE IF NOT EXISTS generated_files (
    id TEXT PRIMARY KEY,
    raw_entry_id TEXT,
    file_type TEXT NOT NULL CHECK (length(trim(file_type)) > 0),
    path TEXT NOT NULL CHECK (length(trim(path)) > 0),
    content_hash TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (raw_entry_id) REFERENCES raw_entries(id)
);

CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    report_type TEXT NOT NULL CHECK (length(trim(report_type)) > 0),
    date_start TEXT NOT NULL,
    date_end TEXT NOT NULL,
    summary TEXT NOT NULL CHECK (length(trim(summary)) > 0),
    file_path TEXT,
    source_entry_ids_json TEXT NOT NULL DEFAULT '[]'
        CHECK (length(trim(source_entry_ids_json)) > 0),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
