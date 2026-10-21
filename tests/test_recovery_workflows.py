"""Regression tests for interrupted migrations, preserved input and stale projections."""

import json
import shutil
import sqlite3
from pathlib import Path

import pytest
from click.testing import CliRunner

from personal_intelligence_engine.app.adapters.fake_extractor import FakeExtractor
from personal_intelligence_engine.app.adapters.markdown_writer import MarkdownWriter
from personal_intelligence_engine.app.cli.commands import cli
from personal_intelligence_engine.app.config import Config
from personal_intelligence_engine.app.main import PIEApp
from personal_intelligence_engine.app.repositories.database import Database


def _disk_failure(*args, **kwargs):
    raise PermissionError("Synthetic disk failure")


def test_failed_migration_rolls_back_ddl_and_can_retry(tmp_path):
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    script = migrations / "001_test.sql"
    script.write_text("CREATE TABLE example (id INTEGER); INSERT INTO absent VALUES (1);", encoding="utf-8")
    db = Database(Config(pie_home=tmp_path, migrations_dir=migrations))
    try:
        with pytest.raises(sqlite3.OperationalError, match="no such table"):
            db.run_migrations()
        assert db.fetchone("SELECT name FROM sqlite_master WHERE name = 'example';") is None
        assert db.applied_migrations() == []
        assert db.fetchone("PRAGMA foreign_keys;")[0] == 1
        script.write_text("CREATE TABLE example (id INTEGER); INSERT INTO example VALUES (1);", encoding="utf-8")
        db.run_migrations()
        assert db.fetchone("SELECT id FROM example;")[0] == 1
        assert db.applied_migrations()[0][0] == "001_test"
        db.run_migrations()
        assert db.fetchone("SELECT COUNT(*) FROM example;")[0] == 1
    finally:
        db.close()


def test_migration_verification_failure_rolls_back_version_and_schema(tmp_path, monkeypatch):
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    (migrations / "001_test.sql").write_text("CREATE TABLE example (id INTEGER);", encoding="utf-8")
    db = Database(Config(pie_home=tmp_path, migrations_dir=migrations))
    try:
        def fail_verification(version):
            raise RuntimeError("Synthetic verification failure")

        monkeypatch.setattr(db, "_verify_migration", fail_verification)
        with pytest.raises(RuntimeError, match="verification failure"):
            db.run_migrations()
        assert db.applied_migrations() == []
        assert db.fetchone("SELECT name FROM sqlite_master WHERE name = 'example';") is None
        assert db.fetchone("PRAGMA foreign_keys;")[0] == 1
    finally:
        db.close()


def test_missing_migrations_fail_explicitly(tmp_path):
    db = Database(Config(pie_home=tmp_path, migrations_dir=tmp_path / "missing"))
    try:
        with pytest.raises(ValueError, match="No SQL migrations"):
            db.run_migrations()
    finally:
        db.close()


