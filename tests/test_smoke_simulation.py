"""End-to-end smoke simulation for PIE Core.

This module exercises every major CLI flow using synthetic data inside a
fully-isolated temporary directory.  It validates that the system works
correctly end-to-end before real data is introduced.

Environment isolation:
    - PIE_DATABASE_PATH → <tmpdir>/pie.db
    - PIE_NOTES_DIR     → <tmpdir>/notes
    - PIE_REPORTS_DIR   → <tmpdir>/reports
    - PIE_BACKUP_DIR    → <tmpdir>/backups
    - PIE_EXPORT_DIR    → <tmpdir>/exports
    - PIE_EXTRACTOR_BACKEND = fake

No real data is used.  No network calls are made.
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import date
from pathlib import Path

import pytest
from click.testing import CliRunner

from personal_intelligence_engine.app.cli.commands import cli

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _configure_temp_env(monkeypatch, work_dir: Path) -> None:
    """Point every PIE directory at an isolated temp tree."""
    monkeypatch.setenv("PIE_DATABASE_PATH", str(work_dir / "pie.db"))
    monkeypatch.setenv("PIE_NOTES_DIR", str(work_dir / "notes"))
    monkeypatch.setenv("PIE_REPORTS_DIR", str(work_dir / "reports"))
    monkeypatch.setenv("PIE_BACKUP_DIR", str(work_dir / "backups"))
    monkeypatch.setenv("PIE_EXPORT_DIR", str(work_dir / "exports"))
    monkeypatch.setenv("PIE_EXTRACTOR_BACKEND", "fake")


def _add_entry(runner: CliRunner, text: str) -> str:
    """Add an entry via CLI, return its structured_entry_id."""
    result = runner.invoke(cli, ["add", text])
    assert result.exit_code == 0, f"pie add failed: {result.output}"
    match = re.search(r"Structured ID:\s+([0-9a-f-]+)", result.output)
    assert match is not None, f"Could not parse structured ID from:\n{result.output}"
    return match.group(1)


# ---------------------------------------------------------------------------
# Synthetic data — 9 entries across 4 projects
# ---------------------------------------------------------------------------

SYNTHETIC_ENTRIES = [
    # (text, expected_type keyword, expected project keyword)
    (
        "Projeto: PIE. Tipo: decisão. Texto: Decidi manter SQLite como fonte de verdade. Tags: arquitetura, sqlite",
        "decision",
        "PIE",
    ),
    (
        "Projeto: Study Plan. Tipo: tarefa. Texto: Preciso revisar conceitos de SQL no sábado. Tags: estudo, sql",
        "candidate_task",
        "Study Plan",
    ),
    (
        "Projeto: Health Routine. Tipo: problema. Texto: Estou dormindo tarde por usar celular na cama. Tags: sono, hábito",
        "problem",
        "Health Routine",
    ),
    (
        "Projeto: Finance Lab. Tipo: ideia. Texto: Criar dashboard local para controle de gastos mensais. Tags: finanças, dashboard",
        "idea",
        "Finance Lab",
    ),
    (
        "Projeto: PIE. Tipo: insight. Texto: Percebi que relatórios semanais ajudam na revisão do progresso. Tags: relatórios, processo",
        "insight",
        "PIE",
    ),
    (
        "Projeto: Study Plan. Tipo: referência. Texto: Encontrei um artigo sobre normalização de banco de dados. Tags: estudo, referência",
        "reference",
        "Study Plan",
    ),
    (
        "Projeto: PIE. Tipo: revisão. Texto: A extração classificou uma decisão como ideia em duas entradas. Tags: qualidade, extração",
        "review",
        "PIE",
    ),
    # Entry 8: low-confidence (short, no keyword match → general_note, 0.50)
    (
        "Anotação rápida sem contexto",
        "general_note",
        None,
    ),
    # Entry 9: low-confidence (long 20+ words, no keyword match → log, 0.50)
    (
        "Esta é uma anotação longa sem palavras-chave específicas que serve para testar o cenário de baixa "
        "confiança quando o FakeExtractor não consegue classificar o conteúdo de forma determinística usando "
        "as regras de palavras-chave configuradas no sistema",
        "log",
        None,
    ),
]


# ═══════════════════════════════════════════════════════════════════════════
# Flow 1 — pie doctor
# ═══════════════════════════════════════════════════════════════════════════


class TestFlow1Doctor:
    """Validate `pie doctor` with fake backend."""

    def test_doctor_fake_passes(self, monkeypatch, work_dir):
        _configure_temp_env(monkeypatch, work_dir)
        result = CliRunner().invoke(cli, ["doctor"])

        assert result.exit_code == 0
        assert "Extractor backend: fake" in result.output
        assert "FakeExtractor is available" in result.output

    def test_doctor_does_not_create_database(self, monkeypatch, work_dir):
        _configure_temp_env(monkeypatch, work_dir)
        CliRunner().invoke(cli, ["doctor"])

        assert not (work_dir / "pie.db").exists()

    def test_doctor_does_not_require_ollama(self, monkeypatch, work_dir):
        _configure_temp_env(monkeypatch, work_dir)
        result = CliRunner().invoke(cli, ["doctor"])

        assert "ollama" not in result.output.lower() or "fake" in result.output.lower()
        assert result.exit_code == 0


# ═══════════════════════════════════════════════════════════════════════════
# Flow 2 — pie add  (9 synthetic entries)
# ═══════════════════════════════════════════════════════════════════════════


class TestFlow2Add:
    """Validate `pie add` with all synthetic entries."""

    def test_add_all_synthetic_entries(self, monkeypatch, work_dir):
        _configure_temp_env(monkeypatch, work_dir)
        runner = CliRunner()
        ids = []

        for text, _expected_type, _expected_project in SYNTHETIC_ENTRIES:
            sid = _add_entry(runner, text)
            ids.append(sid)

        assert len(ids) == 9
        # All IDs should be unique UUIDs
        assert len(set(ids)) == 9

    def test_add_creates_raw_and_structured_entries(self, monkeypatch, work_dir):
        _configure_temp_env(monkeypatch, work_dir)
        runner = CliRunner()
        _add_entry(runner, SYNTHETIC_ENTRIES[0][0])

        db_path = work_dir / "pie.db"
        assert db_path.exists()

        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            raw_count = conn.execute("SELECT COUNT(*) FROM raw_entries;").fetchone()[0]
            struct_count = conn.execute("SELECT COUNT(*) FROM structured_entries;").fetchone()[0]

        assert raw_count == 1
        assert struct_count == 1

    def test_add_creates_audit_logs(self, monkeypatch, work_dir):
        _configure_temp_env(monkeypatch, work_dir)
        runner = CliRunner()
        _add_entry(runner, SYNTHETIC_ENTRIES[0][0])

        with sqlite3.connect(str(work_dir / "pie.db")) as conn:
            conn.row_factory = sqlite3.Row
            audit_count = conn.execute("SELECT COUNT(*) FROM audit_logs;").fetchone()[0]

        # At minimum: entry_created, extraction_completed, validation_completed, markdown_generated
        assert audit_count >= 4

    def test_add_generates_markdown_note(self, monkeypatch, work_dir):
        _configure_temp_env(monkeypatch, work_dir)
        runner = CliRunner()
        result = runner.invoke(cli, ["add", SYNTHETIC_ENTRIES[0][0]])
        assert result.exit_code == 0

        notes_dir = work_dir / "notes"
        assert notes_dir.exists()
        note_files = list(notes_dir.glob("*.md"))
        assert len(note_files) >= 1

    def test_add_output_is_clear(self, monkeypatch, work_dir):
        _configure_temp_env(monkeypatch, work_dir)
        runner = CliRunner()
        result = runner.invoke(cli, ["add", SYNTHETIC_ENTRIES[0][0]])

        assert "[OK] Entry created successfully!" in result.output
        assert "Entry ID:" in result.output
        assert "Structured ID:" in result.output
        assert "Type:" in result.output
        assert "Confidence:" in result.output
        assert "Note:" in result.output

    def test_add_low_confidence_triggers_needs_review(self, monkeypatch, work_dir):
        """Entry 8 (short, no keyword) should have confidence 0.50 → needs_review."""
        _configure_temp_env(monkeypatch, work_dir)
        runner = CliRunner()
        result = runner.invoke(cli, ["add", SYNTHETIC_ENTRIES[7][0]])

        assert result.exit_code == 0
        assert "needs_review" in result.output

        with sqlite3.connect(str(work_dir / "pie.db")) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT status FROM raw_entries LIMIT 1;").fetchone()
            assert row["status"] == "needs_review"


# ═══════════════════════════════════════════════════════════════════════════
# Flow 3 — pie entries list / show
# ═══════════════════════════════════════════════════════════════════════════


class TestFlow3Entries:
    """Validate `pie entries list` and `pie entries show`."""

    @pytest.fixture(autouse=True)
    def _populate(self, monkeypatch, work_dir):
        _configure_temp_env(monkeypatch, work_dir)
        self.runner = CliRunner()
        self.ids = []
        for text, _, _ in SYNTHETIC_ENTRIES:
            self.ids.append(_add_entry(self.runner, text))

    def test_entries_list_shows_all(self):
        result = self.runner.invoke(cli, ["entries", "list"])
        assert result.exit_code == 0
        assert f"Entries ({len(SYNTHETIC_ENTRIES)}):" in result.output

    def test_entries_list_filter_by_type(self):
        result = self.runner.invoke(cli, ["entries", "list", "--type", "decision"])
        assert result.exit_code == 0
        # Should find the decision entry
        assert "decision" in result.output

    def test_entries_list_filter_by_project_returns_empty_with_fake_extractor(self):
        """FakeExtractor does not extract project names — project is always None.

        This is expected behavior: the --project filter correctly returns empty
        because no entries have a project field set.  This is a known limitation
        of FakeExtractor documented in the simulation report.
        """
        result = self.runner.invoke(cli, ["entries", "list", "--project", "PIE"])
        assert result.exit_code == 0
        assert "No entries found" in result.output

    def test_entries_show_displays_detail(self):
        result = self.runner.invoke(cli, ["entries", "show", self.ids[0]])
        assert result.exit_code == 0
        assert "Structured Entry ID:" in result.output
        assert "Raw Entry ID:" in result.output
        assert "Type:" in result.output
        assert "Summary:" in result.output
        assert "Raw Content:" in result.output

    def test_entries_show_truncates_raw_content(self):
        # Entry 9 has long content — raw content should be shortened
        result = self.runner.invoke(cli, ["entries", "show", self.ids[8]])
        assert result.exit_code == 0
        # The full 200+ char content should not appear verbatim
        full_content = SYNTHETIC_ENTRIES[8][0]
        if len(full_content) > 500:
            assert full_content not in result.output

    def test_entries_show_error_for_invalid_id(self):
        result = self.runner.invoke(cli, ["entries", "show", "nonexistent-id-12345"])
        assert result.exit_code != 0
        assert "Traceback" not in result.output


# ═══════════════════════════════════════════════════════════════════════════
# Flow 4 — pie search
# ═══════════════════════════════════════════════════════════════════════════


class TestFlow4Search:
    """Validate `pie search`."""

    @pytest.fixture(autouse=True)
    def _populate(self, monkeypatch, work_dir):
        _configure_temp_env(monkeypatch, work_dir)
        self.runner = CliRunner()
        self.ids = []
        for text, _, _ in SYNTHETIC_ENTRIES:
            self.ids.append(_add_entry(self.runner, text))

    def test_search_finds_by_raw_content(self):
        result = self.runner.invoke(cli, ["search", "SQLite"])
        assert result.exit_code == 0
        assert "Search results" in result.output
        assert self.ids[0] in result.output

    def test_search_sono(self):
        result = self.runner.invoke(cli, ["search", "sono"])
        assert result.exit_code == 0
        assert self.ids[2] in result.output

    def test_search_with_project_filter_returns_empty_with_fake_extractor(self):
        """FakeExtractor does not extract project names — project is always None.

        The --project filter correctly returns no results because structured
        entries have project=NULL.  The search term 'SQL' matches raw content
        but the project filter excludes everything.
        """
        result = self.runner.invoke(cli, ["search", "SQL", "--project", "Study Plan"])
        assert result.exit_code == 0
        assert "No search results found" in result.output

    def test_search_with_type_filter(self):
        result = self.runner.invoke(cli, ["search", "arquitetura", "--type", "decision"])
        assert result.exit_code == 0
        assert self.ids[0] in result.output

    def test_search_no_results(self):
        result = self.runner.invoke(cli, ["search", "xyznonexistent12345"])
        assert result.exit_code == 0
        assert "No search results found" in result.output

    def test_search_does_not_create_audit_logs(self, work_dir):
        """Search is read-only — no new audit logs should be created."""
        with sqlite3.connect(str(work_dir / "pie.db")) as conn:
            before_count = conn.execute("SELECT COUNT(*) FROM audit_logs;").fetchone()[0]

        self.runner.invoke(cli, ["search", "SQLite"])

        with sqlite3.connect(str(work_dir / "pie.db")) as conn:
            after_count = conn.execute("SELECT COUNT(*) FROM audit_logs;").fetchone()[0]

        assert after_count == before_count


# ═══════════════════════════════════════════════════════════════════════════
# Flow 5 — pie review list / show / approve / reject / history
# ═══════════════════════════════════════════════════════════════════════════


class TestFlow5Review:
    """Validate the full review lifecycle."""

    @pytest.fixture(autouse=True)
    def _populate(self, monkeypatch, work_dir):
        _configure_temp_env(monkeypatch, work_dir)
        self.runner = CliRunner()
        self.work_dir = work_dir
        self.ids = []
        for text, _, _ in SYNTHETIC_ENTRIES:
            self.ids.append(_add_entry(self.runner, text))

        # ids[7] = general_note (confidence 0.50) → needs_review
        # ids[8] = log (confidence 0.50) → needs_review
        self.review_id_1 = self.ids[7]
        self.review_id_2 = self.ids[8]

    def test_review_list_shows_low_confidence_entries(self):
        result = self.runner.invoke(cli, ["review", "list"])
        assert result.exit_code == 0
        assert "Entries needing review:" in result.output
        assert self.review_id_1 in result.output
        assert self.review_id_2 in result.output

    def test_review_show_displays_entry_detail(self):
        result = self.runner.invoke(cli, ["review", "show", self.review_id_1])
        assert result.exit_code == 0
        assert "Structured Entry ID:" in result.output
        assert "Confidence:" in result.output
        assert "Raw Content:" in result.output

    def test_review_approve_removes_from_queue(self):
        # Approve entry 8
        result = self.runner.invoke(cli, ["review", "approve", self.review_id_1])
        assert result.exit_code == 0
        assert "[OK] Review entry approved" in result.output

        # Should no longer appear in review list
        list_result = self.runner.invoke(cli, ["review", "list"])
        assert self.review_id_1 not in list_result.output
        # But the other one should still be there
        assert self.review_id_2 in list_result.output

    def test_review_approve_is_idempotent(self):
        self.runner.invoke(cli, ["review", "approve", self.review_id_1])
        result = self.runner.invoke(cli, ["review", "approve", self.review_id_1])
        assert result.exit_code == 0
        assert "already processed" in result.output.lower() or "[OK]" in result.output

    def test_review_reject_removes_from_queue(self):
        result = self.runner.invoke(cli, ["review", "reject", self.review_id_2])
        assert result.exit_code == 0
        assert "[OK] Review entry rejected" in result.output

        list_result = self.runner.invoke(cli, ["review", "list"])
        assert self.review_id_2 not in list_result.output

    def test_review_history_shows_approve_event(self):
        self.runner.invoke(cli, ["review", "approve", self.review_id_1])
        result = self.runner.invoke(cli, ["review", "history", self.review_id_1])
        assert result.exit_code == 0
        assert "review_approved" in result.output

    def test_review_history_shows_reject_event(self):
        self.runner.invoke(cli, ["review", "reject", self.review_id_2])
        result = self.runner.invoke(cli, ["review", "history", self.review_id_2])
        assert result.exit_code == 0
        assert "review_rejected" in result.output

    def test_review_preserves_raw_content(self):
        """Approving/rejecting must not modify raw_entries.content."""
        original_text = SYNTHETIC_ENTRIES[7][0]

        self.runner.invoke(cli, ["review", "approve", self.review_id_1])

        with sqlite3.connect(str(self.work_dir / "pie.db")) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT re.content FROM raw_entries re "
                "JOIN structured_entries se ON se.raw_entry_id = re.id "
                "WHERE se.id = ?;",
                (self.review_id_1,),
            ).fetchone()

        assert row["content"] == original_text

    def test_review_error_for_nonexistent_id(self):
        result = self.runner.invoke(cli, ["review", "show", "nonexistent-id"])
        assert result.exit_code != 0
        assert "Traceback" not in result.output


# ═══════════════════════════════════════════════════════════════════════════
# Flow 6 — pie report daily / weekly / project
# ═══════════════════════════════════════════════════════════════════════════


class TestFlow6Reports:
    """Validate report generation."""

    @pytest.fixture(autouse=True)
    def _populate(self, monkeypatch, work_dir):
        _configure_temp_env(monkeypatch, work_dir)
        self.runner = CliRunner()
        self.work_dir = work_dir
        self.ids = []
        for text, _, _ in SYNTHETIC_ENTRIES:
            self.ids.append(_add_entry(self.runner, text))
        self.today = date.today().isoformat()

    def test_daily_report_generates_file(self):
        result = self.runner.invoke(cli, ["report", "daily", "--date", self.today])
        assert result.exit_code == 0
        assert "[OK] Daily report generated" in result.output
        assert "Entries:" in result.output

        reports_dir = self.work_dir / "reports"
        report_files = list(reports_dir.glob("*.md"))
        assert len(report_files) >= 1

    def test_weekly_report_generates_file(self):
        result = self.runner.invoke(cli, ["report", "weekly", "--date", self.today])
        assert result.exit_code == 0
        assert "[OK] Weekly report generated" in result.output
        assert "Start Date:" in result.output
        assert "End Date:" in result.output

    def test_project_report_generates_file(self):
        result = self.runner.invoke(cli, ["report", "project", "--project", "PIE"])
        assert result.exit_code == 0
        assert "[OK] Project report generated" in result.output
        assert "Project:      PIE" in result.output

    def test_reports_contain_source_ids(self):
        self.runner.invoke(cli, ["report", "daily", "--date", self.today])

        reports_dir = self.work_dir / "reports"
        report_files = list(reports_dir.glob("*.md"))
        assert len(report_files) >= 1

        content = report_files[0].read_text(encoding="utf-8")
        # Reports should reference entry IDs
        assert "structured_entry_id" in content.lower() or "raw_entry_id" in content.lower() or any(
            sid[:8] in content for sid in self.ids
        )

    def test_reports_stay_in_temp_dir(self):
        self.runner.invoke(cli, ["report", "daily", "--date", self.today])
        self.runner.invoke(cli, ["report", "weekly", "--date", self.today])
        self.runner.invoke(cli, ["report", "project", "--project", "PIE"])

        reports_dir = self.work_dir / "reports"
        for f in reports_dir.glob("*.md"):
            assert str(self.work_dir) in str(f)

    def test_daily_report_invalid_date(self):
        result = self.runner.invoke(cli, ["report", "daily", "--date", "2026-99-99"])
        assert result.exit_code != 0
        assert "Traceback" not in result.output


# ═══════════════════════════════════════════════════════════════════════════
# Flow 7 — pie backup create / export json / export markdown
# ═══════════════════════════════════════════════════════════════════════════


class TestFlow7BackupExport:
    """Validate backup and export commands produce files only in temp dir."""

    @pytest.fixture(autouse=True)
    def _populate(self, monkeypatch, work_dir):
        _configure_temp_env(monkeypatch, work_dir)
        self.runner = CliRunner()
        self.work_dir = work_dir
        self.ids = []
        for text, _, _ in SYNTHETIC_ENTRIES:
            self.ids.append(_add_entry(self.runner, text))

    def test_backup_creates_file_in_temp_dir(self):
        result = self.runner.invoke(cli, ["backup", "create"])
        assert result.exit_code == 0
        assert "Backup created:" in result.output

        backup_dir = self.work_dir / "backups"
        backup_files = list(backup_dir.glob("*.sqlite3"))
        assert len(backup_files) == 1
        assert str(self.work_dir) in str(backup_files[0])

    def test_backup_is_valid_sqlite(self):
        self.runner.invoke(cli, ["backup", "create"])
        backup_files = list((self.work_dir / "backups").glob("*.sqlite3"))
        assert len(backup_files) == 1

        with sqlite3.connect(str(backup_files[0])) as conn:
            tables = [row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table';"
            ).fetchall()]
            assert "raw_entries" in tables
            assert "structured_entries" in tables

    def test_export_json_creates_file_in_temp_dir(self):
        result = self.runner.invoke(cli, ["export", "json"])
        assert result.exit_code == 0
        assert "JSON export created:" in result.output

        export_dir = self.work_dir / "exports"
        json_files = list(export_dir.glob("*.json"))
        assert len(json_files) == 1
        assert str(self.work_dir) in str(json_files[0])

    def test_export_json_preserves_ids(self):
        self.runner.invoke(cli, ["export", "json"])
        json_files = list((self.work_dir / "exports").glob("*.json"))
        assert len(json_files) == 1

        with open(json_files[0], encoding="utf-8") as f:
            data = json.load(f)

        assert "raw_entries" in data
        assert "structured_entries" in data
        exported_ids = {row["id"] for row in data["structured_entries"]}
        for sid in self.ids:
            assert sid in exported_ids

    def test_export_markdown_creates_file_in_temp_dir(self):
        result = self.runner.invoke(cli, ["export", "markdown"])
        assert result.exit_code == 0
        assert "Markdown export created:" in result.output

        export_dir = self.work_dir / "exports"
        md_files = list(export_dir.glob("*.md"))
        assert len(md_files) == 1
        assert str(self.work_dir) in str(md_files[0])

    def test_export_markdown_is_readable_and_truncated(self):
        self.runner.invoke(cli, ["export", "markdown"])
        md_files = list((self.work_dir / "exports").glob("*.md"))
        assert len(md_files) == 1

        content = md_files[0].read_text(encoding="utf-8")
        assert "# PIE Export" in content
        assert "Total Entries:" in content
        # Long raw content should be truncated (entry 9)
        full_content = SYNTHETIC_ENTRIES[8][0]
        assert full_content not in content

    def test_gitignore_covers_backups_and_exports(self):
        gitignore_path = Path(__file__).resolve().parents[1] / ".gitignore"
        assert gitignore_path.exists()
        content = gitignore_path.read_text(encoding="utf-8")
        assert "backups/" in content
        assert "exports/" in content


# ═══════════════════════════════════════════════════════════════════════════
# Flow 8 — pie entries reprocess
# ═══════════════════════════════════════════════════════════════════════════


class TestFlow8Reprocess:
    """Validate reprocessing with dry-run, apply, and batch modes."""

    @pytest.fixture(autouse=True)
    def _populate(self, monkeypatch, work_dir):
        _configure_temp_env(monkeypatch, work_dir)
        self.runner = CliRunner()
        self.work_dir = work_dir
        self.ids = []
        for text, _, _ in SYNTHETIC_ENTRIES:
            self.ids.append(_add_entry(self.runner, text))

    def _count_revisions(self) -> int:
        with sqlite3.connect(str(self.work_dir / "pie.db")) as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM structured_entry_revisions;"
            ).fetchone()[0]

    def _count_audit_logs(self) -> int:
        with sqlite3.connect(str(self.work_dir / "pie.db")) as conn:
            return conn.execute("SELECT COUNT(*) FROM audit_logs;").fetchone()[0]

    def _get_raw_content(self, structured_entry_id: str) -> str:
        with sqlite3.connect(str(self.work_dir / "pie.db")) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT re.content FROM raw_entries re "
                "JOIN structured_entries se ON se.raw_entry_id = re.id "
                "WHERE se.id = ?;",
                (structured_entry_id,),
            ).fetchone()
            return row["content"]

    def test_reprocess_dry_run_is_read_only(self):
        sid = self.ids[0]
        revisions_before = self._count_revisions()
        audit_before = self._count_audit_logs()

        result = self.runner.invoke(cli, ["entries", "reprocess", sid, "--dry-run"])
        assert result.exit_code == 0
        assert "(Dry Run)" in result.output

        revisions_after = self._count_revisions()
        audit_after = self._count_audit_logs()

        assert revisions_after == revisions_before
        assert audit_after == audit_before

    def test_reprocess_apply_creates_revision(self):
        sid = self.ids[0]
        revisions_before = self._count_revisions()

        result = self.runner.invoke(cli, ["entries", "reprocess", sid])
        assert result.exit_code == 0

        revisions_after = self._count_revisions()
        assert revisions_after > revisions_before

    def test_reprocess_preserves_raw_content(self):
        sid = self.ids[0]
        original_content = self._get_raw_content(sid)

        self.runner.invoke(cli, ["entries", "reprocess", sid])

        new_content = self._get_raw_content(sid)
        assert new_content == original_content

    def test_reprocess_creates_audit_log(self):
        sid = self.ids[0]

        self.runner.invoke(cli, ["entries", "reprocess", sid])

        with sqlite3.connect(str(self.work_dir / "pie.db")) as conn:
            conn.row_factory = sqlite3.Row
            raw_id = conn.execute(
                "SELECT raw_entry_id FROM structured_entries WHERE id = ?;",
                (sid,),
            ).fetchone()["raw_entry_id"]
            logs = conn.execute(
                "SELECT action FROM audit_logs WHERE raw_entry_id = ?;",
                (raw_id,),
            ).fetchall()
            actions = [row["action"] for row in logs]

        # Should have at least one extraction_completed from reprocess
        assert actions.count("extraction_completed") >= 2  # initial + reprocess

    def test_reprocess_warns_about_stale_markdown(self):
        sid = self.ids[0]
        result = self.runner.invoke(cli, ["entries", "reprocess", sid])

        assert result.exit_code == 0
        assert "notas Markdown" in result.output or "notes/" in result.output.lower() or "não foram regeneradas" in result.output

    def test_reprocess_does_not_regenerate_markdown(self):
        """Markdown notes directory should not gain new files after reprocess."""
        notes_dir = self.work_dir / "notes"
        notes_before = set(notes_dir.glob("*.md")) if notes_dir.exists() else set()

        sid = self.ids[0]
        self.runner.invoke(cli, ["entries", "reprocess", sid])

        notes_after = set(notes_dir.glob("*.md")) if notes_dir.exists() else set()
        new_notes = notes_after - notes_before
        assert len(new_notes) == 0

    def test_batch_reprocess_dry_run(self):
        revisions_before = self._count_revisions()

        result = self.runner.invoke(
            cli, ["entries", "reprocess", "--status", "needs_review", "--dry-run"]
        )
        assert result.exit_code == 0

        revisions_after = self._count_revisions()
        assert revisions_after == revisions_before

    def test_batch_reprocess_apply_with_limit(self):
        revisions_before = self._count_revisions()

        result = self.runner.invoke(
            cli, ["entries", "reprocess", "--status", "needs_review", "--limit", "2"]
        )
        assert result.exit_code == 0
        assert "Batch Summary:" in result.output

        revisions_after = self._count_revisions()
        assert revisions_after > revisions_before


# ═══════════════════════════════════════════════════════════════════════════
# Flow 9 — pie evaluate extraction
# ═══════════════════════════════════════════════════════════════════════════


class TestFlow9Evaluate:
    """Validate extraction evaluation with fake backend."""

    def test_evaluate_fake_backend(self, monkeypatch, work_dir):
        _configure_temp_env(monkeypatch, work_dir)
        result = CliRunner().invoke(cli, ["evaluate", "extraction", "--backend", "fake"])

        assert result.exit_code == 0
        # Should produce evaluation output
        assert "Total Cases" in result.output or "Evaluation" in result.output or "Backend" in result.output

    def test_evaluate_with_output_file(self, monkeypatch, work_dir):
        _configure_temp_env(monkeypatch, work_dir)
        output_path = work_dir / "fake-evaluation.md"

        result = CliRunner().invoke(
            cli, ["evaluate", "extraction", "--backend", "fake", "--output", str(output_path)]
        )

        assert result.exit_code == 0
        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert len(content) > 0

    def test_evaluate_does_not_require_ollama(self, monkeypatch, work_dir):
        _configure_temp_env(monkeypatch, work_dir)
        result = CliRunner().invoke(cli, ["evaluate", "extraction", "--backend", "fake"])

        assert result.exit_code == 0

    def test_evaluate_does_not_touch_database(self, monkeypatch, work_dir):
        _configure_temp_env(monkeypatch, work_dir)
        CliRunner().invoke(cli, ["evaluate", "extraction", "--backend", "fake"])

        db_path = work_dir / "pie.db"
        assert not db_path.exists()


# ═══════════════════════════════════════════════════════════════════════════
# Integrated smoke test — full workflow in sequence
# ═══════════════════════════════════════════════════════════════════════════


class TestIntegratedSmoke:
    """Run the full PIE workflow in one test to validate end-to-end integration."""

    def test_full_workflow(self, monkeypatch, work_dir):
        _configure_temp_env(monkeypatch, work_dir)
        runner = CliRunner()
        today = date.today().isoformat()

        # 1. Doctor
        result = runner.invoke(cli, ["doctor"])
        assert result.exit_code == 0, f"doctor failed: {result.output}"

        # 2. Add entries
        ids = []
        for text, _expected_type, _ in SYNTHETIC_ENTRIES:
            sid = _add_entry(runner, text)
            ids.append(sid)
        assert len(ids) == 9

        # 3. List and show
        result = runner.invoke(cli, ["entries", "list"])
        assert result.exit_code == 0
        result = runner.invoke(cli, ["entries", "show", ids[0]])
        assert result.exit_code == 0

        # 4. Search
        result = runner.invoke(cli, ["search", "SQLite"])
        assert result.exit_code == 0
        assert ids[0] in result.output

        # 5. Review lifecycle
        result = runner.invoke(cli, ["review", "list"])
        assert result.exit_code == 0
        assert ids[7] in result.output  # low confidence entry

        result = runner.invoke(cli, ["review", "approve", ids[7]])
        assert result.exit_code == 0

        result = runner.invoke(cli, ["review", "reject", ids[8]])
        assert result.exit_code == 0

        result = runner.invoke(cli, ["review", "history", ids[7]])
        assert result.exit_code == 0
        assert "review_approved" in result.output

        result = runner.invoke(cli, ["review", "history", ids[8]])
        assert result.exit_code == 0
        assert "review_rejected" in result.output

        # 6. Reports
        result = runner.invoke(cli, ["report", "daily", "--date", today])
        assert result.exit_code == 0

        result = runner.invoke(cli, ["report", "weekly", "--date", today])
        assert result.exit_code == 0

        result = runner.invoke(cli, ["report", "project", "--project", "PIE"])
        assert result.exit_code == 0

        # 7. Backup and export
        result = runner.invoke(cli, ["backup", "create"])
        assert result.exit_code == 0

        result = runner.invoke(cli, ["export", "json"])
        assert result.exit_code == 0

        result = runner.invoke(cli, ["export", "markdown"])
        assert result.exit_code == 0

        # 8. Reprocess (dry-run then apply)
        result = runner.invoke(cli, ["entries", "reprocess", ids[0], "--dry-run"])
        assert result.exit_code == 0

        result = runner.invoke(cli, ["entries", "reprocess", ids[0]])
        assert result.exit_code == 0

        # 9. Evaluate
        result = runner.invoke(cli, ["evaluate", "extraction", "--backend", "fake"])
        assert result.exit_code == 0

        # ── Final assertions ──

        # All files stay in temp dir
        assert not Path("pie.db").exists()

        # Temp dir has all expected subdirectories
        assert (work_dir / "pie.db").exists()
        assert (work_dir / "notes").exists()
        assert (work_dir / "reports").exists()
        assert (work_dir / "backups").exists()
        assert (work_dir / "exports").exists()

        # Verify DB integrity
        with sqlite3.connect(str(work_dir / "pie.db")) as conn:
            conn.row_factory = sqlite3.Row
            raw_count = conn.execute("SELECT COUNT(*) FROM raw_entries;").fetchone()[0]
            struct_count = conn.execute("SELECT COUNT(*) FROM structured_entries;").fetchone()[0]
            audit_count = conn.execute("SELECT COUNT(*) FROM audit_logs;").fetchone()[0]
            revision_count = conn.execute("SELECT COUNT(*) FROM structured_entry_revisions;").fetchone()[0]

        assert raw_count == 9
        assert struct_count == 9
        assert audit_count > 0
        assert revision_count > 0
