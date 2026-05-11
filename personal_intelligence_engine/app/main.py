"""Main application orchestrator for PIE.

Wires together config, database, repositories, services, and adapters.
"""

from __future__ import annotations

from personal_intelligence_engine.app.adapters.fake_extractor import FakeExtractor
from personal_intelligence_engine.app.adapters.local_llm_extractor import LocalLLMExtractor, OllamaClient
from personal_intelligence_engine.app.adapters.markdown_writer import MarkdownWriter
from personal_intelligence_engine.app.config import Config
from personal_intelligence_engine.app.domain.schemas import (
    AuditLogCreate,
    RawEntryCreate,
)
from personal_intelligence_engine.app.domain.types import (
    LOW_CONFIDENCE_THRESHOLD,
    AuditAction,
    AuditStatus,
    EntryStatus,
)
from personal_intelligence_engine.app.repositories.audit_repository import AuditRepository
from personal_intelligence_engine.app.repositories.database import Database
from personal_intelligence_engine.app.repositories.entries_repository import EntriesRepository
from personal_intelligence_engine.app.repositories.reports_repository import ReportsRepository
from personal_intelligence_engine.app.services.audit_service import AuditService
from personal_intelligence_engine.app.services.extraction_service import ExtractionService, Extractor
from personal_intelligence_engine.app.services.ingestion_service import IngestionService
from personal_intelligence_engine.app.services.markdown_service import MarkdownService
from personal_intelligence_engine.app.services.report_service import ReportService
from personal_intelligence_engine.app.services.validation_service import ValidationService


