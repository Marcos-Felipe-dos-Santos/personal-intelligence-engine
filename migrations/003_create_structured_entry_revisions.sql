-- PIE -- Personal Intelligence Engine
-- Migration 003: Structured entry revision snapshots for future human edits

CREATE TABLE IF NOT EXISTS structured_entry_revisions (
    id TEXT PRIMARY KEY,
    structured_entry_id TEXT NOT NULL,
    raw_entry_id TEXT NOT NULL,
    before_json TEXT NOT NULL CHECK (length(trim(before_json)) > 0),
    after_json TEXT NOT NULL CHECK (length(trim(after_json)) > 0),
    changed_fields_json TEXT NOT NULL CHECK (length(trim(changed_fields_json)) > 0),
    reason TEXT,
    actor TEXT NOT NULL CHECK (length(trim(actor)) > 0),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (structured_entry_id) REFERENCES structured_entries(id),
    FOREIGN KEY (raw_entry_id) REFERENCES raw_entries(id)
);
