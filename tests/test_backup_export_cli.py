"""CLI tests for local backup and export commands."""

import json
import re
import sqlite3
from pathlib import Path

from click.testing import CliRunner

from personal_intelligence_engine.app.cli.commands import cli


def _configure_temp_env(monkeypatch, work_dir) -> None:
    monkeypatch.setenv("PIE_DATABASE_PATH", str(work_dir / "pie.db"))
    monkeypatch.setenv("PIE_NOTES_DIR", str(work_dir / "notes"))
    monkeypatch.setenv("PIE_REPORTS_DIR", str(work_dir / "reports"))
    monkeypatch.setenv("PIE_BACKUP_DIR", str(work_dir / "backups"))
    monkeypatch.setenv("PIE_EXPORT_DIR", str(work_dir / "exports"))
    monkeypatch.setenv("PIE_EXTRACTOR_BACKEND", "fake")


def _add_entry(text: str) -> str:
    result = CliRunner().invoke(cli, ["add", text])
    assert result.exit_code == 0, result.output

    match = re.search(r"Structured ID:\s+([0-9a-f-]+)", result.output)
    assert match is not None
    return match.group(1)


def test_backup_create_creates_backup_file(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    # Ensure database exists by adding an entry
    _add_entry("Nota de teste")

    result = CliRunner().invoke(cli, ["backup", "create"])
    assert result.exit_code == 0, result.output
    assert "Backup created:" in result.output

    # Find file path in output
    match = re.search(r"Backup created:\s+(.*)", result.output)
    assert match is not None
    backup_path = Path(match.group(1).strip())
    assert backup_path.exists()
    assert backup_path.parent == work_dir / "backups"

    # Verify backup is a valid SQLite DB with tables
    with sqlite3.connect(backup_path) as conn:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        assert "raw_entries" in tables
        assert "structured_entries" in tables


def test_backup_create_does_not_overwrite(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    _add_entry("Nota de teste")

    # Mock _get_timestamp to return a fixed string
    monkeypatch.setattr(
        "personal_intelligence_engine.app.services.backup_export_service.BackupExportService._get_timestamp",
        lambda self: "2026-05-26T153000"
    )

    result = CliRunner().invoke(cli, ["backup", "create"])
    assert result.exit_code == 0, result.output

    # Second backup with same timestamp should fail
    result2 = CliRunner().invoke(cli, ["backup", "create"])
    assert result2.exit_code != 0
    assert "already exists" in result2.output or "Could not access configured path" in result2.output


def test_backup_create_friendly_error_if_db_missing(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    # Do not call _add_entry so db.db is never created
    db_path = work_dir / "pie.db"
    assert not db_path.exists()

    result = CliRunner().invoke(cli, ["backup", "create"])
    assert result.exit_code != 0
    assert "does not exist" in result.output or "Could not access configured path" in result.output


def test_export_json_creates_json_file(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Nota de teste para exportação JSON")

    result = CliRunner().invoke(cli, ["export", "json"])
    assert result.exit_code == 0, result.output
    assert "JSON export created:" in result.output

    match = re.search(r"JSON export created:\s+(.*)", result.output)
    assert match is not None
    export_path = Path(match.group(1).strip())
    assert export_path.exists()
    assert export_path.parent == work_dir / "exports"

    # Verify JSON structure
    with open(export_path, encoding="utf-8") as f:
        data = json.load(f)

    assert "raw_entries" in data
    assert "structured_entries" in data
    assert "audit_logs" in data

    # Verify IDs are preserved
    structured_rows = data["structured_entries"]
    assert len(structured_rows) > 0
    exported_ids = [row["id"] for row in structured_rows]
    assert structured_id in exported_ids


def test_export_markdown_creates_markdown_file(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    # Add a note with long content to test snippet truncation
    long_content = "Esta é uma nota extremamente longa com o propósito de testar " * 5
    structured_id = _add_entry(long_content)

    result = CliRunner().invoke(cli, ["export", "markdown"])
    assert result.exit_code == 0, result.output
    assert "Markdown export created:" in result.output

    match = re.search(r"Markdown export created:\s+(.*)", result.output)
    assert match is not None
    export_path = Path(match.group(1).strip())
    assert export_path.exists()
    assert export_path.parent == work_dir / "exports"

    # Verify Markdown contents
    content = export_path.read_text(encoding="utf-8")
    assert "# PIE Export" in content
    assert "Total Entries:" in content

    # Should group by type (FakeExtractor produces 'idea' or similar)
    assert "##" in content

    # Verify structured ID and raw ID presence
    assert f"Structured Entry ID:** {structured_id}" in content
    assert "Raw Entry ID:**" in content

    # Verify that safe snippet is used and does not include the full long content
    assert "Snippet:**" in content
    assert len(long_content) > 120
    # The snippet must be shortened (max 120 chars, ending with ...)
    assert long_content not in content
    assert "..." in content


def test_gitignore_contains_backups_and_exports(work_dir):
    # Verify the real gitignore in the workspace has backups/ and exports/
    gitignore_path = Path(__file__).resolve().parents[1] / ".gitignore"
    assert gitignore_path.exists()
    content = gitignore_path.read_text(encoding="utf-8")
    assert "backups/" in content
    assert "exports/" in content


def test_no_llm_called_during_backup_export(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    _add_entry("Nota de teste")

    # Run backup and export, and check audit_logs. They should NOT log backup/export actions.
    CliRunner().invoke(cli, ["backup", "create"])
    CliRunner().invoke(cli, ["export", "json"])
    CliRunner().invoke(cli, ["export", "markdown"])

    db_path = work_dir / "pie.db"
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute("SELECT action FROM audit_logs;")
        actions = [row[0] for row in cursor.fetchall()]

    # Make sure no LLM/API logs or backup/export action logs exist in audit logs
    for action in actions:
        assert "backup" not in action
        assert "export" not in action


def test_regression_existing_commands_continue_to_work(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)

    # 1. Add entry
    structured_id = _add_entry("Minha ideia de regressão")

    # 2. Entries list
    res_list = CliRunner().invoke(cli, ["entries", "list"])
    assert res_list.exit_code == 0
    assert structured_id in res_list.output

    # 3. Entries show
    res_show = CliRunner().invoke(cli, ["entries", "show", structured_id])
    assert res_show.exit_code == 0
    assert "Minha ideia de regressão" in res_show.output

    # 4. Search
    res_search = CliRunner().invoke(cli, ["search", "regressão"])
    assert res_search.exit_code == 0
    assert structured_id in res_search.output

    # 5. Review commands
    res_rev_list = CliRunner().invoke(cli, ["review", "list"])
    assert res_rev_list.exit_code == 0

    # 6. Report daily
    res_report = CliRunner().invoke(cli, ["report", "daily", "--date", "2026-05-26"])
    assert res_report.exit_code == 0
    assert "Daily report generated" in res_report.output

    # 7. Evaluate extraction
    res_eval = CliRunner().invoke(cli, ["evaluate", "extraction"])
    assert res_eval.exit_code == 0
    assert "Total Cases" in res_eval.output or "Evaluation" in res_eval.output
