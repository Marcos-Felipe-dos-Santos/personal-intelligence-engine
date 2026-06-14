"""Tests for report decisions and report tasks CLI commands."""

from datetime import datetime, timezone
from pathlib import Path

from click.testing import CliRunner

from personal_intelligence_engine.app.cli.commands import cli
from personal_intelligence_engine.app.domain.schemas import RawEntry, StructuredEntry
from personal_intelligence_engine.app.domain.types import EntryStatus, EntryType, ValidationStatus

_NOW = datetime(2026, 6, 14, 10, 0, tzinfo=timezone.utc).isoformat()


def _configure_temp_env(monkeypatch, work_dir) -> None:
    monkeypatch.setenv("PIE_DATABASE_PATH", str(work_dir / "test.db"))
    monkeypatch.setenv("PIE_NOTES_DIR", str(work_dir / "notes"))
    monkeypatch.setenv("PIE_REPORTS_DIR", str(work_dir / "reports"))
    monkeypatch.setenv("PIE_BACKUP_DIR", str(work_dir / "backups"))
    monkeypatch.setenv("PIE_EXPORT_DIR", str(work_dir / "exports"))
    monkeypatch.setenv("PIE_EXTRACTOR_BACKEND", "fake")


def _insert(
    app,
    *,
    raw_id: str,
    structured_id: str,
    entry_type: EntryType,
    summary: str,
    project: str | None = None,
    validation_status: ValidationStatus = ValidationStatus.VALID,
    created_at: str = _NOW,
) -> None:
    raw = RawEntry(
        id=raw_id,
        content=f"Raw content for {raw_id}",
        source="test",
        status=EntryStatus.PROCESSED,
        created_at=created_at,
        updated_at=created_at,
        content_hash=f"{raw_id}".ljust(64, "0")[:64],
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


def test_report_decisions_filters_by_type(monkeypatch, work_dir, app):
    """report decisions includes only decision entries, not tasks or other types."""
    _configure_temp_env(monkeypatch, work_dir)

    _insert(app, raw_id="r1", structured_id="s1", entry_type=EntryType.DECISION, summary="Decision A")
    _insert(app, raw_id="r2", structured_id="s2", entry_type=EntryType.DECISION, summary="Decision B")
    _insert(app, raw_id="r3", structured_id="s3", entry_type=EntryType.CANDIDATE_TASK, summary="Task X")

    result = CliRunner().invoke(cli, ["report", "decisions"])

    assert result.exit_code == 0, result.output
    assert "Decisions report generated" in result.output
    assert "Entries:      2" in result.output

    report_file = Path(work_dir / "reports" / "decisions_all.md")
    assert report_file.exists()
    content = report_file.read_text()
    assert "Decision A" in content
    assert "Decision B" in content
    assert "Task X" not in content


def test_report_decisions_by_project(monkeypatch, work_dir, app):
    """report decisions --project returns only decisions for that project."""
    _configure_temp_env(monkeypatch, work_dir)

    _insert(app, raw_id="r1", structured_id="s1", entry_type=EntryType.DECISION, summary="PIE Decision", project="PIE")
    _insert(app, raw_id="r2", structured_id="s2", entry_type=EntryType.DECISION, summary="Other Decision", project="OTHER")

    result = CliRunner().invoke(cli, ["report", "decisions", "--project", "PIE"])

    assert result.exit_code == 0, result.output
    assert "Entries:      1" in result.output

    report_file = Path(work_dir / "reports" / "decisions_PIE.md")
    assert report_file.exists()
    content = report_file.read_text()
    assert "PIE Decision" in content
    assert "Other Decision" not in content


def test_report_tasks_filters_pending(monkeypatch, work_dir, app):
    """report tasks includes valid and needs_review tasks but not invalid ones."""
    _configure_temp_env(monkeypatch, work_dir)

    _insert(app, raw_id="r1", structured_id="s1", entry_type=EntryType.CANDIDATE_TASK,
            summary="Valid Task", validation_status=ValidationStatus.VALID)
    _insert(app, raw_id="r2", structured_id="s2", entry_type=EntryType.CANDIDATE_TASK,
            summary="Needs Review Task", validation_status=ValidationStatus.NEEDS_REVIEW)
    _insert(app, raw_id="r3", structured_id="s3", entry_type=EntryType.CANDIDATE_TASK,
            summary="Invalid Task", validation_status=ValidationStatus.INVALID)

    result = CliRunner().invoke(cli, ["report", "tasks"])

    assert result.exit_code == 0, result.output
    assert "Entries:      2" in result.output

    report_file = Path(work_dir / "reports" / "tasks_pending.md")
    content = report_file.read_text()
    assert "Valid Task" in content
    assert "Needs Review Task" in content
    assert "Invalid Task" not in content


def test_report_tasks_markdown_generated(monkeypatch, work_dir, app):
    """report tasks generates a correctly formatted Markdown file."""
    _configure_temp_env(monkeypatch, work_dir)

    _insert(app, raw_id="r1", structured_id="s1", entry_type=EntryType.CANDIDATE_TASK,
            summary="Build the thing", project="PIE", validation_status=ValidationStatus.VALID)

    result = CliRunner().invoke(cli, ["report", "tasks"])

    assert result.exit_code == 0, result.output

    report_file = Path(work_dir / "reports" / "tasks_pending.md")
    assert report_file.exists()
    content = report_file.read_text()

    assert "# Pending Tasks Report" in content
    assert "**Total pending:** 1" in content
    assert "s1" in content
    assert "Build the thing" in content
    assert "PIE" in content


def test_report_tasks_excludes_soft_deleted(monkeypatch, work_dir, app):
    """report tasks does not include soft-deleted task entries."""
    _configure_temp_env(monkeypatch, work_dir)

    _insert(app, raw_id="r1", structured_id="s1", entry_type=EntryType.CANDIDATE_TASK,
            summary="Active Task", validation_status=ValidationStatus.VALID)
    _insert(app, raw_id="r2", structured_id="s2", entry_type=EntryType.CANDIDATE_TASK,
            summary="Deleted Task", validation_status=ValidationStatus.VALID)

    app.delete_entry("s2")

    result = CliRunner().invoke(cli, ["report", "tasks"])

    assert result.exit_code == 0, result.output
    assert "Entries:      1" in result.output

    content = Path(work_dir / "reports" / "tasks_pending.md").read_text()
    assert "Active Task" in content
    assert "Deleted Task" not in content


def test_report_decisions_since_filter(monkeypatch, work_dir, app):
    """report decisions --since excludes decisions created before the given date."""
    _configure_temp_env(monkeypatch, work_dir)

    _insert(app, raw_id="r1", structured_id="s1", entry_type=EntryType.DECISION,
            summary="Old Decision", created_at="2026-01-01T00:00:00+00:00")
    _insert(app, raw_id="r2", structured_id="s2", entry_type=EntryType.DECISION,
            summary="Recent Decision", created_at="2026-06-01T00:00:00+00:00")

    result = CliRunner().invoke(cli, ["report", "decisions", "--since", "2026-06-01"])

    assert result.exit_code == 0, result.output
    assert "Entries:      1" in result.output

    content = Path(work_dir / "reports" / "decisions_all.md").read_text()
    assert "Recent Decision" in content
    assert "Old Decision" not in content


def test_report_tasks_by_project(monkeypatch, work_dir, app):
    """report tasks --project returns only tasks for that project."""
    _configure_temp_env(monkeypatch, work_dir)

    _insert(app, raw_id="r1", structured_id="s1", entry_type=EntryType.CANDIDATE_TASK,
            summary="PIE Task", project="PIE", validation_status=ValidationStatus.VALID)
    _insert(app, raw_id="r2", structured_id="s2", entry_type=EntryType.CANDIDATE_TASK,
            summary="Other Task", project="OTHER", validation_status=ValidationStatus.VALID)

    result = CliRunner().invoke(cli, ["report", "tasks", "--project", "PIE"])

    assert result.exit_code == 0, result.output
    assert "Entries:      1" in result.output

    report_file = Path(work_dir / "reports" / "tasks_pending_PIE.md")
    assert report_file.exists()
    content = report_file.read_text()
    assert "PIE Task" in content
    assert "Other Task" not in content


def test_report_decisions_empty_database(monkeypatch, work_dir, app):
    """report decisions on an empty database generates a valid file with the empty message."""
    _configure_temp_env(monkeypatch, work_dir)

    result = CliRunner().invoke(cli, ["report", "decisions"])

    assert result.exit_code == 0, result.output
    content = Path(work_dir / "reports" / "decisions_all.md").read_text()
    assert "No decisions found" in content


def test_report_tasks_empty_database(monkeypatch, work_dir, app):
    """report tasks on an empty database generates a valid file with the empty message."""
    _configure_temp_env(monkeypatch, work_dir)

    result = CliRunner().invoke(cli, ["report", "tasks"])

    assert result.exit_code == 0, result.output
    content = Path(work_dir / "reports" / "tasks_pending.md").read_text()
    assert "No pending tasks found" in content
