"""Tests for weekly and project reports, including CLI and regressions."""

import re
from datetime import datetime, timezone
from pathlib import Path

from click.testing import CliRunner

from personal_intelligence_engine.app.cli.commands import cli
from personal_intelligence_engine.app.domain.schemas import RawEntry, StructuredEntry
from personal_intelligence_engine.app.domain.types import EntryStatus, EntryType, ValidationStatus


def _configure_temp_env(monkeypatch, work_dir) -> None:
    monkeypatch.setenv("PIE_DATABASE_PATH", str(work_dir / "test.db"))
    monkeypatch.setenv("PIE_NOTES_DIR", str(work_dir / "notes"))
    monkeypatch.setenv("PIE_REPORTS_DIR", str(work_dir / "reports"))
    monkeypatch.setenv("PIE_BACKUP_DIR", str(work_dir / "backups"))
    monkeypatch.setenv("PIE_EXPORT_DIR", str(work_dir / "exports"))
    monkeypatch.setenv("PIE_EXTRACTOR_BACKEND", "fake")


def _add_entry_cli(text: str) -> str:
    """Add an entry via CLI and return the structured entry ID."""
    result = CliRunner().invoke(cli, ["add", text])
    assert result.exit_code == 0, result.output
    match = re.search(r"Structured ID:\s+([0-9a-f-]+)", result.output)
    assert match is not None
    return match.group(1)


def _insert_entry_at(
    app,
    *,
    raw_id: str,
    structured_id: str,
    created_at: str,
    entry_type: EntryType,
    summary: str,
    project: str | None = None,
    validation_status: ValidationStatus = ValidationStatus.VALID,
) -> None:
    """Helper to insert synthetic entries at a specific timestamp (in UTC)."""
    raw = RawEntry(
        id=raw_id,
        content=f"Synthetic raw content for {raw_id} with summary: {summary}. This is longer raw data.",
        source="test",
        status=EntryStatus.PROCESSED,
        created_at=created_at,
        updated_at=created_at,
        content_hash=f"{raw_id}".ljust(64, '0')[:64],
    )
    if validation_status == ValidationStatus.NEEDS_REVIEW:
        raw.status = EntryStatus.NEEDS_REVIEW

    app.entries_repo.insert_raw_entry(raw)
    app.entries_repo.insert_structured_entry(
        StructuredEntry(
            id=structured_id,
            raw_entry_id=raw_id,
            entry_type=entry_type,
            project=project,
            summary=summary,
            confidence=0.85,
            structured_json="{}",
            validation_status=validation_status,
            created_at=created_at,
            updated_at=created_at,
        )
    )


# Scenario 1: report weekly successfully generates a Markdown file.
def test_1_weekly_report_generates_markdown_file(monkeypatch, work_dir, app):
    _configure_temp_env(monkeypatch, work_dir)
    _insert_entry_at(
        app,
        raw_id="raw-1",
        structured_id="struct-1",
        created_at=datetime(2026, 5, 26, 12, 0, tzinfo=timezone.utc).isoformat(),
        entry_type=EntryType.DECISION,
        summary="Decidimos usar SQLite",
    )

    result = CliRunner().invoke(cli, ["report", "weekly", "--date", "2026-05-26"])
    assert result.exit_code == 0, result.output
    assert "[OK] Weekly report generated!" in result.output

    # Verify file exists
    match = re.search(r"File:\s+(.*)", result.output)
    assert match is not None
    report_file = Path(match.group(1).strip())
    assert report_file.exists()
    assert report_file.parent == work_dir / "reports"
    assert report_file.name == "weekly_2026-05-25_to_2026-05-31.md"


