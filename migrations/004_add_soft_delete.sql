-- PIE -- Personal Intelligence Engine
-- Migration 004: Add soft-delete support for raw_entries and structured_entries

ALTER TABLE raw_entries ADD COLUMN deleted_at TEXT DEFAULT NULL;
ALTER TABLE structured_entries ADD COLUMN deleted_at TEXT DEFAULT NULL;
