"""Tests for audit logging."""

import json
from contextlib import suppress
from pathlib import Path

from personal_intelligence_engine.app.adapters.local_llm_extractor import LocalLLMExtractor
from personal_intelligence_engine.app.config import Config
from personal_intelligence_engine.app.domain.types import AuditAction, AuditStatus
from personal_intelligence_engine.app.main import PIEApp
from personal_intelligence_engine.app.services.extraction_service import ExtractionService

_MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


class AuditOllamaClient:
    def generate(self, *, base_url, model, prompt, timeout_seconds):
        return {
            "response": json.dumps(
                {
                    "entry_type": "decision",
                    "summary": "Synthetic decision about local extraction.",
                    "confidence": 0.86,
                    "tags": ["decision"],
                    "extra": {},
                }
            )
        }

    def list_models(self, *, base_url, timeout_seconds):
        return ["test-model"]


class SensitiveFailingExtractor:
    prompt_version = "synthetic_prompt_v1"

    def extract(self, content: str):
        raise ValueError(f"Backend failed while processing: {content}")


class TestAuditLog:
    """Tests for audit log functionality."""

    def test_audit_logs_created(self, app):
        """Adding an entry creates audit log records."""
        result = app.add_entry("Decidi usar Click para CLI")
        logs = app.audit.get_logs_for_entry(result["entry_id"])
        assert len(logs) >= 4

    def test_audit_actions_recorded(self, app):
        """All expected audit actions are recorded."""
        result = app.add_entry("Tive uma ideia para o projeto")
        logs = app.audit.get_logs_for_entry(result["entry_id"])
        actions = {log.action for log in logs}

        assert AuditAction.ENTRY_CREATED in actions
        assert AuditAction.EXTRACTION_COMPLETED in actions
        assert AuditAction.VALIDATION_COMPLETED in actions
        assert AuditAction.MARKDOWN_GENERATED in actions

    def test_low_confidence_audit_event(self, app):
        """Low confidence triggers a specific audit event."""
        result = app.add_entry("Texto sem classificação clara")
        assert result["validation_status"] == "needs_review"

        logs = app.audit.get_logs_for_entry(result["entry_id"])
        actions = {log.action for log in logs}
        assert AuditAction.LOW_CONFIDENCE in actions

        # Check that the low confidence log has warning status
        low_conf_logs = [log for log in logs if log.action == AuditAction.LOW_CONFIDENCE]
        assert len(low_conf_logs) == 1
        assert low_conf_logs[0].status == AuditStatus.WARNING

    def test_high_confidence_no_low_confidence_event(self, app):
        """High confidence entries do NOT trigger low_confidence audit."""
        result = app.add_entry("Eu decidi mudar a stack")
        logs = app.audit.get_logs_for_entry(result["entry_id"])
        actions = {log.action for log in logs}
        assert AuditAction.LOW_CONFIDENCE not in actions

    def test_audit_log_has_timestamps(self, app):
        """Audit logs have created_at timestamps."""
        result = app.add_entry("Teste de timestamp")
        logs = app.audit.get_logs_for_entry(result["entry_id"])
        for log in logs:
            assert log.created_at is not None
            assert len(log.created_at) > 0

    def test_audit_log_extraction_method(self, app):
        """Extraction audit log records the method used."""
        result = app.add_entry("Tive uma ideia")
        logs = app.audit.get_logs_for_entry(result["entry_id"])
        extraction_logs = [log for log in logs if log.action == AuditAction.EXTRACTION_COMPLETED]
        assert len(extraction_logs) == 1
        assert extraction_logs[0].method == "fake_extractor"
        assert extraction_logs[0].model_name == "FakeExtractor"

    def test_llm_audit_log_records_backend_model_and_prompt_version(self, work_dir):
        """LLM extraction audit log records backend, model, and prompt version."""
        config = Config(
            database_path=work_dir / "test.db",
            notes_dir=work_dir / "notes",
            reports_dir=work_dir / "reports",
            migrations_dir=_MIGRATIONS_DIR,
            extractor_backend="ollama",
            ollama_model="test-model",
            llm_retry_backoff_seconds=0,
        )
        app = PIEApp(config=config)
        extractor = LocalLLMExtractor(
            base_url="http://localhost:11434",
            model="test-model",
            timeout_seconds=1,
            max_retries=0,
            retry_backoff_seconds=0,
            http_client=AuditOllamaClient(),
        )
        app.extractor = extractor
        app.extraction = ExtractionService(extractor)
        try:
            result = app.add_entry("Decidi usar extracao local sintetica")
            logs = app.audit.get_logs_for_entry(result["entry_id"])
        finally:
            app.close()

        extraction_logs = [log for log in logs if log.action == AuditAction.EXTRACTION_COMPLETED]
        assert len(extraction_logs) == 1
        assert extraction_logs[0].method == "ollama"
        assert extraction_logs[0].model_name == "test-model"
        assert extraction_logs[0].prompt_version == "extraction_prompt_v1"
        assert extraction_logs[0].status == AuditStatus.SUCCESS

    def test_audit_error_redacts_raw_input(self, app):
        """Extraction error audit log does not store the raw input text."""
        sensitive_text = "synthetic private phrase alpha"
        app.extractor = SensitiveFailingExtractor()
        app.extraction = ExtractionService(app.extractor)

        with suppress(ValueError):
            app.add_entry(sensitive_text)

        rows = app.db.fetchall("SELECT * FROM audit_logs WHERE status = 'error';")
        assert len(rows) == 1
        assert sensitive_text not in rows[0]["error_message"]
        assert "[redacted input]" in rows[0]["error_message"]