# Scenario 2: report weekly uses Monday-to-Sunday boundaries.
def test_2_weekly_report_monday_to_sunday_boundaries(app):
    # Week: Monday 2026-05-25 to Sunday 2026-05-31
    # Entry on previous Sunday (out of bounds)
    _insert_entry_at(
        app,
        raw_id="raw-prev-sun",
        structured_id="struct-prev-sun",
        created_at=datetime(2026, 5, 24, 23, 0, tzinfo=timezone.utc).isoformat(),  # 2026-05-24 20:00 local
        entry_type=EntryType.DECISION,
        summary="Previous Sunday Decision",
    )
    # Entry on Monday (in bounds)
    _insert_entry_at(
        app,
        raw_id="raw-mon",
        structured_id="struct-mon",
        created_at=datetime(2026, 5, 25, 12, 0, tzinfo=timezone.utc).isoformat(),
        entry_type=EntryType.DECISION,
        summary="Monday Decision",
    )
    # Entry on Sunday (in bounds)
    _insert_entry_at(
        app,
        raw_id="raw-sun",
        structured_id="struct-sun",
        created_at=datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc).isoformat(),
        entry_type=EntryType.DECISION,
        summary="Sunday Decision",
    )
    # Entry on next Monday (out of bounds)
    _insert_entry_at(
        app,
        raw_id="raw-next-mon",
        structured_id="struct-next-mon",
        created_at=datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc).isoformat(),
        entry_type=EntryType.DECISION,
        summary="Next Monday Decision",
    )

    report = app.generate_weekly_report("2026-05-27")  # Wednesday in that week
    assert report["date_start"] == "2026-05-25"
    assert report["date_end"] == "2026-05-31"

    content = Path(report["file_path"]).read_text(encoding="utf-8")
    assert "Monday Decision" in content
    assert "Sunday Decision" in content
    assert "Previous Sunday Decision" not in content
    assert "Next Monday Decision" not in content


# Scenario 3: report weekly converts timezone boundaries properly.
def test_3_weekly_report_timezone_boundaries(app):
    # America/Sao_Paulo is UTC-3.
    # Week: Mon 2026-05-25 to Sun 2026-05-31
    # Mon 2026-05-25 00:00:00 local = UTC 2026-05-25 03:00:00.
    # Sun 2026-05-31 23:59:59.999 local = UTC 2026-06-01 02:59:59.999.

    # Entry just before Monday start local: Sunday 23:59 local = Monday 02:59 UTC
    _insert_entry_at(
        app,
        raw_id="raw-just-before-start",
        structured_id="struct-just-before-start",
        created_at=datetime(2026, 5, 25, 2, 59, tzinfo=timezone.utc).isoformat(),
        entry_type=EntryType.DECISION,
        summary="Just before start (still previous week)",
    )
    # Entry exactly at Monday start local: Monday 00:00 local = Monday 03:00 UTC
    _insert_entry_at(
        app,
        raw_id="raw-exactly-start",
        structured_id="struct-exactly-start",
        created_at=datetime(2026, 5, 25, 3, 0, tzinfo=timezone.utc).isoformat(),
        entry_type=EntryType.DECISION,
        summary="Exactly at start",
    )
    # Entry exactly at Sunday end local: Sunday 23:59 local = Monday 02:59 UTC of next week
    _insert_entry_at(
        app,
        raw_id="raw-exactly-end",
        structured_id="struct-exactly-end",
        created_at=datetime(2026, 6, 1, 2, 59, tzinfo=timezone.utc).isoformat(),
        entry_type=EntryType.DECISION,
        summary="Exactly at end",
    )
    # Entry just after Sunday end local: Monday 00:00 local = Monday 03:00 UTC of next week
    _insert_entry_at(
        app,
        raw_id="raw-just-after-end",
        structured_id="struct-just-after-end",
        created_at=datetime(2026, 6, 1, 3, 0, tzinfo=timezone.utc).isoformat(),
        entry_type=EntryType.DECISION,
        summary="Just after end (next week)",
    )

    report = app.generate_weekly_report("2026-05-26")
    content = Path(report["file_path"]).read_text(encoding="utf-8")

    assert "Exactly at start" in content
    assert "Exactly at end" in content
    assert "Just before start" not in content
    assert "Just after end" not in content


# Scenario 4: report weekly output includes the total entries count.
def test_4_weekly_report_total_entries_count(monkeypatch, work_dir, app):
    _configure_temp_env(monkeypatch, work_dir)
    _insert_entry_at(
        app,
        raw_id="raw-1",
        structured_id="struct-1",
        created_at=datetime(2026, 5, 26, 12, 0, tzinfo=timezone.utc).isoformat(),
        entry_type=EntryType.DECISION,
        summary="Decidimos usar SQLite",
    )
    _insert_entry_at(
        app,
        raw_id="raw-2",
        structured_id="struct-2",
        created_at=datetime(2026, 5, 27, 12, 0, tzinfo=timezone.utc).isoformat(),
        entry_type=EntryType.PROBLEM,
        summary="O banco travou",
    )

    result = CliRunner().invoke(cli, ["report", "weekly", "--date", "2026-05-26"])
    assert result.exit_code == 0
    assert "Entries:      2" in result.output

    match = re.search(r"File:\s+(.*)", result.output)
    report_file = Path(match.group(1).strip())
    content = report_file.read_text(encoding="utf-8")
    assert "**Total entries:** 2" in content