def test_doctor_does_not_apply_pending_migrations(tmp_path, monkeypatch):
    migrations = tmp_path / "first_migration"
    migrations.mkdir()
    source = Config().migrations_dir / "001_initial_schema.sql"
    (migrations / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    db = Database(Config(pie_home=tmp_path, migrations_dir=migrations))
    db.run_migrations()
    db.close()
    monkeypatch.setenv("PIE_HOME", str(tmp_path))
    result = CliRunner().invoke(cli, ["doctor"])
    assert result.exit_code == 0, result.output
    assert "Pending migrations (4)" in result.output
    with sqlite3.connect(tmp_path / "pie.db") as conn:
        assert conn.execute("SELECT COUNT(*) FROM schema_migrations;").fetchone()[0] == 1
        assert "deleted_at" not in {row[1] for row in conn.execute("PRAGMA table_info(raw_entries);")}


@pytest.mark.parametrize("action,status", [("approve", "valid"), ("reject", "invalid")])
def test_review_updates_note_status(app, action, status):
    added = app.add_entry("Nota sintetica para revisao")
    method = getattr(app, f"{action}_review_entry")
    result = method(added["structured_entry_id"])
    assert result["projection_status"] == "updated"
    note = Path(added["note_path"]).read_text(encoding="utf-8")
    assert f"status: {status}" in note
    assert "needs human review" not in note


def test_review_can_clear_project_and_records_revision(app):
    added = app.add_entry("Decidi testar", project="ProjetoTeste")
    sid = added["structured_entry_id"]
    result = app.edit_review_entry(sid, project="  ")
    assert result["after"]["project"] is None
    detail = app.get_entry_detail(sid)
    assert detail["project"] is None
    revision = app.db.fetchone("SELECT after_json FROM structured_entry_revisions WHERE structured_entry_id = ?;", (sid,))
    assert json.loads(revision[0])["project"] is None
    assert "project: none" in Path(added["note_path"]).read_text(encoding="utf-8")


@pytest.mark.parametrize("operation", ["approve", "reject", "edit"])
def test_review_disk_failure_reports_committed_write(app, monkeypatch, operation):
    added = app.add_entry("Nota sintetica para revisao")
    sid = added["structured_entry_id"]
    with monkeypatch.context() as scoped:
        scoped.setattr(app.markdown, "generate_note", _disk_failure)
        if operation == "edit":
            result = app.edit_review_entry(sid, summary="Resumo corrigido")
            assert app.get_entry_detail(sid)["summary"] == "Resumo corrigido"
        else:
            result = getattr(app, f"{operation}_review_entry")(sid)
            expected = "valid" if operation == "approve" else "invalid"
            assert app.get_entry_detail(sid)["validation_status"] == expected
    assert result["projection_status"] == "stale"
    assert f"pie entries rebuild-note {sid}" in result["warning"]
    assert app.rebuild_note(sid)["projection_status"] == "updated"


def test_batch_counts_committed_changes_when_projection_fails(app, monkeypatch):
    added = app.add_entry("Decidi testar", auto_approve=True)
    sid = added["structured_entry_id"]
    monkeypatch.setattr(app.markdown, "generate_note", _disk_failure)
    result = app.reprocess_entries_by_status("valid", dry_run=False)
    assert result["failed"] == []
    assert len(result["applied"]) == 1
    assert result["applied"][0]["projection_status"] == "stale"
    assert app.get_entry_detail(sid)["validation_status"] == "needs_review"
    assert app.db.fetchone("SELECT COUNT(*) FROM structured_entry_revisions;")[0] == 1


def test_failed_input_can_be_recovered_without_duplicate_or_raw_edits(app, monkeypatch):
    text = "Decidi preservar esta entrada sintetica"
    with monkeypatch.context() as scoped:
        def fail_extraction(content):
            raise ValueError("Synthetic unavailable extractor")

        scoped.setattr(app.extraction, "extract", fail_extraction)
        with pytest.raises(ValueError, match="unavailable"):
            app.add_entry(text)
    rows = app.entries_repo.list_retry_candidates()
    assert len(rows) == 1
    rid = rows[0]["id"]
    before = app.entries_repo.get_raw_entry(rid)
    result = app.retry_raw_entry(rid)
    after = app.entries_repo.get_raw_entry(rid)
    assert result["entry_id"] == rid
    assert (before.content, before.content_hash, before.created_at) == (after.content, after.content_hash, after.created_at)
    assert after.content == text
    assert app.entries_repo.list_retry_candidates() == []
    assert app.db.fetchone("SELECT COUNT(*) FROM raw_entries;")[0] == 1
    assert app.db.fetchone("SELECT COUNT(*) FROM structured_entries;")[0] == 1
    with pytest.raises(ValueError, match="No recoverable"):
        app.retry_raw_entry(rid)


def test_retry_cli_lists_ids_without_raw_and_recovers_pending_input(tmp_path, monkeypatch):
    monkeypatch.setenv("PIE_HOME", str(tmp_path))
    app = PIEApp()
    with monkeypatch.context() as scoped:
        scoped.setattr(app.markdown, "generate_note", _disk_failure)
        with pytest.raises(PermissionError):
            app.add_entry("Texto sintetico que nao deve aparecer na listagem")
    rid = app.entries_repo.list_retry_candidates()[0]["id"]
    app.close()
    runner = CliRunner()
    listed = runner.invoke(cli, ["entries", "failed"])
    assert listed.exit_code == 0, listed.output
    assert rid in listed.output
    assert "Texto sintetico" not in listed.output
    recovered = runner.invoke(cli, ["entries", "retry", rid])
    assert recovered.exit_code == 0, recovered.output
    assert rid in recovered.output
    assert runner.invoke(cli, ["entries", "retry", rid]).exit_code != 0


def test_rebuild_note_does_not_run_extractor(app, monkeypatch):
    added = app.add_entry("Decidi testar uma reconstrucao")
    note = Path(added["note_path"])
    expected = note.read_text(encoding="utf-8")
    note.unlink()
    monkeypatch.setattr(app.extraction, "extract", _disk_failure)
    result = app.rebuild_note(added["structured_entry_id"])
    assert result["projection_status"] == "updated"
    assert note.read_text(encoding="utf-8") == expected


def test_backup_reopens_in_isolated_app_and_rebuilds_projection(app, tmp_path):
    added = app.add_entry("Decidi validar recuperacao do backup", project="Sintetico")
    app.edit_review_entry(added["structured_entry_id"], summary="Resumo preservado no backup")
    backup = Path(app.create_backup()["backup_path"])
    restored_home = tmp_path / "restored"
    restored_home.mkdir()
    restored_db = restored_home / "pie.db"
    shutil.copy2(backup, restored_db)
    restored = PIEApp(Config(pie_home=restored_home))
    try:
        assert restored.db.fetchone("PRAGMA integrity_check;")[0] == "ok"
        assert restored.db.fetchall("PRAGMA foreign_key_check;") == []
        detail = restored.get_entry_detail(added["structured_entry_id"])
        assert detail["summary"] == "Resumo preservado no backup"
        assert detail["raw_content"] == "Decidi validar recuperacao do backup"
        assert restored.db.fetchone("SELECT COUNT(*) FROM structured_entry_revisions;")[0] == 1
        rebuilt = restored.rebuild_note(added["structured_entry_id"])
        assert rebuilt["projection_status"] == "updated"
        assert "Resumo preservado no backup" in Path(rebuilt["note_path"]).read_text(encoding="utf-8")
    finally:
        restored.close()


def test_quality_gate_exits_nonzero_below_explicit_threshold():
    result = CliRunner().invoke(cli, ["evaluate", "extraction", "--backend", "fake", "--min-score", "0.8"])
    assert result.exit_code != 0
    assert "below threshold" in result.output
    assert "Extraction Quality Evaluation Report" in result.output


def test_quality_gate_keeps_report_when_output_is_saved(tmp_path):
    output = tmp_path / "quality.md"
    result = CliRunner().invoke(
        cli, ["evaluate", "extraction", "--backend", "fake", "--min-score", "0.8", "--output", str(output)]
    )
    assert result.exit_code != 0
    assert output.exists()
    assert "below threshold" in result.output


def test_fake_extractor_quality_baseline_does_not_regress():
    # Keep its current limitations explicit; these are synthetic lexical scores.
    from personal_intelligence_engine.app.cli.commands import EXTRACTION_QUALITY_FIXTURES
    from personal_intelligence_engine.app.evaluation.runner import evaluate_extractor

    run = evaluate_extractor(FakeExtractor(), EXTRACTION_QUALITY_FIXTURES, backend="fake")
    assert run.average_score >= 0.52


def test_cli_distinguishes_committed_batch_from_stale_note(tmp_path, monkeypatch):
    monkeypatch.setenv("PIE_HOME", str(tmp_path))
    runner = CliRunner()
    assert runner.invoke(cli, ["add", "Decidi testar o lote", "--auto-approve"]).exit_code == 0
    with monkeypatch.context() as scoped:
        scoped.setattr(MarkdownWriter, "write_note", _disk_failure)
        result = runner.invoke(cli, ["entries", "reprocess", "--status", "valid"])
    assert result.exit_code == 0, result.output
    assert "Total applied: 1" in result.output
    assert "Total failed:   0" in result.output
    assert "Notes needing rebuild: 1" in result.output
    assert "Database changes are saved" in result.output
    assert "rebuild-note" in result.output


def test_rebuild_cli_can_repair_note_and_reports_persistent_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("PIE_HOME", str(tmp_path))
    app = PIEApp()
    added = app.add_entry("Decidi testar reconstrucao via CLI")
    app.close()
    note = Path(added["note_path"])
    note.unlink()
    runner = CliRunner()
    with monkeypatch.context() as scoped:
        scoped.setattr(MarkdownWriter, "write_note", _disk_failure)
        failed = runner.invoke(cli, ["entries", "rebuild-note", added["structured_entry_id"]])
    assert failed.exit_code != 0
    assert "Database changes are saved" in failed.output
    assert not note.exists()
    result = runner.invoke(cli, ["entries", "rebuild-note", added["structured_entry_id"]])
    assert result.exit_code == 0, result.output
    assert note.exists()


def test_failed_atomic_replace_preserves_previous_note(app, monkeypatch):
    added = app.add_entry("Decidi testar escrita atomica")
    note = Path(added["note_path"])
    before = note.read_bytes()
    with monkeypatch.context() as scoped:
        scoped.setattr("personal_intelligence_engine.app.adapters.markdown_writer.os.replace", _disk_failure)
        result = app.edit_review_entry(added["structured_entry_id"], summary="Novo resumo")
    assert result["projection_status"] == "stale"
    assert note.read_bytes() == before
    assert list(note.parent.iterdir()) == [note]
    assert app.rebuild_note(added["structured_entry_id"])["projection_status"] == "updated"
    assert "Novo resumo" in note.read_text(encoding="utf-8")


def test_retry_excludes_deleted_raw_input(app):
    # Simulate input preserved before extraction, then marked as deleted.
    from personal_intelligence_engine.app.domain.schemas import RawEntryCreate

    raw = app.ingestion.ingest(RawEntryCreate(content="Entrada sintetica excluida"))
    app.db.execute("UPDATE raw_entries SET deleted_at = ? WHERE id = ?;", ("2026-01-01T00:00:00+00:00", raw.id))
    app.db.commit()
    assert app.entries_repo.list_retry_candidates() == []
    with pytest.raises(ValueError, match="No recoverable"):
        app.retry_raw_entry(raw.id)
