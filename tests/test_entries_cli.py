"""CLI tests for entries list/show and search commands."""

import os
import re
import sqlite3

from click.testing import CliRunner

from personal_intelligence_engine.app.cli.commands import cli


def _configure_temp_env(monkeypatch, work_dir) -> None:
    monkeypatch.setenv("PIE_DATABASE_PATH", str(work_dir / "pie.db"))
    monkeypatch.setenv("PIE_NOTES_DIR", str(work_dir / "notes"))
    monkeypatch.setenv("PIE_REPORTS_DIR", str(work_dir / "reports"))
    monkeypatch.setenv("PIE_EXTRACTOR_BACKEND", "fake")


def _add_entry(text: str, auto_approve: bool = False) -> str:
    """Add an entry and return the structured entry ID."""
    args = ["add", text]
    if auto_approve:
        args.append("--auto-approve")
    result = CliRunner().invoke(cli, args)
    assert result.exit_code == 0, result.output
    match = re.search(r"Structured ID:\s+([0-9a-f-]+)", result.output)
    assert match is not None
    return match.group(1)


# -----------------------------------------------------------------------
# 1. entries list shows existing entries
# -----------------------------------------------------------------------

def test_entries_list_shows_existing_entries(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    sid = _add_entry("Eu decidi usar SQLite no projeto sintetico")

    result = CliRunner().invoke(cli, ["entries", "list"])

    assert result.exit_code == 0
    assert sid in result.output
    assert "decision" in result.output
    assert "Entries (" in result.output


# -----------------------------------------------------------------------
# 2. entries list filters by type
# -----------------------------------------------------------------------

def test_entries_list_filters_by_type(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    decision_id = _add_entry("Eu decidi usar SQLite no projeto sintetico")
    _add_entry("Tive uma ideia para melhorar o pipeline")

    result = CliRunner().invoke(cli, ["entries", "list", "--type", "decision"])

    assert result.exit_code == 0
    assert decision_id in result.output
    assert "idea" not in result.output


# -----------------------------------------------------------------------
# 3. entries list filters by project
# -----------------------------------------------------------------------

def test_entries_list_filters_by_project(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    # FakeExtractor does not set project, so filtering by project returns nothing
    _add_entry("Eu decidi usar SQLite no projeto sintetico")

    result = CliRunner().invoke(cli, ["entries", "list", "--project", "NonExistentProject"])

    assert result.exit_code == 0
    assert "No entries found." in result.output


# -----------------------------------------------------------------------
# 4. entries list filters by validation_status
# -----------------------------------------------------------------------

def test_entries_list_filters_by_validation_status(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    # "decidi" => decision, confidence 0.60 => needs_review (unless auto-approved)
    valid_id = _add_entry("Eu decidi usar SQLite no projeto sintetico", auto_approve=True)
    # fallback => general_note, confidence 0.30 => needs_review
    review_id = _add_entry("Nota sintetica sem projeto claro")

    result_valid = CliRunner().invoke(cli, ["entries", "list", "--status", "valid"])
    result_review = CliRunner().invoke(cli, ["entries", "list", "--status", "needs_review"])

    assert result_valid.exit_code == 0
    assert valid_id in result_valid.output
    assert review_id not in result_valid.output

    assert result_review.exit_code == 0
    assert review_id in result_review.output
    assert valid_id not in result_review.output


# -----------------------------------------------------------------------
# 5. entries list respects limit
# -----------------------------------------------------------------------

def test_entries_list_respects_limit(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    _add_entry("Eu decidi usar SQLite no projeto sintetico")
    _add_entry("Tive uma ideia para melhorar o pipeline")
    _add_entry("Nota sintetica sem projeto claro")

    result = CliRunner().invoke(cli, ["entries", "list", "--limit", "1"])

    assert result.exit_code == 0
    assert "Entries (1):" in result.output


# -----------------------------------------------------------------------
# 6. entries list empty shows friendly message
# -----------------------------------------------------------------------

def test_entries_list_empty_shows_friendly_message(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)

    result = CliRunner().invoke(cli, ["entries", "list"])

    assert result.exit_code == 0
    assert "No entries found." in result.output


# -----------------------------------------------------------------------
# 7. entries show shows full detail
# -----------------------------------------------------------------------

def test_entries_show_displays_entry_details(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    sid = _add_entry("Eu decidi usar SQLite no projeto sintetico")

    result = CliRunner().invoke(cli, ["entries", "show", sid])

    assert result.exit_code == 0
    assert f"Structured Entry ID: {sid}" in result.output
    assert "Raw Entry ID:" in result.output
    assert "Type:" in result.output
    assert "decision" in result.output
    assert "Summary:" in result.output
    assert "Confidence:" in result.output
    assert "60%" in result.output
    assert "Tags:" in result.output
    assert "Validation Status:" in result.output
    assert "Created At:" in result.output
    assert "Updated At:" in result.output
    assert "Raw Content:" in result.output
    assert "Structured JSON:" in result.output


# -----------------------------------------------------------------------
# 8. entries show missing ID returns friendly error
# -----------------------------------------------------------------------

def test_entries_show_missing_id_returns_friendly_error(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)

    result = CliRunner().invoke(cli, ["entries", "show", "missing-id"])

    assert result.exit_code != 0
    assert "No entry found for structured entry ID 'missing-id'" in result.output
    assert "Traceback" not in result.output


# -----------------------------------------------------------------------
# 9. entries show truncates long raw content
# -----------------------------------------------------------------------

def test_entries_show_truncates_long_raw_content(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    long_text = "Eu decidi " + "palavra " * 200
    sid = _add_entry(long_text)

    result = CliRunner().invoke(cli, ["entries", "show", sid])

    assert result.exit_code == 0
    # The raw content line should be truncated (not contain the full text)
    assert "Raw Content:" in result.output
    # Full text is ~1600+ chars, snippet limit is 500
    assert long_text not in result.output
    assert "..." in result.output


# -----------------------------------------------------------------------
# 10. search finds term in raw content
# -----------------------------------------------------------------------

def test_search_finds_term_in_raw_content(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    sid = _add_entry("Eu decidi usar SQLite no projeto sintetico")

    result = CliRunner().invoke(cli, ["search", "SQLite"])

    assert result.exit_code == 0
    assert sid in result.output
    assert "Search results" in result.output


# -----------------------------------------------------------------------
# 11. search finds term in summary
# -----------------------------------------------------------------------

def test_search_finds_term_in_summary(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    # FakeExtractor summary = truncated version of content
    sid = _add_entry("Eu decidi usar SQLite no projeto sintetico")

    # The summary will contain "decidi" since it's from the content
    result = CliRunner().invoke(cli, ["search", "decidi"])

    assert result.exit_code == 0
    assert sid in result.output


# -----------------------------------------------------------------------
# 12. search finds term in project
# -----------------------------------------------------------------------

def test_search_finds_term_in_project(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    # FakeExtractor does not set project, so searching by project yields no results
    _add_entry("Eu decidi usar SQLite no projeto sintetico")

    result = CliRunner().invoke(cli, ["search", "NonExistentProjectName"])

    assert result.exit_code == 0
    assert "No search results found." in result.output


# -----------------------------------------------------------------------
# 13. search finds term in structured_json/tags
# -----------------------------------------------------------------------

def test_search_finds_term_in_structured_json_tags(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    # "decidi" => decision, tags include "decision"
    sid = _add_entry("Eu decidi usar SQLite no projeto sintetico")

    # Search for "decision" which appears in structured_json tags
    result = CliRunner().invoke(cli, ["search", "decision"])

    assert result.exit_code == 0
    assert sid in result.output


# -----------------------------------------------------------------------
# 14. search filters by type
# -----------------------------------------------------------------------

def test_search_filters_by_type(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    decision_id = _add_entry("Eu decidi usar SQLite no projeto sintetico")
    idea_id = _add_entry("Tive uma ideia para melhorar o pipeline sintetico")

    # Both contain "sintetico", but filter by decision
    result = CliRunner().invoke(cli, ["search", "sintetico", "--type", "decision"])

    assert result.exit_code == 0
    assert decision_id in result.output
    assert idea_id not in result.output


# -----------------------------------------------------------------------
# 15. search filters by project
# -----------------------------------------------------------------------

def test_search_filters_by_project(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    _add_entry("Eu decidi usar SQLite no projeto sintetico")

    # FakeExtractor does not set project; filtering by project returns nothing
    result = CliRunner().invoke(cli, ["search", "SQLite", "--project", "NonExistent"])

    assert result.exit_code == 0
    assert "No search results found." in result.output


# -----------------------------------------------------------------------
# 16. search filters by validation_status
# -----------------------------------------------------------------------

def test_search_filters_by_validation_status(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    valid_id = _add_entry("Eu decidi usar SQLite no projeto sintetico", auto_approve=True)
    review_id = _add_entry("Nota sintetica sem projeto claro")

    result_valid = CliRunner().invoke(cli, ["search", "sintetico", "--status", "valid"])
    result_review = CliRunner().invoke(cli, ["search", "sintetica", "--status", "needs_review"])

    assert result_valid.exit_code == 0
    assert valid_id in result_valid.output
    assert review_id not in result_valid.output

    assert result_review.exit_code == 0
    assert review_id in result_review.output
    assert valid_id not in result_review.output


# -----------------------------------------------------------------------
# 17. search no results shows friendly message
# -----------------------------------------------------------------------

def test_search_no_results_shows_friendly_message(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    _add_entry("Eu decidi usar SQLite no projeto sintetico")

    result = CliRunner().invoke(cli, ["search", "TermoQueNaoExisteEmNenhumaEntrada"])

    assert result.exit_code == 0
    assert "No search results found." in result.output


# -----------------------------------------------------------------------
# 18. search does not create extra database files
# -----------------------------------------------------------------------

def test_search_does_not_create_extra_database(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    _add_entry("Eu decidi usar SQLite no projeto sintetico")

    db_files_before = [f for f in os.listdir(work_dir) if f.endswith(".db")]

    CliRunner().invoke(cli, ["search", "SQLite"])

    db_files_after = [f for f in os.listdir(work_dir) if f.endswith(".db")]
    assert db_files_before == db_files_after


# -----------------------------------------------------------------------
# 19. search is read-only
# -----------------------------------------------------------------------

def test_search_does_not_create_audit_log_or_files(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    _add_entry("Eu decidi usar SQLite no projeto sintetico")
    notes_before = sorted(os.listdir(work_dir / "notes"))
    reports_before = sorted(os.listdir(work_dir / "reports"))
    with sqlite3.connect(work_dir / "pie.db") as connection:
        audit_count_before = connection.execute("SELECT COUNT(*) FROM audit_logs;").fetchone()[0]

    result = CliRunner().invoke(cli, ["search", "SQLite"])

    assert result.exit_code == 0
    with sqlite3.connect(work_dir / "pie.db") as connection:
        audit_count_after = connection.execute("SELECT COUNT(*) FROM audit_logs;").fetchone()[0]
    assert audit_count_after == audit_count_before
    assert sorted(os.listdir(work_dir / "notes")) == notes_before
    assert sorted(os.listdir(work_dir / "reports")) == reports_before


# -----------------------------------------------------------------------
# 20. review commands still work
# -----------------------------------------------------------------------

def test_review_commands_still_work(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    sid = _add_entry("Nota sintetica sem projeto claro")

    list_result = CliRunner().invoke(cli, ["review", "list"])
    show_result = CliRunner().invoke(cli, ["review", "show", sid])
    approve_result = CliRunner().invoke(cli, ["review", "approve", sid])

    assert list_result.exit_code == 0
    assert sid in list_result.output
    assert show_result.exit_code == 0
    assert approve_result.exit_code == 0
    assert "Review entry approved" in approve_result.output


# -----------------------------------------------------------------------
# 21. pie add still works
# -----------------------------------------------------------------------

def test_add_still_works(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)

    result = CliRunner().invoke(cli, ["add", "Eu decidi testar a regressao sintetica"])

    assert result.exit_code == 0
    assert "Entry created successfully" in result.output


# -----------------------------------------------------------------------
# 22. pie report daily still works
# -----------------------------------------------------------------------

def test_report_daily_still_works(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    _add_entry("Eu decidi testar o relatorio sintetico")

    result = CliRunner().invoke(cli, ["report", "daily", "--date", "2026-05-26"])

    assert result.exit_code == 0
    assert "Daily report generated" in result.output