# Scenario 5: report weekly output includes a summary count by type.
def test_5_weekly_report_summary_count_by_type(app):
    _insert_entry_at(
        app,
        raw_id="raw-1",
        structured_id="struct-1",
        created_at=datetime(2026, 5, 26, 12, 0, tzinfo=timezone.utc).isoformat(),
        entry_type=EntryType.DECISION,
        summary="Decision 1",
    )
    _insert_entry_at(
        app,
        raw_id="raw-2",
        structured_id="struct-2",
        created_at=datetime(2026, 5, 27, 12, 0, tzinfo=timezone.utc).isoformat(),
        entry_type=EntryType.PROBLEM,
        summary="Problem 1",
    )

    report = app.generate_weekly_report("2026-05-26")
    content = Path(report["file_path"]).read_text(encoding="utf-8")
    assert "## Summary by Type" in content
    assert "| decision | 1 |" in content
    assert "| problem | 1 |" in content


# Scenario 6: report weekly output contains raw entry and structured entry IDs.
def test_6_weekly_report_contains_raw_and_structured_ids(app):
    _insert_entry_at(
        app,
        raw_id="raw-uid-123",
        structured_id="struct-uid-456",
        created_at=datetime(2026, 5, 26, 12, 0, tzinfo=timezone.utc).isoformat(),
        entry_type=EntryType.DECISION,
        summary="Decision 1",
    )

    report = app.generate_weekly_report("2026-05-26")
    content = Path(report["file_path"]).read_text(encoding="utf-8")
    assert "Structured Entry ID: `struct-uid-456`" in content
    assert "Raw Entry ID: `raw-uid-123`" in content
    assert "- Structured Entry ID: `struct-uid-456`" in content
    assert "  Raw Entry ID: `raw-uid-123`" in content


# Scenario 7: report weekly includes needs_review counts and highlights needs_review entries.
def test_7_weekly_report_includes_needs_review_details(app):
    _insert_entry_at(
        app,
        raw_id="raw-valid",
        structured_id="struct-valid",
        created_at=datetime(2026, 5, 26, 12, 0, tzinfo=timezone.utc).isoformat(),
        entry_type=EntryType.DECISION,
        summary="Valid Decision",
        validation_status=ValidationStatus.VALID,
    )
    _insert_entry_at(
        app,
        raw_id="raw-review",
        structured_id="struct-review",
        created_at=datetime(2026, 5, 27, 12, 0, tzinfo=timezone.utc).isoformat(),
        entry_type=EntryType.DECISION,
        summary="Review Required Decision",
        validation_status=ValidationStatus.NEEDS_REVIEW,
    )

    report = app.generate_weekly_report("2026-05-26")
    content = Path(report["file_path"]).read_text(encoding="utf-8")
    assert "## Validation Status" in content
    assert "- **Approved/Valid entries:** 1" in content
    assert "- **Needs Review entries:** 1" in content
    assert "- **Status:** needs_review" in content


# Scenario 8: report weekly for empty weeks generates a clean report stating "No entries".
def test_8_weekly_report_empty_week(app):
    report = app.generate_weekly_report("2000-01-01")
    assert Path(report["file_path"]).exists()
    content = Path(report["file_path"]).read_text(encoding="utf-8")
    assert "No entries recorded for this week." in content


