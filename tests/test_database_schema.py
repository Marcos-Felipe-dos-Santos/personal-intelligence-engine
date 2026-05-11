"""Tests for SQLite schema constraints."""

import sqlite3

import pytest


def test_schema_migrations_table_exists(app):
    row = app.db.fetchone(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'schema_migrations';"
    )

    assert row is not None


def test_structured_entries_reject_invalid_confidence(app):
    app.db.execute(
        """
        INSERT INTO raw_entries
            (id, content, source, status, created_at, updated_at, metadata_json, content_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            "raw-invalid-confidence",
            "Synthetic test entry",
            "test",
            "pending",
            "2026-05-09T00:00:00+00:00",
            "2026-05-09T00:00:00+00:00",
            None,
            "a" * 64,
        ),
    )
    app.db.commit()

    with pytest.raises(sqlite3.IntegrityError):
        app.db.execute(
            """
            INSERT INTO structured_entries
                (id, raw_entry_id, entry_type, project, summary, confidence,
                 structured_json, validation_status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                "structured-invalid-confidence",
                "raw-invalid-confidence",
                "idea",
                None,
                "Synthetic summary",
                1.1,
                "{}",
                "valid",
                "2026-05-09T00:00:00+00:00",
                "2026-05-09T00:00:00+00:00",
            ),
        )


def test_structured_entries_enforce_raw_entry_foreign_key(app):
    with pytest.raises(sqlite3.IntegrityError):
        app.db.execute(
            """
            INSERT INTO structured_entries
                (id, raw_entry_id, entry_type, project, summary, confidence,
                 structured_json, validation_status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                "structured-missing-raw",
                "missing-raw-entry",
                "idea",
                None,
                "Synthetic summary",
                0.8,
                "{}",
                "valid",
                "2026-05-09T00:00:00+00:00",
                "2026-05-09T00:00:00+00:00",
            ),
        )
