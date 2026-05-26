"""CLI and integration tests for the entries reprocess command."""

import json
import re
import sqlite3

from click.testing import CliRunner

from personal_intelligence_engine.app.cli.commands import cli
from personal_intelligence_engine.app.domain.schemas import ExtractionResult
from personal_intelligence_engine.app.domain.types import EntryType


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


def test_reprocess_dry_run_does_not_alter_db(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Eu decidi usar SQLite")

    # Mock the extractor to return a different result
    def mock_extract(self, content):
        return ExtractionResult(
            entry_type=EntryType.IDEA,
            summary="New mocked summary",
            confidence=0.99,
            tags=["mocked"],
        )

    monkeypatch.setattr(
        "personal_intelligence_engine.app.adapters.fake_extractor.FakeExtractor.extract",
        mock_extract
    )

    with sqlite3.connect(work_dir / "pie.db") as conn:
        audit_count_before = conn.execute("SELECT COUNT(*) FROM audit_logs;").fetchone()[0]

    # Run dry run
    result = CliRunner().invoke(cli, ["entries", "reprocess", structured_id, "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "Dry Run" in result.output
    assert "Entry Type: 'decision' -> 'idea'" in result.output

    # Query DB to make sure it was NOT changed
    with sqlite3.connect(work_dir / "pie.db") as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM structured_entries WHERE id = ?;", (structured_id,)).fetchone()
        assert row["entry_type"] == "decision"  # Stays decision
        assert row["confidence"] == 0.85

        revisions = conn.execute("SELECT COUNT(*) FROM structured_entry_revisions;").fetchone()[0]
        assert revisions == 0

        audit_count_after = conn.execute("SELECT COUNT(*) FROM audit_logs;").fetchone()[0]
        assert audit_count_after == audit_count_before


def test_reprocess_dry_run_displays_comparison(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Eu decidi usar SQLite")

    def mock_extract(self, content):
        return ExtractionResult(
            entry_type=EntryType.IDEA,
            summary="New mocked summary",
            confidence=0.99,
            tags=["mocked"],
        )

    monkeypatch.setattr(
        "personal_intelligence_engine.app.adapters.fake_extractor.FakeExtractor.extract",
        mock_extract
    )

    result = CliRunner().invoke(cli, ["entries", "reprocess", structured_id, "--dry-run"])
    assert result.exit_code == 0
    assert "Structured Entry ID: " in result.output
    assert "Entry Type: 'decision' -> 'idea'" in result.output
    assert "Summary: " in result.output
    assert "Confidence: 85% -> 99%" in result.output


def test_reprocess_applies_new_version(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Eu decidi usar SQLite")

    def mock_extract(self, content):
        return ExtractionResult(
            entry_type=EntryType.IDEA,
            summary="New mocked summary",
            confidence=0.99,
            tags=["mocked"],
        )

    monkeypatch.setattr(
        "personal_intelligence_engine.app.adapters.fake_extractor.FakeExtractor.extract",
        mock_extract
    )

    result = CliRunner().invoke(cli, ["entries", "reprocess", structured_id])
    assert result.exit_code == 0, result.output
    assert "Reprocessamento aplicado com sucesso!" in result.output

    # Query DB to make sure it was changed
    with sqlite3.connect(work_dir / "pie.db") as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM structured_entries WHERE id = ?;", (structured_id,)).fetchone()
        assert row["entry_type"] == "idea"
        assert row["confidence"] == 0.99
        assert row["summary"] == "New mocked summary"


def test_reprocess_preserves_raw_entries_content(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    raw_text = "Eu decidi usar SQLite para o projeto"
    structured_id = _add_entry(raw_text)

    def mock_extract(self, content):
        return ExtractionResult(
            entry_type=EntryType.IDEA,
            summary="New mocked summary",
            confidence=0.99,
            tags=["mocked"],
        )

    monkeypatch.setattr(
        "personal_intelligence_engine.app.adapters.fake_extractor.FakeExtractor.extract",
        mock_extract
    )

    CliRunner().invoke(cli, ["entries", "reprocess", structured_id])

    with sqlite3.connect(work_dir / "pie.db") as conn:
        conn.row_factory = sqlite3.Row
        # Fetch raw entry
        row = conn.execute("SELECT * FROM raw_entries;").fetchone()
        assert row["content"] == raw_text


def test_reprocess_creates_revision(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Eu decidi usar SQLite")

    def mock_extract(self, content):
        return ExtractionResult(
            entry_type=EntryType.IDEA,
            summary="New mocked summary",
            confidence=0.99,
            tags=["mocked"],
        )

    monkeypatch.setattr(
        "personal_intelligence_engine.app.adapters.fake_extractor.FakeExtractor.extract",
        mock_extract
    )

    CliRunner().invoke(cli, ["entries", "reprocess", structured_id])

    with sqlite3.connect(work_dir / "pie.db") as conn:
        conn.row_factory = sqlite3.Row
        revision = conn.execute("SELECT * FROM structured_entry_revisions WHERE structured_entry_id = ?;", (structured_id,)).fetchone()
        assert revision is not None
        assert revision["reason"] == "reprocess"
        assert revision["actor"] == "system"

        # Check before/after json structures
        before = json.loads(revision["before_json"])
        after = json.loads(revision["after_json"])
        changed = json.loads(revision["changed_fields_json"])

        assert before["entry_type"] == "decision"
        assert after["entry_type"] == "idea"
        assert "content" not in before
        assert "content" not in after
        assert "raw_content" not in before
        assert "raw_content" not in after
        assert "entry_type" in changed
        assert "confidence" in changed
        assert "summary" in changed


def test_reprocess_creates_audit_log(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Eu decidi usar SQLite")

    # Clear prior audit logs to make counting simple
    with sqlite3.connect(work_dir / "pie.db") as conn:
        conn.execute("DELETE FROM audit_logs;")
        conn.commit()

    CliRunner().invoke(cli, ["entries", "reprocess", structured_id])

    with sqlite3.connect(work_dir / "pie.db") as conn:
        cursor = conn.execute("SELECT action, method FROM audit_logs;")
        logs = cursor.fetchall()
        assert ("extraction_completed", "reprocess:fake_extractor") in logs
        assert ("validation_completed", "reprocess") in logs


def test_reprocess_missing_id_returns_error(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    _add_entry("Eu decidi usar SQLite")

    result = CliRunner().invoke(cli, ["entries", "reprocess", "non-existent-id"])
    assert result.exit_code != 0
    assert "No entry found" in result.output or "Could not access configured path" in result.output


def test_reprocess_by_status_selects_correct_entries(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    # FakeExtractor unclassified fallback gives confidence 0.50 (needs_review)
    needs_review_id = _add_entry("Nota sem palavras chave e com confianca baixa")
    # Exact keyword match gives confidence 0.85 (processed)
    valid_id = _add_entry("Eu decidi usar SQLite")

    # Verify initial states
    with sqlite3.connect(work_dir / "pie.db") as conn:
        conn.row_factory = sqlite3.Row
        assert conn.execute("SELECT validation_status FROM structured_entries WHERE id = ?;", (needs_review_id,)).fetchone()[0] == "needs_review"
        assert conn.execute("SELECT validation_status FROM structured_entries WHERE id = ?;", (valid_id,)).fetchone()[0] == "valid"

    # Mock extract to give high confidence for reprocessed entries
    def mock_extract(self, content):
        return ExtractionResult(
            entry_type=EntryType.DECISION,
            summary="Processed decision summary",
            confidence=0.95,
            tags=["reprocessed"],
        )

    monkeypatch.setattr(
        "personal_intelligence_engine.app.adapters.fake_extractor.FakeExtractor.extract",
        mock_extract
    )

    # Reprocess only needs_review
    result = CliRunner().invoke(cli, ["entries", "reprocess", "--status", "needs_review"])
    assert result.exit_code == 0, result.output
    assert needs_review_id in result.output
    assert valid_id not in result.output

    # DB verify
    with sqlite3.connect(work_dir / "pie.db") as conn:
        conn.row_factory = sqlite3.Row
        # The needs_review entry should now be updated and valid
        nr_entry = conn.execute("SELECT * FROM structured_entries WHERE id = ?;", (needs_review_id,)).fetchone()
        assert nr_entry["validation_status"] == "valid"
        assert nr_entry["confidence"] == 0.95

        # The valid entry should not have changed (confidence remains 0.85)
        v_entry = conn.execute("SELECT * FROM structured_entries WHERE id = ?;", (valid_id,)).fetchone()
        assert v_entry["confidence"] == 0.85


def test_reprocess_by_status_respects_limit(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    _add_entry("Nota simples sem palavras chave 1")
    _add_entry("Nota simples sem palavras chave 2")
    _add_entry("Nota simples sem palavras chave 3")

    # Query DB to make sure all 3 are needs_review or processed.
    # Reprocess with --limit 2
    result = CliRunner().invoke(cli, ["entries", "reprocess", "--status", "needs_review", "--limit", "2", "--dry-run"])
    assert result.exit_code == 0
    # Dry run output should print 2 structured entry blocks
    blocks = result.output.count("Structured Entry ID:")
    assert blocks == 2


def test_reprocess_by_status_rejects_invalid_limit(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    _add_entry("Nota simples sem palavras chave")

    result = CliRunner().invoke(
        cli,
        ["entries", "reprocess", "--status", "needs_review", "--limit", "0", "--dry-run"],
    )

    assert result.exit_code != 0
    assert "Invalid value for '--limit'" in result.output


def test_reprocess_by_status_empty_message(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    # Add a valid entry only
    _add_entry("Eu decidi usar SQLite")

    result = CliRunner().invoke(cli, ["entries", "reprocess", "--status", "needs_review"])
    assert result.exit_code == 0
    assert "Nenhuma entrada encontrada" in result.output


def test_reprocess_low_confidence_gets_needs_review(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Eu decidi usar SQLite") # originally valid (0.85)

    # Mock extract to return low confidence (0.45)
    def mock_extract(self, content):
        return ExtractionResult(
            entry_type=EntryType.DECISION,
            summary="Low confidence decision",
            confidence=0.45,
            tags=["low-conf"],
        )

    monkeypatch.setattr(
        "personal_intelligence_engine.app.adapters.fake_extractor.FakeExtractor.extract",
        mock_extract
    )

    result = CliRunner().invoke(cli, ["entries", "reprocess", structured_id])
    assert result.exit_code == 0, result.output

    # Query DB to verify it's marked as needs_review
    with sqlite3.connect(work_dir / "pie.db") as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM structured_entries WHERE id = ?;", (structured_id,)).fetchone()
        assert row["validation_status"] == "needs_review"
        assert row["confidence"] == 0.45


def test_reprocess_does_not_regenerate_markdown(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Eu decidi usar SQLite")

    # Find the note path
    note_dir = work_dir / "notes"
    note_files_before = set(note_dir.glob("*.md"))

    # Mock extract to change entry
    def mock_extract(self, content):
        return ExtractionResult(
            entry_type=EntryType.IDEA,
            summary="Markdown test summary",
            confidence=0.90,
            tags=["idea"],
        )

    monkeypatch.setattr(
        "personal_intelligence_engine.app.adapters.fake_extractor.FakeExtractor.extract",
        mock_extract
    )

    CliRunner().invoke(cli, ["entries", "reprocess", structured_id])

    note_files_after = set(note_dir.glob("*.md"))
    # Verify no new markdown file was created, nor files modified
    assert note_files_before == note_files_after


def test_regression_pie_add_works(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    result = CliRunner().invoke(cli, ["add", "Nova ideia regressiva"])
    assert result.exit_code == 0
    assert "Entry created successfully!" in result.output


def test_regression_cli_commands(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Eu decidi usar SQLite")

    # 1. entries list
    res_list = CliRunner().invoke(cli, ["entries", "list"])
    assert res_list.exit_code == 0
    assert structured_id in res_list.output

    # 2. entries show
    res_show = CliRunner().invoke(cli, ["entries", "show", structured_id])
    assert res_show.exit_code == 0
    assert "decision" in res_show.output

    # 3. search
    res_search = CliRunner().invoke(cli, ["search", "SQLite"])
    assert res_search.exit_code == 0
    assert structured_id in res_search.output

    # 4. review commands
    res_review_list = CliRunner().invoke(cli, ["review", "list"])
    assert res_review_list.exit_code == 0

    # 5. backup/export
    res_backup = CliRunner().invoke(cli, ["backup", "create"])
    assert res_backup.exit_code == 0