# Scenario 9: report weekly with invalid date syntax returns a friendly error.
def test_9_weekly_report_invalid_date(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    result = CliRunner().invoke(cli, ["report", "weekly", "--date", "invalid-date"])
    assert result.exit_code != 0
    assert "Invalid date. Use YYYY-MM-DD." in result.output
    assert "Traceback" not in result.output


# Scenario 10: report project generates a Markdown file.
def test_10_project_report_generates_markdown_file(monkeypatch, work_dir, app):
    _configure_temp_env(monkeypatch, work_dir)
    _insert_entry_at(
        app,
        raw_id="raw-1",
        structured_id="struct-1",
        created_at=datetime(2026, 5, 26, 12, 0, tzinfo=timezone.utc).isoformat(),
        entry_type=EntryType.DECISION,
        summary="Decidimos usar SQLite",
        project="PIE",
    )

    result = CliRunner().invoke(cli, ["report", "project", "--project", "PIE"])
    assert result.exit_code == 0, result.output
    assert "[OK] Project report generated!" in result.output

    match = re.search(r"File:\s+(.*)", result.output)
    assert match is not None
    report_file = Path(match.group(1).strip())
    assert report_file.exists()
    assert report_file.parent == work_dir / "reports"
    assert report_file.name == "project_PIE.md"


# Scenario 11: report project filters structured entries correctly by project name.
def test_11_project_report_filtering(app):
    _insert_entry_at(
        app,
        raw_id="raw-pie",
        structured_id="struct-pie",
        created_at=datetime(2026, 5, 26, 12, 0, tzinfo=timezone.utc).isoformat(),
        entry_type=EntryType.DECISION,
        summary="PIE Decision",
        project="PIE",
    )
    _insert_entry_at(
        app,
        raw_id="raw-other",
        structured_id="struct-other",
        created_at=datetime(2026, 5, 26, 12, 0, tzinfo=timezone.utc).isoformat(),
        entry_type=EntryType.DECISION,
        summary="Other Decision",
        project="OtherProject",
    )

    report = app.generate_project_report("PIE")
    content = Path(report["file_path"]).read_text(encoding="utf-8")
    assert "PIE Decision" in content
    assert "Other Decision" not in content


# Scenario 12: report project renders sections for decisions, problems, candidate tasks, and insights when present.
def test_12_project_report_sections(app):
    _insert_entry_at(
        app,
        raw_id="raw-dec",
        structured_id="struct-dec",
        created_at=datetime(2026, 5, 26, 12, 0, tzinfo=timezone.utc).isoformat(),
        entry_type=EntryType.DECISION,
        summary="Decision Summary",
        project="PIE",
    )
    _insert_entry_at(
        app,
        raw_id="raw-prob",
        structured_id="struct-prob",
        created_at=datetime(2026, 5, 26, 12, 0, tzinfo=timezone.utc).isoformat(),
        entry_type=EntryType.PROBLEM,
        summary="Problem Summary",
        project="PIE",
    )
    _insert_entry_at(
        app,
        raw_id="raw-task",
        structured_id="struct-task",
        created_at=datetime(2026, 5, 26, 12, 0, tzinfo=timezone.utc).isoformat(),
        entry_type=EntryType.CANDIDATE_TASK,
        summary="Task Summary",
        project="PIE",
    )
    _insert_entry_at(
        app,
        raw_id="raw-ins",
        structured_id="struct-ins",
        created_at=datetime(2026, 5, 26, 12, 0, tzinfo=timezone.utc).isoformat(),
        entry_type=EntryType.INSIGHT,
        summary="Insight Summary",
        project="PIE",
    )

    report = app.generate_project_report("PIE")
    content = Path(report["file_path"]).read_text(encoding="utf-8")
    assert "## Decisions" in content
    assert "Decision Summary" in content
    assert "## Problems" in content
    assert "Problem Summary" in content
    assert "## Candidate Tasks" in content
    assert "Task Summary" in content
    assert "## Insights" in content
    assert "Insight Summary" in content


# Scenario 13: report project includes source IDs.
def test_13_project_report_source_ids(app):
    _insert_entry_at(
        app,
        raw_id="raw-proj-id",
        structured_id="struct-proj-id",
        created_at=datetime(2026, 5, 26, 12, 0, tzinfo=timezone.utc).isoformat(),
        entry_type=EntryType.DECISION,
        summary="Decision Summary",
        project="PIE",
    )

    report = app.generate_project_report("PIE")
    content = Path(report["file_path"]).read_text(encoding="utf-8")
    assert "Structured Entry ID: `struct-proj-id`" in content
    assert "Raw Entry ID: `raw-proj-id`" in content


# Scenario 14: report project with no entries returns a friendly message.
def test_14_project_report_empty(app):
    report = app.generate_project_report("EmptyProject")
    assert Path(report["file_path"]).exists()
    content = Path(report["file_path"]).read_text(encoding="utf-8")
    assert "No entries recorded for this project." in content


# Scenario 15: report project with empty name returns an error.
def test_15_project_report_empty_name(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    result = CliRunner().invoke(cli, ["report", "project", "--project", ""])
    assert result.exit_code != 0
    assert "Project name cannot be empty." in result.output
    assert "Traceback" not in result.output

    # Spaces only
    result2 = CliRunner().invoke(cli, ["report", "project", "--project", "   "])
    assert result2.exit_code != 0
    assert "Project name cannot be empty." in result2.output


# Scenario 16: Verify that reports/ folder is ignored by git.
def test_16_git_ignores_reports():
    gitignore_path = Path(__file__).resolve().parents[1] / ".gitignore"
    assert gitignore_path.exists()
    content = gitignore_path.read_text(encoding="utf-8")
    lines = [line.strip() for line in content.splitlines()]
    assert "reports/" in lines


# Scenario 17: Verify that reports only output summaries and snippets, not full raw contents.
def test_17_reports_do_not_leak_raw_content(app):
    _insert_entry_at(
        app,
        raw_id="raw-leak",
        structured_id="struct-leak",
        created_at=datetime(2026, 5, 26, 12, 0, tzinfo=timezone.utc).isoformat(),
        entry_type=EntryType.DECISION,
        summary="A compact summary of the decision",
        project="PIE",
    )

    report_weekly = app.generate_weekly_report("2026-05-26")
    content_weekly = Path(report_weekly["file_path"]).read_text(encoding="utf-8")
    assert "This is longer raw data." not in content_weekly
    assert "A compact summary of the decision" in content_weekly

    report_project = app.generate_project_report("PIE")
    content_project = Path(report_project["file_path"]).read_text(encoding="utf-8")
    assert "This is longer raw data." not in content_project
    assert "A compact summary of the decision" in content_project


# Scenario 18: Regression: daily report continues to work.
def test_18_regression_daily_report(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    _add_entry_cli("Eu decidi usar Pydantic")

    result = CliRunner().invoke(cli, ["report", "daily", "--date", "2026-05-26"])
    assert result.exit_code == 0, result.output
    assert "Daily report generated" in result.output


# Scenario 19: Regression: entries list, show, and search continue to work.
def test_19_regression_entries_commands(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    sid = _add_entry_cli("Eu decidi usar SQLite")

    # list
    list_res = CliRunner().invoke(cli, ["entries", "list"])
    assert list_res.exit_code == 0
    assert sid in list_res.output

    # show
    show_res = CliRunner().invoke(cli, ["entries", "show", sid])
    assert show_res.exit_code == 0
    assert "SQLite" in show_res.output

    # search
    search_res = CliRunner().invoke(cli, ["search", "SQLite"])
    assert search_res.exit_code == 0
    assert sid in search_res.output


# Scenario 20: Regression: review commands work.
def test_20_regression_review_commands(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    # entry with low confidence goes to review (fake entry with general text is usually low confidence)
    sid = _add_entry_cli("Nota generica sem palavras-chave")

    list_res = CliRunner().invoke(cli, ["review", "list"])
    assert list_res.exit_code == 0
    assert sid in list_res.output

    show_res = CliRunner().invoke(cli, ["review", "show", sid])
    assert show_res.exit_code == 0

    approve_res = CliRunner().invoke(cli, ["review", "approve", sid])
    assert approve_res.exit_code == 0
    assert "approved" in approve_res.output.lower()


# Scenario 21: Regression: backup and export work.
def test_21_regression_backup_export_commands(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    _add_entry_cli("Nota para backup e exportacao")

    # backup
    backup_res = CliRunner().invoke(cli, ["backup", "create"])
    assert backup_res.exit_code == 0
    assert "Backup created:" in backup_res.output

    # export json
    export_json_res = CliRunner().invoke(cli, ["export", "json"])
    assert export_json_res.exit_code == 0
    assert "JSON export created:" in export_json_res.output

    # export markdown
    export_md_res = CliRunner().invoke(cli, ["export", "markdown"])
    assert export_md_res.exit_code == 0
    assert "Markdown export created:" in export_md_res.output


# Scenario 22: Regression: entries reprocess works.
def test_22_regression_reprocess_command(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    sid = _add_entry_cli("Nota generica")

    # reprocess --dry-run
    reprocess_res = CliRunner().invoke(cli, ["entries", "reprocess", sid, "--dry-run"])
    assert reprocess_res.exit_code == 0
    assert "Structured Entry ID:" in reprocess_res.output