class PIEApp:
    """Top-level application — facade for the full pipeline."""

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config()
        self.config.ensure_dirs()

        # Database
        self.db = Database(self.config)
        self.db.run_migrations()

        # Repositories
        self.entries_repo = EntriesRepository(self.db)
        self.audit_repo = AuditRepository(self.db)
        self.reports_repo = ReportsRepository(self.db)

        # Adapters
        self.extractor = self._build_extractor()
        self.markdown_writer = MarkdownWriter(self.config.notes_dir)

        # Services
        self.ingestion = IngestionService(self.entries_repo)
        self.extraction = ExtractionService(self.extractor)
        self.validation = ValidationService(self.entries_repo)
        self.markdown = MarkdownService(self.markdown_writer, self.entries_repo)
        self.audit = AuditService(self.audit_repo)
        self.report = ReportService(
            self.entries_repo,
            self.reports_repo,
            self.config.reports_dir,
            self.config.local_timezone,
        )

    def _build_extractor(self) -> Extractor:
        """Build the configured extraction adapter."""
        if self.config.extractor_backend == "fake":
            return FakeExtractor()

        if self.config.extractor_backend == "ollama":
            return LocalLLMExtractor(
                base_url=self.config.ollama_base_url,
                model=self.config.ollama_model,
                timeout_seconds=self.config.llm_timeout_seconds,
                max_retries=self.config.llm_max_retries,
                retry_backoff_seconds=self.config.llm_retry_backoff_seconds,
            )

        raise ValueError(
            f"Invalid extractor backend '{self.config.extractor_backend}'. Use 'fake' or 'ollama'."
        )

    def add_entry(self, text: str, source: str = "cli") -> dict:
        """Full pipeline: ingest → extract → validate → markdown → audit.

        Args:
            text: Raw text content.
            source: Source identifier (default: "cli").

        Returns:
            Dict with entry_id, structured_entry_id, status, note_path.
        """
        if not text.strip():
            raise ValueError("Input text cannot be empty.")

        # 1. Ingest raw entry
        raw = self.ingestion.ingest(RawEntryCreate(content=text, source=source))

        # Audit: entry created
        self.audit.log(AuditLogCreate(
            raw_entry_id=raw.id,
            action=AuditAction.ENTRY_CREATED,
            actor="system",
            method="cli",
            input_hash=raw.content_hash,
            status=AuditStatus.SUCCESS,
        ))

        # 2. Extract structured data
        try:
            extraction = self.extraction.extract(text)
        except Exception as exc:
            self.entries_repo.update_raw_entry_status(
                raw.id,
                EntryStatus.ERROR.value,
                raw.updated_at,
            )
            self.audit.log(AuditLogCreate(
                raw_entry_id=raw.id,
                action=AuditAction.EXTRACTION_COMPLETED,
                actor="system",
                method=self._extractor_method(),
                model_name=self._extractor_model_name(),
                prompt_version=self._extractor_prompt_version(),
                status=AuditStatus.ERROR,
                error_message=self._summarize_error(exc, raw_text=text),
            ))
            raise

        # Audit: extraction completed
        self.audit.log(AuditLogCreate(
            raw_entry_id=raw.id,
            action=AuditAction.EXTRACTION_COMPLETED,
            actor="system",
            method=self._extractor_method(),
            model_name=self._extractor_model_name(),
            prompt_version=self._extractor_prompt_version(),
            status=AuditStatus.SUCCESS,
        ))

        # 3. Validate and save structured entry
        structured = self.validation.validate_and_save(raw.id, extraction)

        # Audit: validation completed
        self.audit.log(AuditLogCreate(
            raw_entry_id=raw.id,
            action=AuditAction.VALIDATION_COMPLETED,
            actor="system",
            status=AuditStatus.SUCCESS,
        ))

        # 4. Handle low confidence
        if extraction.confidence < LOW_CONFIDENCE_THRESHOLD:
            self.entries_repo.update_raw_entry_status(
                raw.id,
                EntryStatus.NEEDS_REVIEW.value,
                structured.updated_at,
            )
            self.audit.log(AuditLogCreate(
                raw_entry_id=raw.id,
                action=AuditAction.LOW_CONFIDENCE,
                actor="system",
                status=AuditStatus.WARNING,
                error_message=f"Confidence {extraction.confidence:.2f} below threshold {LOW_CONFIDENCE_THRESHOLD}",
            ))
        else:
            self.entries_repo.update_raw_entry_status(
                raw.id,
                EntryStatus.PROCESSED.value,
                structured.updated_at,
            )

        # 5. Generate Markdown note
        generated = self.markdown.generate_note(structured, text)

        # Audit: markdown generated
        self.audit.log(AuditLogCreate(
            raw_entry_id=raw.id,
            action=AuditAction.MARKDOWN_GENERATED,
            actor="system",
            output_hash=generated.content_hash,
            status=AuditStatus.SUCCESS,
        ))

        return {
            "entry_id": raw.id,
            "structured_entry_id": structured.id,
            "entry_type": structured.entry_type.value,
            "confidence": structured.confidence,
            "validation_status": structured.validation_status.value,
            "note_path": generated.path,
            "status": "ok",
        }

    def generate_daily_report(self, date_str: str) -> dict:
        """Generate a daily report for the given date.

        Args:
            date_str: Date in YYYY-MM-DD format.

        Returns:
            Dict with report_id, file_path, entry_count, status.
        """
        report = self.report.generate_daily_report(date_str)

        # Audit: report generated
        self.audit.log(AuditLogCreate(
            action=AuditAction.REPORT_GENERATED,
            actor="system",
            method="daily_report",
            status=AuditStatus.SUCCESS,
        ))

        import json
        entry_ids = json.loads(report.source_entry_ids_json)

        return {
            "report_id": report.id,
            "file_path": report.file_path,
            "entry_count": len(entry_ids),
            "date": date_str,
            "status": "ok",
        }

    def close(self) -> None:
        """Close database connection."""
        self.db.close()

    def _extractor_method(self) -> str:
        """Return a short audit method for the configured extractor."""
        if self.config.extractor_backend == "ollama":
            return "ollama"
        return "fake_extractor"

    def _extractor_model_name(self) -> str:
        """Return the audit model name for the configured extractor."""
        if self.config.extractor_backend == "ollama":
            return self.config.ollama_model
        return "FakeExtractor"

    def _extractor_prompt_version(self) -> str | None:
        """Return the prompt version for prompt-backed extractors."""
        prompt_version = getattr(self.extractor, "prompt_version", None)
        if isinstance(prompt_version, str) and prompt_version:
            return prompt_version
        return None

    @staticmethod
    def _summarize_error(exc: Exception, raw_text: str | None = None) -> str:
        """Summarize extraction errors for audit logs without storing raw input."""
        message = " ".join(str(exc).split())
        if raw_text:
            message = message.replace(raw_text, "[redacted input]")
        if len(message) > 240:
            return f"{message[:237]}..."
        return message


def check_extractor_backend(config: Config, http_client: OllamaClient | None = None) -> dict:
    """Check the configured extractor backend without creating database entries."""
    if config.extractor_backend == "fake":
        return {
            "ok": True,
            "backend": "fake",
            "message": "FakeExtractor is available.",
            "model_name": "FakeExtractor",
            "prompt_version": None,
        }

    if config.extractor_backend == "ollama":
        try:
            extractor = LocalLLMExtractor(
                base_url=config.ollama_base_url,
                model=config.ollama_model,
                timeout_seconds=config.llm_timeout_seconds,
                max_retries=config.llm_max_retries,
                retry_backoff_seconds=config.llm_retry_backoff_seconds,
                http_client=http_client,
            )
        except ValueError as exc:
            return {
                "ok": False,
                "backend": "ollama",
                "message": str(exc),
                "model_name": config.ollama_model or None,
                "prompt_version": None,
            }

        health = extractor.health_check()
        return {
            "ok": health.ok,
            "backend": "ollama",
            "message": health.message,
            "model_name": health.model_name,
            "prompt_version": health.prompt_version,
        }

    return {
        "ok": False,
        "backend": config.extractor_backend,
        "message": f"Invalid extractor backend '{config.extractor_backend}'. Use 'fake' or 'ollama'.",
        "model_name": None,
        "prompt_version": None,
    }
