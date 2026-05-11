"""Tests for the ingestion pipeline (pie add flow)."""

from pathlib import Path

import pytest

from personal_intelligence_engine.app.adapters.local_llm_extractor import LocalLLMExtractorError
from personal_intelligence_engine.app.services.extraction_service import ExtractionService


class FailingExtractor:
    def extract(self, content: str):
        raise LocalLLMExtractorError("Ollama is unavailable. Is the local server running?")


class TestIngestion:
    """Tests for the full ingestion pipeline."""

    def test_add_saves_raw_entry(self, app):
        """pie add saves a raw entry in the database."""
        result = app.add_entry("Tive uma ideia para o projeto")
        assert result["status"] == "ok"
        assert result["entry_id"]

        # Verify raw entry exists in DB
        raw = app.entries_repo.get_raw_entry(result["entry_id"])
        assert raw is not None
        assert raw.content == "Tive uma ideia para o projeto"

    def test_add_saves_structured_entry(self, app):
        """pie add creates a structured entry."""
        result = app.add_entry("Tive uma ideia para o projeto")
        assert result["structured_entry_id"]

        structured = app.entries_repo.get_structured_entry(result["structured_entry_id"])
        assert structured is not None
        assert structured.raw_entry_id == result["entry_id"]

    def test_add_generates_markdown(self, app):
        """pie add generates a Markdown note file."""
        result = app.add_entry("Preciso fazer uma tarefa importante")
        note_path = Path(result["note_path"])
        assert note_path.exists()

        content = note_path.read_text(encoding="utf-8")
        assert "---" in content  # frontmatter
        assert result["structured_entry_id"] in content

    def test_add_creates_audit_log(self, app):
        """pie add creates audit log entries."""
        result = app.add_entry("Decidi mudar a arquitetura")
        logs = app.audit.get_logs_for_entry(result["entry_id"])
        assert len(logs) >= 4  # entry_created, extraction, validation, markdown

        actions = [log.action.value for log in logs]
        assert "entry_created" in actions
        assert "extraction_completed" in actions
        assert "validation_completed" in actions
        assert "markdown_generated" in actions

    def test_multiple_entries(self, app):
        """Multiple entries can be added sequentially."""
        r1 = app.add_entry("Primeira entrada")
        r2 = app.add_entry("Segunda entrada")
        assert r1["entry_id"] != r2["entry_id"]

    def test_entry_source_is_recorded(self, app):
        """Source is correctly recorded."""
        result = app.add_entry("Test entry", source="api")
        raw = app.entries_repo.get_raw_entry(result["entry_id"])
        assert raw.source == "api"

    def test_blank_entry_is_rejected(self, app):
        """Blank entries are rejected before extraction."""
        with pytest.raises(ValueError, match="Input text cannot be empty"):
            app.add_entry("   ")

    def test_extraction_failure_preserves_raw_entry_without_structured_entry(self, app):
        """LLM extraction failures preserve raw input and do not create partial structured data."""
        app.extraction = ExtractionService(FailingExtractor())

        with pytest.raises(LocalLLMExtractorError, match="Ollama is unavailable"):
            app.add_entry("Entrada sintetica para falha controlada de LLM")

        raw_rows = app.db.fetchall("SELECT * FROM raw_entries;")
        structured_rows = app.db.fetchall("SELECT * FROM structured_entries;")
        audit_rows = app.db.fetchall("SELECT * FROM audit_logs WHERE status = 'error';")

        assert len(raw_rows) == 1
        assert raw_rows[0]["content"] == "Entrada sintetica para falha controlada de LLM"
        assert raw_rows[0]["status"] == "error"
        assert structured_rows == []
        assert len(audit_rows) == 1
        assert "Ollama is unavailable" in audit_rows[0]["error_message"]
