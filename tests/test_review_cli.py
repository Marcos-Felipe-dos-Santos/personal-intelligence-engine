"""CLI tests for read-only human review commands."""

import re
import sqlite3

from click.testing import CliRunner

from personal_intelligence_engine.app.cli.commands import cli


def _configure_temp_env(monkeypatch, work_dir) -> None:
    monkeypatch.setenv("PIE_DATABASE_PATH", str(work_dir / "pie.db"))
    monkeypatch.setenv("PIE_NOTES_DIR", str(work_dir / "notes"))
    monkeypatch.setenv("PIE_REPORTS_DIR", str(work_dir / "reports"))
    monkeypatch.setenv("PIE_EXTRACTOR_BACKEND", "fake")


def _add_entry(text: str) -> str:
    result = CliRunner().invoke(cli, ["add", text])
    assert result.exit_code == 0, result.output

    match = re.search(r"Structured ID:\s+([0-9a-f-]+)", result.output)
    assert match is not None
    return match.group(1)


def _fetch_counts(database_path) -> tuple[int, int, int]:
    with sqlite3.connect(database_path) as connection:
        raw_count = connection.execute("SELECT COUNT(*) FROM raw_entries;").fetchone()[0]
        structured_count = connection.execute("SELECT COUNT(*) FROM structured_entries;").fetchone()[0]
        audit_count = connection.execute("SELECT COUNT(*) FROM audit_logs;").fetchone()[0]
    return raw_count, structured_count, audit_count


def test_review_list_shows_needs_review_entry(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Nota sintetica sem projeto claro")

    result = CliRunner().invoke(cli, ["review", "list"])

    assert result.exit_code == 0
    assert "Entries needing review" in result.output
    assert structured_id in result.output
    assert "general_note" in result.output
    assert "50%" in result.output
    assert "Nota sintetica sem projeto claro" in result.output


def test_review_list_does_not_show_processed_entry(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    processed_id = _add_entry("Eu decidi usar SQLite no projeto sintetico")
    needs_review_id = _add_entry("Nota sintetica sem projeto claro")

    result = CliRunner().invoke(cli, ["review", "list"])

    assert result.exit_code == 0
    assert needs_review_id in result.output
    assert processed_id not in result.output


def test_review_list_without_results_shows_friendly_message(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    _add_entry("Eu decidi usar SQLite no projeto sintetico")

    result = CliRunner().invoke(cli, ["review", "list"])

    assert result.exit_code == 0
    assert "No entries need review" in result.output


def test_review_show_displays_entry_details(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Nota sintetica sem projeto claro")

    result = CliRunner().invoke(cli, ["review", "show", structured_id])

    assert result.exit_code == 0
    assert f"Structured Entry ID: {structured_id}" in result.output
    assert "Raw Entry ID:" in result.output
    assert "Type:" in result.output
    assert "general_note" in result.output
    assert "Project:" in result.output
    assert "Summary:" in result.output
    assert "Confidence:" in result.output
    assert "50%" in result.output
    assert "Tags:" in result.output
    assert "unclassified" in result.output
    assert "Validation Status:" in result.output
    assert "needs_review" in result.output
    assert "Raw Content:" in result.output
    assert "Nota sintetica sem projeto claro" in result.output
    assert "Created At:" in result.output


def test_review_show_missing_id_returns_friendly_error(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)

    result = CliRunner().invoke(cli, ["review", "show", "missing-id"])

    assert result.exit_code != 0
    assert "No review entry found for structured entry ID 'missing-id'" in result.output
    assert "Traceback" not in result.output


def test_review_commands_do_not_modify_database(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Nota sintetica sem projeto claro")
    before_list = _fetch_counts(work_dir / "pie.db")

    list_result = CliRunner().invoke(cli, ["review", "list"])
    show_result = CliRunner().invoke(cli, ["review", "show", structured_id])

    assert list_result.exit_code == 0
    assert show_result.exit_code == 0
    assert _fetch_counts(work_dir / "pie.db") == before_list
