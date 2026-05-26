"""Tests for SQLite schema constraints."""

import shutil
import sqlite3
from pathlib import Path

import pytest

from personal_intelligence_engine.app.config import Config
from personal_intelligence_engine.app.repositories.database import Database

_MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def test_schema_migrations_table_exists(app):
    row = app.db.fetchone(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'schema_migrations';"
    )

    assert row is not None


def test_migration_003_is_applied(app):
    row = app.db.fetchone(
        "SELECT version FROM schema_migrations WHERE version = ?;",
        ("003_create_structured_entry_revisions",),
    )

    assert row is not None


def test_structured_entry_revisions_table_exists(app):
    row = app.db.fetchone(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'structured_entry_revisions';"
    )

    assert row is not None


def test_structured_entry_revisions_have_foreign_keys(app):
    rows = app.db.fetchall("PRAGMA foreign_key_list(structured_entry_revisions);")
    references = {(row["from"], row["table"], row["to"]) for row in rows}

    assert ("structured_entry_id", "structured_entries", "id") in references
    assert ("raw_entry_id", "raw_entries", "id") in references


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


def test_structured_entry_revisions_reject_invalid_foreign_keys(app):
    with pytest.raises(sqlite3.IntegrityError):
        app.db.execute(
            """
            INSERT INTO structured_entry_revisions
                (id, structured_entry_id, raw_entry_id, before_json, after_json,
                 changed_fields_json, reason, actor, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                "revision-missing-parents",
                "missing-structured-entry",
                "missing-raw-entry",
                '{"summary": "Before"}',
                '{"summary": "After"}',
                '["summary"]',
                None,
                "user",
                "2026-05-09T00:00:00+00:00",
            ),
        )


@pytest.mark.parametrize(
    "action",
    ["review_approved", "review_rejected", "review_edited"],
)
def test_audit_logs_accept_review_actions(app, action):
    app.db.execute(
        """
        INSERT INTO audit_logs
            (id, raw_entry_id, action, actor, method, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """,
        (
            f"audit-{action}",
            None,
            action,
            "user",
            "human_review",
            "success",
            "2026-05-09T00:00:00+00:00",
        ),
    )
    app.db.commit()

    row = app.db.fetchone("SELECT action FROM audit_logs WHERE id = ?;", (f"audit-{action}",))
    assert row["action"] == action


def test_audit_logs_reject_invalid_action(app):
    with pytest.raises(sqlite3.IntegrityError):
        app.db.execute(
            """
            INSERT INTO audit_logs
                (id, raw_entry_id, action, actor, method, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (
                "audit-invalid-action",
                None,
                "review.invalid",
                "user",
                "human_review",
                "success",
                "2026-05-09T00:00:00+00:00",
            ),
        )


def test_migration_002_preserves_existing_audit_logs(work_dir):
    first_migrations_dir = work_dir / "migrations_first"
    first_migrations_dir.mkdir()
    shutil.copyfile(
        _MIGRATIONS_DIR / "001_initial_schema.sql",
        first_migrations_dir / "001_initial_schema.sql",
    )

    config = Config(
        database_path=work_dir / "migration-test.db",
        notes_dir=work_dir / "notes",
        reports_dir=work_dir / "reports",
        migrations_dir=first_migrations_dir,
        extractor_backend="fake",
    )
    db = Database(config)
    try:
        db.run_migrations()
        db.execute(
            """
            INSERT INTO audit_logs
                (id, raw_entry_id, action, actor, method, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (
                "existing-audit-log",
                None,
                "entry_created",
                "system",
                "test",
                "success",
                "2026-05-09T00:00:00+00:00",
            ),
        )
        db.commit()
    finally:
        db.close()

    second_migrations_dir = work_dir / "migrations_second"
    second_migrations_dir.mkdir()
    shutil.copyfile(
        _MIGRATIONS_DIR / "001_initial_schema.sql",
        second_migrations_dir / "001_initial_schema.sql",
    )
    shutil.copyfile(
        _MIGRATIONS_DIR / "002_add_review_audit_actions.sql",
        second_migrations_dir / "002_add_review_audit_actions.sql",
    )

    config = Config(
        database_path=work_dir / "migration-test.db",
        notes_dir=work_dir / "notes",
        reports_dir=work_dir / "reports",
        migrations_dir=second_migrations_dir,
        extractor_backend="fake",
    )
    db = Database(config)
    try:
        db.run_migrations()
        preserved = db.fetchone("SELECT action FROM audit_logs WHERE id = ?;", ("existing-audit-log",))
        assert preserved["action"] == "entry_created"

        db.execute(
            """
            INSERT INTO audit_logs
                (id, raw_entry_id, action, actor, method, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (
                "new-review-audit-log",
                None,
                "review_approved",
                "user",
                "human_review",
                "success",
                "2026-05-09T00:00:00+00:00",
            ),
        )
        db.commit()

        applied = {
            row["version"]
            for row in db.fetchall("SELECT version FROM schema_migrations ORDER BY version;")
        }
        assert "002_add_review_audit_actions" in applied
    finally:
        db.close()
