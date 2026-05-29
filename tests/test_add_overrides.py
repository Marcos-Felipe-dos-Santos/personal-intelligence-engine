"""Tests for pie add metadata override flags (--project, --type, --tag).

Validates that user-provided overrides are applied correctly to the
extraction result without altering raw content, audit logs, or
the validation/confidence pipeline.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from click.testing import CliRunner

from personal_intelligence_engine.app.cli.commands import cli
from personal_intelligence_engine.app.domain.types import EntryType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _configure_env(monkeypatch, work_dir: Path) -> None:
    """Isolate all PIE directories in a temp tree."""
    monkeypatch.setenv("PIE_DATABASE_PATH", str(work_dir / "pie.db"))
    monkeypatch.setenv("PIE_NOTES_DIR", str(work_dir / "notes"))
    monkeypatch.setenv("PIE_REPORTS_DIR", str(work_dir / "reports"))
    monkeypatch.setenv("PIE_BACKUP_DIR", str(work_dir / "backups"))
    monkeypatch.setenv("PIE_EXPORT_DIR", str(work_dir / "exports"))
    monkeypatch.setenv("PIE_EXTRACTOR_BACKEND", "fake")


def _db(work_dir: Path):
    """Return an open sqlite3 connection with Row factory."""
    conn = sqlite3.connect(str(work_dir / "pie.db"))
    conn.row_factory = sqlite3.Row
    return conn


def _structured_row(work_dir: Path, structured_id: str) -> dict:
    """Fetch the structured entry joined with raw entry."""
    with _db(work_dir) as conn:
        row = conn.execute(
            """
            SELECT s.*, r.content AS raw_content
            FROM structured_entries s
            JOIN raw_entries r ON r.id = s.raw_entry_id
            WHERE s.id = ?;
            """,
            (structured_id,),
        ).fetchone()
        return dict(row)


def _parse_structured_id(output: str) -> str:
    """Extract structured_entry_id from CLI add output."""
    import re

    match = re.search(r"Structured ID:\s+([0-9a-f-]+)", output)
    assert match is not None, f"Could not parse Structured ID from:\n{output}"
    return match.group(1)


# ═══════════════════════════════════════════════════════════════════════════
# 1. Backward compatibility — no flags
# ═══════════════════════════════════════════════════════════════════════════


class TestNoFlags:
    """pie add without any new flags must continue working exactly as before."""

    def test_add_without_flags_works(self, monkeypatch, work_dir):
        _configure_env(monkeypatch, work_dir)
        result = CliRunner().invoke(cli, [
            "add",
            "Projeto: PIE. Tipo: decisão. Decidi manter SQLite.",
        ])
        assert result.exit_code == 0
        assert "[OK] Entry created successfully!" in result.output
        assert "Type:" in result.output

    def test_add_without_flags_has_no_project(self, monkeypatch, work_dir):
        _configure_env(monkeypatch, work_dir)
        result = CliRunner().invoke(cli, [
            "add",
            "Algo sem projeto explícito.",
        ])
        assert result.exit_code == 0
        # project should not appear in output
        assert "Project:" not in result.output

        sid = _parse_structured_id(result.output)
        row = _structured_row(work_dir, sid)
        assert row["project"] is None


# ═══════════════════════════════════════════════════════════════════════════
# 2. --project flag
# ═══════════════════════════════════════════════════════════════════════════


class TestProjectFlag:
    """Validate --project override."""

    def test_project_saved_in_db(self, monkeypatch, work_dir):
        _configure_env(monkeypatch, work_dir)
        result = CliRunner().invoke(cli, [
            "add",
            "Decidi algo importante",
            "--project", "PIE",
        ])
        assert result.exit_code == 0

        sid = _parse_structured_id(result.output)
        row = _structured_row(work_dir, sid)
        assert row["project"] == "PIE"

    def test_project_shown_in_output(self, monkeypatch, work_dir):
        _configure_env(monkeypatch, work_dir)
        result = CliRunner().invoke(cli, [
            "add",
            "Decidi algo importante",
            "--project", "PIE",
        ])
        assert result.exit_code == 0
        assert "Project:       PIE" in result.output

    def test_project_in_structured_json(self, monkeypatch, work_dir):
        _configure_env(monkeypatch, work_dir)
        result = CliRunner().invoke(cli, [
            "add",
            "Decidi algo importante",
            "--project", "Finance Lab",
        ])
        assert result.exit_code == 0

        sid = _parse_structured_id(result.output)
        row = _structured_row(work_dir, sid)
        sj = json.loads(row["structured_json"])
        assert sj["project"] == "Finance Lab"

    def test_entries_list_project_filter_finds_entry(self, monkeypatch, work_dir):
        _configure_env(monkeypatch, work_dir)
        runner = CliRunner()
        result = runner.invoke(cli, [
            "add",
            "Decidi algo importante",
            "--project", "PIE",
        ])
        sid = _parse_structured_id(result.output)

        result = runner.invoke(cli, ["entries", "list", "--project", "PIE"])
        assert result.exit_code == 0
        assert sid in result.output

    def test_search_project_filter_finds_entry(self, monkeypatch, work_dir):
        _configure_env(monkeypatch, work_dir)
        runner = CliRunner()
        result = runner.invoke(cli, [
            "add",
            "Decidi algo importante sobre SQLite",
            "--project", "PIE",
        ])
        sid = _parse_structured_id(result.output)

        result = runner.invoke(cli, ["search", "SQLite", "--project", "PIE"])
        assert result.exit_code == 0
        assert sid in result.output

    def test_project_report_finds_entry(self, monkeypatch, work_dir):
        _configure_env(monkeypatch, work_dir)
        runner = CliRunner()
        runner.invoke(cli, [
            "add",
            "Decidi algo importante",
            "--project", "PIE",
        ])

        from datetime import date

        today = date.today().isoformat()
        result = runner.invoke(cli, ["report", "project", "--project", "PIE"])
        assert result.exit_code == 0
        assert "[OK] Project report generated" in result.output


# ═══════════════════════════════════════════════════════════════════════════
# 3. --type flag
# ═══════════════════════════════════════════════════════════════════════════


class TestTypeFlag:
    """Validate --type override."""

    def test_type_overrides_extraction(self, monkeypatch, work_dir):
        _configure_env(monkeypatch, work_dir)
        # FakeExtractor would classify "Anotação rápida" as general_note
        result = CliRunner().invoke(cli, [
            "add",
            "Anotação rápida",
            "--type", "decision",
        ])
        assert result.exit_code == 0
        assert "Type:          decision" in result.output

        sid = _parse_structured_id(result.output)
        row = _structured_row(work_dir, sid)
        assert row["entry_type"] == "decision"

    def test_type_invalid_gives_friendly_error(self, monkeypatch, work_dir):
        _configure_env(monkeypatch, work_dir)
        result = CliRunner().invoke(cli, [
            "add",
            "Teste",
            "--type", "invalid_type",
        ])
        assert result.exit_code != 0
        # Click.Choice gives a friendly error with valid options
        assert "invalid_type" in result.output
        assert "Traceback" not in result.output

    def test_type_does_not_change_confidence(self, monkeypatch, work_dir):
        _configure_env(monkeypatch, work_dir)
        # "Anotação rápida" → general_note, confidence 0.50
        result = CliRunner().invoke(cli, [
            "add",
            "Anotação rápida",
            "--type", "decision",
        ])
        assert result.exit_code == 0
        # Confidence should still be 0.50 (50%), not boosted
        assert "Confidence:    50%" in result.output

    def test_all_valid_types_accepted(self, monkeypatch, work_dir):
        _configure_env(monkeypatch, work_dir)
        runner = CliRunner()
        for entry_type in EntryType:
            result = runner.invoke(cli, [
                "add",
                f"Teste tipo {entry_type.value}",
                "--type", entry_type.value,
            ])
            assert result.exit_code == 0, f"Failed for type {entry_type.value}: {result.output}"


# ═══════════════════════════════════════════════════════════════════════════
# 4. --tag flag
# ═══════════════════════════════════════════════════════════════════════════


class TestTagFlag:
    """Validate --tag override and merge behavior."""

    def test_single_tag(self, monkeypatch, work_dir):
        _configure_env(monkeypatch, work_dir)
        result = CliRunner().invoke(cli, [
            "add",
            "Decidi algo",
            "--tag", "arquitetura",
        ])
        assert result.exit_code == 0

        sid = _parse_structured_id(result.output)
        row = _structured_row(work_dir, sid)
        sj = json.loads(row["structured_json"])
        assert "arquitetura" in sj["tags"]

    def test_multiple_tags(self, monkeypatch, work_dir):
        _configure_env(monkeypatch, work_dir)
        result = CliRunner().invoke(cli, [
            "add",
            "Decidi algo",
            "--tag", "arquitetura",
            "--tag", "sqlite",
        ])
        assert result.exit_code == 0

        sid = _parse_structured_id(result.output)
        row = _structured_row(work_dir, sid)
        sj = json.loads(row["structured_json"])
        assert "arquitetura" in sj["tags"]
        assert "sqlite" in sj["tags"]

    def test_tags_merged_without_duplicates(self, monkeypatch, work_dir):
        _configure_env(monkeypatch, work_dir)
        # FakeExtractor extracts "decision" tag for entries with "decidi"
        result = CliRunner().invoke(cli, [
            "add",
            "Decidi algo",
            "--tag", "decision",
            "--tag", "extra",
        ])
        assert result.exit_code == 0

        sid = _parse_structured_id(result.output)
        row = _structured_row(work_dir, sid)
        sj = json.loads(row["structured_json"])
        # "decision" should appear only once (from extractor + user merged)
        assert sj["tags"].count("decision") == 1
        assert "extra" in sj["tags"]

    def test_tags_case_normalized(self, monkeypatch, work_dir):
        _configure_env(monkeypatch, work_dir)
        result = CliRunner().invoke(cli, [
            "add",
            "Decidi algo",
            "--tag", "Arquitetura",
            "--tag", "SQLITE",
        ])
        assert result.exit_code == 0

        sid = _parse_structured_id(result.output)
        row = _structured_row(work_dir, sid)
        sj = json.loads(row["structured_json"])
        # Tags should be lowercase
        assert "arquitetura" in sj["tags"]
        assert "sqlite" in sj["tags"]


# ═══════════════════════════════════════════════════════════════════════════
# 5. Combined flags
# ═══════════════════════════════════════════════════════════════════════════


class TestCombinedFlags:
    """Validate using all flags together."""

    def test_all_flags_combined(self, monkeypatch, work_dir):
        _configure_env(monkeypatch, work_dir)
        result = CliRunner().invoke(cli, [
            "add",
            "Decidi manter SQLite como fonte de verdade",
            "--project", "PIE",
            "--type", "decision",
            "--tag", "arquitetura",
            "--tag", "sqlite",
        ])
        assert result.exit_code == 0
        assert "Project:       PIE" in result.output
        assert "Type:          decision" in result.output

        sid = _parse_structured_id(result.output)
        row = _structured_row(work_dir, sid)
        assert row["project"] == "PIE"
        assert row["entry_type"] == "decision"

        sj = json.loads(row["structured_json"])
        assert "arquitetura" in sj["tags"]
        assert "sqlite" in sj["tags"]

    def test_raw_content_never_modified(self, monkeypatch, work_dir):
        _configure_env(monkeypatch, work_dir)
        original_text = "Texto original sem mudança"
        result = CliRunner().invoke(cli, [
            "add",
            original_text,
            "--project", "PIE",
            "--type", "idea",
            "--tag", "test",
        ])
        assert result.exit_code == 0

        sid = _parse_structured_id(result.output)
        row = _structured_row(work_dir, sid)
        assert row["raw_content"] == original_text


# ═══════════════════════════════════════════════════════════════════════════
# 6. Audit logs & Markdown
# ═══════════════════════════════════════════════════════════════════════════


class TestAuditAndMarkdown:
    """Validate that overrides don't break audit or markdown generation."""

    def test_audit_logs_created_with_overrides(self, monkeypatch, work_dir):
        _configure_env(monkeypatch, work_dir)
        result = CliRunner().invoke(cli, [
            "add",
            "Decidi algo",
            "--project", "PIE",
            "--type", "decision",
        ])
        assert result.exit_code == 0

        with _db(work_dir) as conn:
            count = conn.execute("SELECT COUNT(*) FROM audit_logs;").fetchone()[0]
        # Should have at minimum: entry_created, extraction_completed, validation_completed, markdown_generated
        assert count >= 4

    def test_markdown_note_reflects_overrides(self, monkeypatch, work_dir):
        _configure_env(monkeypatch, work_dir)
        result = CliRunner().invoke(cli, [
            "add",
            "Decidi algo",
            "--project", "PIE",
            "--type", "decision",
            "--tag", "arquitetura",
        ])
        assert result.exit_code == 0

        notes_dir = work_dir / "notes"
        assert notes_dir.exists()
        note_files = list(notes_dir.glob("*.md"))
        assert len(note_files) >= 1

        content = note_files[0].read_text(encoding="utf-8")
        # Markdown should reflect overridden values
        assert "PIE" in content
        assert "decision" in content


# ═══════════════════════════════════════════════════════════════════════════
# 7. Review flow with overrides
# ═══════════════════════════════════════════════════════════════════════════


class TestReviewWithOverrides:
    """Validate that review flow works correctly with overridden entries."""

    def test_low_confidence_with_override_still_triggers_review(self, monkeypatch, work_dir):
        """Even with --project and --type, confidence 0.50 still triggers needs_review."""
        _configure_env(monkeypatch, work_dir)
        runner = CliRunner()
        # "Anotação rápida" → general_note, confidence 0.50
        result = runner.invoke(cli, [
            "add",
            "Anotação rápida",
            "--project", "PIE",
            "--type", "decision",
        ])
        assert result.exit_code == 0
        assert "needs_review" in result.output

        sid = _parse_structured_id(result.output)

        # Should appear in review list
        result = runner.invoke(cli, ["review", "list"])
        assert result.exit_code == 0
        assert sid in result.output

        # Approve it
        result = runner.invoke(cli, ["review", "approve", sid])
        assert result.exit_code == 0
        assert "[OK] Review entry approved" in result.output

        # Should no longer appear in review list
        result = runner.invoke(cli, ["review", "list"])
        assert sid not in result.output
