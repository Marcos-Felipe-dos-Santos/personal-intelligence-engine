"""Tests for robustness features: soft delete, restore, purge, and doctor migrations/deep health checks."""

import re
import sqlite3
from pathlib import Path

from click.testing import CliRunner

from personal_intelligence_engine.app.adapters.local_llm_extractor import (
    LocalLLMExtractor,
)
from personal_intelligence_engine.app.cli.commands import cli
from personal_intelligence_engine.app.config import Config
from personal_intelligence_engine.app.main import PIEApp


def _configure_temp_env(monkeypatch, work_dir) -> None:
    monkeypatch.setenv("PIE_DATABASE_PATH", str(work_dir / "pie.db"))
    monkeypatch.setenv("PIE_NOTES_DIR", str(work_dir / "notes"))
    monkeypatch.setenv("PIE_REPORTS_DIR", str(work_dir / "reports"))
    monkeypatch.setenv("PIE_EXTRACTOR_BACKEND", "fake")


# 1. Soft delete / restore / purge tests
def test_soft_delete_lifecycle(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    runner = CliRunner()

    # Add entry
    add_res = runner.invoke(cli, ["add", "Eu decidi usar SQLite no projeto sintetico", "--auto-approve"])
    assert add_res.exit_code == 0
    match = re.search(r"Structured ID:\s+([0-9a-f-]+)", add_res.output)
    sid = match.group(1)

    # 1. Ensure it appears in entries list
    list_res = runner.invoke(cli, ["entries", "list"])
    assert sid in list_res.output

    # 2. Ensure search finds it
    search_res = runner.invoke(cli, ["search", "SQLite"])
    assert sid in search_res.output

    # 3. Soft delete it
    del_res = runner.invoke(cli, ["entries", "delete", sid, "--yes"])
    assert del_res.exit_code == 0
    assert "deleted" in del_res.output.lower()

    # 4. List and search should not return it
    list_res2 = runner.invoke(cli, ["entries", "list"])
    assert sid not in list_res2.output

    search_res2 = runner.invoke(cli, ["search", "SQLite"])
    assert sid not in search_res2.output

    # 5. Show detail should return error since it's deleted
    show_res = runner.invoke(cli, ["entries", "show", sid])
    assert show_res.exit_code != 0

    # 6. Verify audit log entry_deleted is recorded
    with sqlite3.connect(work_dir / "pie.db") as conn:
        conn.row_factory = sqlite3.Row
        logs = conn.execute("SELECT action, actor, method, status FROM audit_logs WHERE action = 'entry_deleted';").fetchall()
        assert len(logs) == 1
        assert logs[0]["action"] == "entry_deleted"
        assert logs[0]["actor"] == "user"
        assert logs[0]["status"] == "success"

    # 7. Restore the entry
    restore_res = runner.invoke(cli, ["entries", "restore", sid])
    assert restore_res.exit_code == 0
    assert "restored" in restore_res.output.lower()

    # 8. List/Search/Show should work again
    list_res3 = runner.invoke(cli, ["entries", "list"])
    assert sid in list_res3.output

    # 9. Verify restore audit log
    with sqlite3.connect(work_dir / "pie.db") as conn:
        conn.row_factory = sqlite3.Row
        logs = conn.execute("SELECT action, status FROM audit_logs WHERE action = 'entry_restored';").fetchall()
        assert len(logs) == 1
        assert logs[0]["status"] == "success"


def test_purge_deleted_entries(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    runner = CliRunner()

    # Add two entries
    sid1 = re.search(r"Structured ID:\s+([0-9a-f-]+)", runner.invoke(cli, ["add", "Decidi usar SQLite", "--auto-approve"]).output).group(1)
    sid2 = re.search(r"Structured ID:\s+([0-9a-f-]+)", runner.invoke(cli, ["add", "Tive uma ideia", "--auto-approve"]).output).group(1)

    with sqlite3.connect(work_dir / "pie.db") as conn:
        raw_id = conn.execute("SELECT raw_entry_id FROM structured_entries WHERE id = ?;", (sid1,)).fetchone()[0]

    # Soft delete one
    runner.invoke(cli, ["entries", "delete", sid1, "--yes"])

    # Purge with older-than 0 (to delete immediately)
    purge_res = runner.invoke(cli, ["entries", "purge", "--older-than", "0", "--yes"])
    assert purge_res.exit_code == 0
    assert "Permanently deleted 1 entries" in purge_res.output

    # Verify in DB: sid1 is completely gone from structured_entries and raw_entries
    with sqlite3.connect(work_dir / "pie.db") as conn:
        assert conn.execute("SELECT COUNT(*) FROM structured_entries WHERE id = ?;", (sid1,)).fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM raw_entries WHERE id = ?;", (raw_id,)).fetchone()[0] == 0
        # sid2 is still there
        assert conn.execute("SELECT COUNT(*) FROM structured_entries WHERE id = ?;", (sid2,)).fetchone()[0] == 1

    # Verify purge audit log
    with sqlite3.connect(work_dir / "pie.db") as conn:
        logs = conn.execute("SELECT action, status FROM audit_logs WHERE action = 'entries_purged';").fetchall()
        assert len(logs) == 1


# 2. Database migrations pending and applied introspection tests
def test_migration_introspection(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    config = Config(
        database_path=work_dir / "pie_migration_test.db",
        notes_dir=work_dir / "notes",
        reports_dir=work_dir / "reports",
        migrations_dir=Path(__file__).resolve().parent.parent / "migrations",
        extractor_backend="fake",
    )

    db = PIEApp(config).db
    try:
        applied = db.applied_migrations()
        pending = db.pending_migrations()
        assert len(applied) > 0
        assert len(pending) == 0

        # Verify applied are in version order
        versions = [version for version, _ in applied]
        assert versions == sorted(versions)
    finally:
        db.close()


def test_pie_doctor_shows_migrations(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    runner = CliRunner()

    # Run doctor
    res = runner.invoke(cli, ["doctor"])
    assert res.exit_code == 0
    assert "Schema Migrations:" in res.output
    # Database is not created yet, so:
    assert "Current Schema Version: -" in res.output
    assert "Pending migrations (" in res.output

    # Create DB by adding an entry
    runner.invoke(cli, ["add", "Eu decidi usar SQLite", "--auto-approve"])

    # Run doctor again
    res2 = runner.invoke(cli, ["doctor"])
    assert res2.exit_code == 0
    assert "Current Schema Version:" in res2.output
    assert "005_add_delete_audit_actions" in res2.output
    assert "Pending migrations: none" in res2.output


# 3. Ollama local validations: deep health check / doctor --deep
class MockSuccessOllamaClient:
    def list_models(self, *, base_url, timeout_seconds):
        return ["test-model"]
    def generate(self, *, base_url, model, prompt, timeout_seconds):
        return {
            "response": '{"entry_type": "decision", "summary": "Valid test decision.", "confidence": 0.85, "tags": ["test"], "extra": {}}'
        }


class MockInvalidJSONOllamaClient:
    def list_models(self, *, base_url, timeout_seconds):
        return ["test-model"]
    def generate(self, *, base_url, model, prompt, timeout_seconds):
        return {"response": "invalid json response"}


class MockSuspiciousConfidenceOllamaClient:
    def list_models(self, *, base_url, timeout_seconds):
        return ["test-model"]
    def generate(self, *, base_url, model, prompt, timeout_seconds):
        return {
            "response": '{"entry_type": "decision", "summary": "Valid summary.", "confidence": 1.0, "tags": [], "extra": {}}'
        }



def test_deep_health_check_success():
    extractor = LocalLLMExtractor(
        base_url="http://localhost:11434",
        model="test-model",
        http_client=MockSuccessOllamaClient(),
    )
    health = extractor.deep_health_check()
    assert health.ok is True
    assert "produces valid extractions" in health.message
    assert len(health.warnings) == 0


def test_deep_health_check_invalid_json():
    extractor = LocalLLMExtractor(
        base_url="http://localhost:11434",
        model="test-model",
        http_client=MockInvalidJSONOllamaClient(),
    )
    health = extractor.deep_health_check()
    assert health.ok is False
    assert "extraction failed" in health.message


def test_deep_health_check_suspicious_confidence():
    extractor = LocalLLMExtractor(
        base_url="http://localhost:11434",
        model="test-model",
        http_client=MockSuspiciousConfidenceOllamaClient(),
    )
    health = extractor.deep_health_check()
    # It responds, so deep health check ok could be True but with warnings!
    assert health.ok is True
    assert len(health.warnings) > 0
    assert any("Suspicious confidence" in w for w in health.warnings)


def test_pie_doctor_deep_propagates_warnings(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    monkeypatch.setenv("PIE_EXTRACTOR_BACKEND", "ollama")
    monkeypatch.setenv("PIE_OLLAMA_MODEL", "test-model")

    # We mock check_extractor_backend to return ok=True with warnings
    def mock_check(config, http_client=None, deep=False):
        return {
            "ok": True,
            "backend": "ollama",
            "message": "Warnings present.",
            "model_name": "test-model",
            "prompt_version": "v1",
            "warnings": ["Suspicious confidence: 1.5"]
        }

    monkeypatch.setattr("personal_intelligence_engine.app.cli.commands.check_extractor_backend", mock_check)

    runner = CliRunner()
    res = runner.invoke(cli, ["doctor", "--deep"])
    assert res.exit_code == 0
    assert "Warnings:" in res.output
    assert "Suspicious confidence: 1.5" in res.output
