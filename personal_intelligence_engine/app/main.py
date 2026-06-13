"""Main application orchestrator for PIE.

Wires together config, database, repositories, services, and adapters.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from personal_intelligence_engine.app.adapters.fake_extractor import FakeExtractor
from personal_intelligence_engine.app.adapters.local_llm_extractor import LocalLLMExtractor, OllamaClient
from personal_intelligence_engine.app.adapters.markdown_writer import MarkdownWriter
from personal_intelligence_engine.app.config import Config
from personal_intelligence_engine.app.domain.schemas import (
    AuditLogCreate,
    ExtractionResult,
    RawEntryCreate,
    StructuredEntryRevision,
)
from personal_intelligence_engine.app.domain.types import (
    LOW_CONFIDENCE_THRESHOLD,
    AuditAction,
    AuditStatus,
    EntryStatus,
    EntryType,
    ValidationStatus,
)
from personal_intelligence_engine.app.repositories.audit_repository import AuditRepository
from personal_intelligence_engine.app.repositories.database import Database
from personal_intelligence_engine.app.repositories.entries_repository import EntriesRepository
from personal_intelligence_engine.app.repositories.reports_repository import ReportsRepository
from personal_intelligence_engine.app.repositories.revisions_repository import RevisionsRepository
from personal_intelligence_engine.app.services.audit_service import AuditService
from personal_intelligence_engine.app.services.backup_export_service import BackupExportService
from personal_intelligence_engine.app.services.extraction_service import ExtractionService, Extractor
from personal_intelligence_engine.app.services.ingestion_service import IngestionService
from personal_intelligence_engine.app.services.markdown_service import MarkdownService
from personal_intelligence_engine.app.services.report_service import ReportService
from personal_intelligence_engine.app.services.reprocess_service import ReprocessService
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
        self.revisions_repo = RevisionsRepository(self.db)

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
        self.backup_export = BackupExportService(self.config, self.db)
        self.reprocess = ReprocessService(
            self.config,
            self.db,
            self.entries_repo,
            self.revisions_repo,
            self.extraction,
            self.audit,
            self.markdown,
            self.extractor,
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
                allow_remote=self.config.allow_remote_ollama,
            )

        raise ValueError(f"Invalid extractor backend '{self.config.extractor_backend}'. Use 'fake' or 'ollama'.")

    def add_entry(
        self,
        text: str,
        source: str = "cli",
        *,
        project: str | None = None,
        entry_type: str | None = None,
        tags: list[str] | None = None,
        auto_approve: bool = False,
    ) -> dict:
        """Full pipeline: ingest → extract → override → validate → markdown → audit.

        Args:
            text: Raw text content.
            source: Source identifier (default: "cli").
            project: Optional project name override.
            entry_type: Optional entry type override (must be a valid EntryType value).
            tags: Optional list of tags to merge with extracted tags.
            auto_approve: If True, skip needs_review even for low-confidence entries.

        Returns:
            Dict with entry_id, structured_entry_id, status, note_path.
        """
        if not text.strip():
            raise ValueError("Input text cannot be empty.")

        # 1. Ingest raw entry. This is committed before extraction so raw input
        # is preserved if a configured extractor fails.
        with self.db.transaction():
            raw = self.ingestion.ingest(RawEntryCreate(content=text, source=source))

            self.audit.log(
                AuditLogCreate(
                    raw_entry_id=raw.id,
                    action=AuditAction.ENTRY_CREATED,
                    actor="system",
                    method="cli",
                    input_hash=raw.content_hash,
                    status=AuditStatus.SUCCESS,
                )
            )

        # 2. Extract structured data
        try:
            extraction = self.extraction.extract(text)
        except Exception as exc:
            with self.db.transaction():
                self.entries_repo.update_raw_entry_status(
                    raw.id,
                    EntryStatus.ERROR.value,
                    raw.updated_at,
                )
                self.audit.log(
                    AuditLogCreate(
                        raw_entry_id=raw.id,
                        action=AuditAction.EXTRACTION_COMPLETED,
                        actor="system",
                        method=self._extractor_method(),
                        model_name=self._extractor_model_name(),
                        prompt_version=self._extractor_prompt_version(),
                        status=AuditStatus.ERROR,
                        error_message=self._summarize_error(exc, raw_text=text),
                    )
                )
            raise

        # 2b. Apply user-provided overrides (project, entry_type, tags)
        extraction = self._apply_overrides(
            extraction,
            project=project,
            entry_type=entry_type,
            tags=tags,
        )

        structured = None
        try:
            with self.db.transaction():
                # Audit: extraction completed
                self.audit.log(
                    AuditLogCreate(
                        raw_entry_id=raw.id,
                        action=AuditAction.EXTRACTION_COMPLETED,
                        actor="system",
                        method=self._extractor_method(),
                        model_name=self._extractor_model_name(),
                        prompt_version=self._extractor_prompt_version(),
                        status=AuditStatus.SUCCESS,
                    )
                )

                # 3. Validate and save structured entry
                structured = self.validation.validate_and_save(raw.id, extraction)

                # Audit: validation completed
                self.audit.log(
                    AuditLogCreate(
                        raw_entry_id=raw.id,
                        action=AuditAction.VALIDATION_COMPLETED,
                        actor="system",
                        status=AuditStatus.SUCCESS,
                    )
                )

                # 4. Handle low confidence
                if extraction.confidence < LOW_CONFIDENCE_THRESHOLD and not auto_approve:
                    self.entries_repo.update_raw_entry_status(
                        raw.id,
                        EntryStatus.NEEDS_REVIEW.value,
                        structured.updated_at,
                    )
                    self.audit.log(
                        AuditLogCreate(
                            raw_entry_id=raw.id,
                            action=AuditAction.LOW_CONFIDENCE,
                            actor="system",
                            status=AuditStatus.WARNING,
                            error_message=f"Confidence {extraction.confidence:.2f} below threshold {LOW_CONFIDENCE_THRESHOLD}",
                        )
                    )
                else:
                    self.entries_repo.update_raw_entry_status(
                        raw.id,
                        EntryStatus.PROCESSED.value,
                        structured.updated_at,
                    )
                    if structured.validation_status == ValidationStatus.NEEDS_REVIEW:
                        self.entries_repo.update_structured_entry(
                            structured_entry_id=structured.id,
                            entry_type=structured.entry_type.value,
                            project=structured.project,
                            summary=structured.summary,
                            confidence=structured.confidence,
                            structured_json=structured.structured_json,
                            validation_status=ValidationStatus.VALID.value,
                            updated_at=structured.updated_at,
                        )
                        structured = structured.model_copy(update={"validation_status": ValidationStatus.VALID})

                # 5. Generate Markdown note and record it in the same DB transaction.
                generated = self.markdown.generate_note(structured, text)

                # Audit: markdown generated
                self.audit.log(
                    AuditLogCreate(
                        raw_entry_id=raw.id,
                        action=AuditAction.MARKDOWN_GENERATED,
                        actor="system",
                        output_hash=generated.content_hash,
                        status=AuditStatus.SUCCESS,
                    )
                )
        except Exception:
            if structured is not None:
                note_path = self.config.notes_dir / f"{structured.id}.md"
                note_path.unlink(missing_ok=True)
            raise

        return {
            "entry_id": raw.id,
            "structured_entry_id": structured.id,
            "entry_type": structured.entry_type.value,
            "project": structured.project,
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
        self.audit.log(
            AuditLogCreate(
                action=AuditAction.REPORT_GENERATED,
                actor="system",
                method="daily_report",
                status=AuditStatus.SUCCESS,
            )
        )

        entry_ids = json.loads(report.source_entry_ids_json)

        return {
            "report_id": report.id,
            "file_path": report.file_path,
            "entry_count": len(entry_ids),
            "date": date_str,
            "status": "ok",
        }

    def generate_weekly_report(self, date_str: str) -> dict:
        """Generate a weekly report for the week containing the given date.

        Args:
            date_str: Date in YYYY-MM-DD format.

        Returns:
            Dict with report_id, file_path, entry_count, date_start, date_end, status.
        """
        report = self.report.generate_weekly_report(date_str)

        # Audit: report generated
        self.audit.log(
            AuditLogCreate(
                action=AuditAction.REPORT_GENERATED,
                actor="system",
                method="weekly_report",
                status=AuditStatus.SUCCESS,
            )
        )

        entry_ids = json.loads(report.source_entry_ids_json)

        return {
            "report_id": report.id,
            "file_path": report.file_path,
            "entry_count": len(entry_ids),
            "date_start": report.date_start,
            "date_end": report.date_end,
            "status": "ok",
        }

    def generate_project_report(self, project: str) -> dict:
        """Generate a project report for the given project name.

        Args:
            project: The name of the project.

        Returns:
            Dict with report_id, file_path, entry_count, project, status.
        """
        report = self.report.generate_project_report(project)

        # Audit: report generated
        self.audit.log(
            AuditLogCreate(
                action=AuditAction.REPORT_GENERATED,
                actor="system",
                method="project_report",
                status=AuditStatus.SUCCESS,
            )
        )

        entry_ids = json.loads(report.source_entry_ids_json)

        return {
            "report_id": report.id,
            "file_path": report.file_path,
            "entry_count": len(entry_ids),
            "project": project,
            "status": "ok",
        }

    def list_review_entries(self) -> list[dict]:
        """List entries currently waiting for human review."""
        return [self._format_review_entry(row) for row in self.entries_repo.list_entries_needing_review()]

    def get_review_entry(self, structured_entry_id: str) -> dict:
        """Get one entry currently waiting for human review."""
        row = self.entries_repo.get_review_entry(structured_entry_id)
        if row is None:
            raise ValueError(f"No review entry found for structured entry ID '{structured_entry_id}'.")
        return self._format_review_entry(row)

    def get_review_history(self, structured_entry_id: str) -> dict:
        """Get audit history for the raw entry linked to a structured entry."""
        row = self.entries_repo.get_review_candidate(structured_entry_id)
        if row is None:
            raise ValueError(f"No structured entry found for ID '{structured_entry_id}'.")

        logs = self.audit.get_logs_for_entry(row["raw_entry_id"])
        return {
            "structured_entry_id": row["structured_entry_id"],
            "raw_entry_id": row["raw_entry_id"],
            "events": [
                {
                    "created_at": log.created_at,
                    "action": log.action.value,
                    "status": log.status.value,
                    "actor": log.actor,
                    "method": log.method,
                    "model_name": log.model_name,
                    "prompt_version": log.prompt_version,
                    "error_message": log.error_message,
                }
                for log in logs
            ],
        }

    def approve_review_entry(self, structured_entry_id: str) -> dict:
        """Approve one entry currently waiting for human review."""
        row = self.entries_repo.get_review_candidate(structured_entry_id)
        if row is None:
            raise ValueError(f"No structured entry found for ID '{structured_entry_id}'.")

        if row["raw_status"] != "needs_review" and row["validation_status"] != "needs_review":
            return {
                "status": "already_processed",
                "structured_entry_id": row["structured_entry_id"],
                "raw_entry_id": row["raw_entry_id"],
                "message": "Entry is not in review; it is already processed or valid.",
            }

        updated_at = datetime.now(timezone.utc).isoformat()
        with self.db.transaction():
            self.entries_repo.mark_review_entry_approved(
                structured_entry_id=row["structured_entry_id"],
                raw_entry_id=row["raw_entry_id"],
                updated_at=updated_at,
            )
            self.audit.log(
                AuditLogCreate(
                    raw_entry_id=row["raw_entry_id"],
                    action=AuditAction.REVIEW_APPROVED,
                    actor="user",
                    method="human_review",
                    status=AuditStatus.SUCCESS,
                )
            )

        return {
            "status": "approved",
            "structured_entry_id": row["structured_entry_id"],
            "raw_entry_id": row["raw_entry_id"],
            "message": "Entry approved and removed from review queue.",
        }

    def reject_review_entry(self, structured_entry_id: str) -> dict:
        """Reject one entry currently waiting for human review."""
        row = self.entries_repo.get_review_candidate(structured_entry_id)
        if row is None:
            raise ValueError(f"No structured entry found for ID '{structured_entry_id}'.")

        if row["raw_status"] != "needs_review" and row["validation_status"] != "needs_review":
            return {
                "status": "already_processed",
                "structured_entry_id": row["structured_entry_id"],
                "raw_entry_id": row["raw_entry_id"],
                "message": "Entry is not in review; it is already processed, valid, or invalid.",
            }

        updated_at = datetime.now(timezone.utc).isoformat()
        with self.db.transaction():
            self.entries_repo.mark_review_entry_rejected(
                structured_entry_id=row["structured_entry_id"],
                raw_entry_id=row["raw_entry_id"],
                updated_at=updated_at,
            )
            self.audit.log(
                AuditLogCreate(
                    raw_entry_id=row["raw_entry_id"],
                    action=AuditAction.REVIEW_REJECTED,
                    actor="user",
                    method="human_review",
                    status=AuditStatus.SUCCESS,
                )
            )

        return {
            "status": "rejected",
            "structured_entry_id": row["structured_entry_id"],
            "raw_entry_id": row["raw_entry_id"],
            "message": "Entry rejected and removed from review queue.",
        }

    def edit_review_entry(
        self,
        structured_entry_id: str,
        *,
        summary: str | None = None,
        project: str | None = None,
        entry_type: str | None = None,
    ) -> dict:
        """Edit structured fields of an entry, preserving raw content and recording a revision.

        Args:
            structured_entry_id: ID of the structured entry to edit.
            summary: New summary text (optional).
            project: New project name (optional). Pass "" to clear to NULL.
            entry_type: New entry type value (optional).

        Returns:
            Dict with before/after snapshots, changed_fields, structured_entry_id, message.
        """
        if summary is None and project is None and entry_type is None:
            raise ValueError("Specify at least one field to edit (summary, project, entry_type).")

        # Validate field values before any DB access
        if summary is not None and not summary.strip():
            raise ValueError("summary must not be empty.")
        # Normalize empty project string to NULL
        if project is not None and not project.strip():
            project = None

        # get_entry_detail enforces deleted_at IS NULL on both tables, so it
        # naturally blocks edits on soft-deleted entries and provides raw_content.
        detail = self.entries_repo.get_entry_detail(structured_entry_id)
        if detail is None:
            raise ValueError(f"No structured entry found for ID '{structured_entry_id}'.")

        raw_content = detail["raw_content"]

        # Fetch as StructuredEntry for type-safe model_copy
        structured = self.entries_repo.get_structured_entry(structured_entry_id)
        if structured is None:  # pragma: no cover
            raise RuntimeError(f"Inconsistency: structured entry '{structured_entry_id}' missing after detail fetch.")

        # Parse current structured_json to keep embedded fields in sync
        try:
            payload = json.loads(structured.structured_json or "{}")
        except json.JSONDecodeError:
            payload = {}

        new_summary = summary if summary is not None else structured.summary
        new_project = project if project is not None else structured.project
        new_entry_type = EntryType(entry_type) if entry_type is not None else structured.entry_type

        payload["summary"] = new_summary
        payload["project"] = new_project
        payload["entry_type"] = new_entry_type.value
        new_structured_json = json.dumps(payload, ensure_ascii=False)

        updated_at = datetime.now(timezone.utc).isoformat()

        # Snapshots must not contain raw content (enforced by schema validator)
        before_dict = {
            "id": structured.id,
            "raw_entry_id": structured.raw_entry_id,
            "entry_type": structured.entry_type.value,
            "project": structured.project,
            "summary": structured.summary,
            "confidence": structured.confidence,
            "structured_json": structured.structured_json,
            "validation_status": structured.validation_status.value,
            "created_at": structured.created_at,
            "updated_at": structured.updated_at,
        }
        after_dict = {
            "id": structured.id,
            "raw_entry_id": structured.raw_entry_id,
            "entry_type": new_entry_type.value,
            "project": new_project,
            "summary": new_summary,
            "confidence": structured.confidence,
            "structured_json": new_structured_json,
            "validation_status": structured.validation_status.value,
            "created_at": structured.created_at,
            "updated_at": updated_at,
        }

        changed_fields = [
            key
            for key in ["entry_type", "project", "summary", "structured_json"]
            if before_dict[key] != after_dict[key]
        ]

        # Early return when nothing actually changed — avoids polluting audit history
        if not changed_fields:
            return {
                "structured_entry_id": structured_entry_id,
                "raw_entry_id": structured.raw_entry_id,
                "before": {
                    "summary": structured.summary,
                    "project": structured.project,
                    "entry_type": structured.entry_type.value,
                },
                "after": {
                    "summary": new_summary,
                    "project": new_project,
                    "entry_type": new_entry_type.value,
                },
                "changed_fields": [],
                "message": "No changes detected.",
            }

        updated_structured = structured.model_copy(
            update={
                "entry_type": new_entry_type,
                "project": new_project,
                "summary": new_summary,
                "structured_json": new_structured_json,
                "updated_at": updated_at,
            }
        )

        with self.db.transaction():
            self.entries_repo.update_structured_entry(
                structured_entry_id=structured_entry_id,
                entry_type=new_entry_type.value,
                project=new_project,
                summary=new_summary,
                confidence=structured.confidence,
                structured_json=new_structured_json,
                validation_status=structured.validation_status.value,
                updated_at=updated_at,
            )
            self.revisions_repo.create_revision(
                StructuredEntryRevision(
                    structured_entry_id=structured_entry_id,
                    raw_entry_id=structured.raw_entry_id,
                    before_json=json.dumps(before_dict, ensure_ascii=False),
                    after_json=json.dumps(after_dict, ensure_ascii=False),
                    changed_fields_json=json.dumps(changed_fields, ensure_ascii=False),
                    reason="review_edit",
                    actor="user",
                )
            )
            self.audit.log(
                AuditLogCreate(
                    raw_entry_id=structured.raw_entry_id,
                    action=AuditAction.REVIEW_EDITED,
                    actor="user",
                    method="human_review",
                    status=AuditStatus.SUCCESS,
                )
            )

        # Markdown is regenerated outside the transaction so a write failure
        # does not roll back the DB update. The DB is the source of truth;
        # the .md is a projection that can be rebuilt. (Same pattern as ReprocessService.)
        self.markdown.generate_note(updated_structured, raw_content)

        return {
            "structured_entry_id": structured_entry_id,
            "raw_entry_id": structured.raw_entry_id,
            "before": {
                "summary": structured.summary,
                "project": structured.project,
                "entry_type": structured.entry_type.value,
            },
            "after": {
                "summary": new_summary,
                "project": new_project,
                "entry_type": new_entry_type.value,
            },
            "changed_fields": changed_fields,
            "message": f"Entry updated. {len(changed_fields)} field(s) changed.",
        }

    # --- Entries List / Show / Search ---

    def list_entries(
        self,
        *,
        entry_type: str | None = None,
        project: str | None = None,
        validation_status: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """List structured entries with optional filters."""
        rows = self.entries_repo.list_entries(
            entry_type=entry_type,
            project=project,
            validation_status=validation_status,
            limit=limit,
        )
        return [self._format_entry_row(row) for row in rows]

    def get_entry_detail(self, structured_entry_id: str) -> dict:
        """Get full detail for one structured entry."""
        row = self.entries_repo.get_entry_detail(structured_entry_id)
        if row is None:
            raise ValueError(f"No entry found for structured entry ID '{structured_entry_id}'.")
        result = self._format_entry_row(row)
        result["updated_at"] = row["updated_at"]
        result["raw_content"] = row["raw_content"]
        return result

    def search_entries(
        self,
        query: str,
        *,
        entry_type: str | None = None,
        project: str | None = None,
        validation_status: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Search entries by text across raw content, summary, project, and structured_json."""
        rows = self.entries_repo.search_entries(
            query,
            entry_type=entry_type,
            project=project,
            validation_status=validation_status,
            limit=limit,
        )
        results = []
        for row in rows:
            entry = self._format_entry_row(row)
            entry["raw_content"] = row["raw_content"]
            entry["match_source"] = row.get("match_source", "unknown")
            results.append(entry)
        return results

    # --- Delete / Restore / Purge ---

    def delete_entry(self, structured_entry_id: str) -> dict:
        """Soft-delete an entry by structured entry ID."""
        deleted_at = datetime.now(timezone.utc).isoformat()
        with self.db.transaction():
            raw_entry_id = self.entries_repo.soft_delete_entry(structured_entry_id, deleted_at)
            if raw_entry_id is None:
                raise ValueError(f"No active entry found for structured entry ID '{structured_entry_id}'.")
            self.audit.log(
                AuditLogCreate(
                    raw_entry_id=raw_entry_id,
                    action=AuditAction.ENTRY_DELETED,
                    actor="user",
                    method="cli",
                    status=AuditStatus.SUCCESS,
                )
            )
        return {
            "status": "deleted",
            "structured_entry_id": structured_entry_id,
            "raw_entry_id": raw_entry_id,
            "message": "Entry soft-deleted. Use 'pie entries restore' to undo.",
        }

    def restore_entry(self, structured_entry_id: str) -> dict:
        """Restore a soft-deleted entry by structured entry ID."""
        with self.db.transaction():
            raw_entry_id = self.entries_repo.restore_entry(structured_entry_id)
            if raw_entry_id is None:
                raise ValueError(f"No deleted entry found for structured entry ID '{structured_entry_id}'.")
            self.audit.log(
                AuditLogCreate(
                    raw_entry_id=raw_entry_id,
                    action=AuditAction.ENTRY_RESTORED,
                    actor="user",
                    method="cli",
                    status=AuditStatus.SUCCESS,
                )
            )
        return {
            "status": "restored",
            "structured_entry_id": structured_entry_id,
            "raw_entry_id": raw_entry_id,
            "message": "Entry restored successfully.",
        }

    def purge_deleted(self, days_old: int = 30) -> dict:
        """Permanently delete entries that were soft-deleted more than N days ago."""
        from datetime import timedelta

        cutoff = (datetime.now(timezone.utc) - timedelta(days=days_old)).isoformat()
        with self.db.transaction():
            count, failed_files = self.entries_repo.purge_deleted_entries(cutoff)
            self.audit.log(
                AuditLogCreate(
                    action=AuditAction.ENTRIES_PURGED,
                    actor="user",
                    method="cli",
                    status=AuditStatus.SUCCESS,
                    error_message=f"Purged {count} entries older than {days_old} days.",
                )
            )
        return {
            "status": "purged",
            "count": count,
            "days_old": days_old,
            "message": f"Permanently deleted {count} entries soft-deleted more than {days_old} days ago.",
            "unlink_failures": failed_files,
        }

    def close(self) -> None:
        """Close database connection."""
        self.db.close()

    def create_backup(self) -> dict:
        """Create a secure backup of the SQLite database."""
        path = self.backup_export.create_backup()
        return {
            "backup_path": str(path),
            "status": "ok",
        }

    def export_json(self) -> dict:
        """Export core database tables to a portable JSON format."""
        path = self.backup_export.export_json()
        return {
            "export_path": str(path),
            "status": "ok",
        }

    def export_markdown(self) -> dict:
        """Export structured entries grouped by entry_type as Markdown."""
        path = self.backup_export.export_markdown()
        return {
            "export_path": str(path),
            "status": "ok",
        }

    def reprocess_entry(self, structured_entry_id: str, dry_run: bool = True) -> dict:
        """Reprocess a single structured entry by re-running extraction."""
        return self.reprocess.reprocess_entry(structured_entry_id, dry_run=dry_run)

    def reprocess_entries_by_status(self, status: str, limit: int = 20, dry_run: bool = True) -> dict:
        """Reprocess structured entries filtered by status."""
        ids = self.entries_repo.list_entries_by_status(status, limit=limit)
        applied = []
        failed = []
        for structured_entry_id in ids:
            try:
                applied.append(self.reprocess.reprocess_entry(structured_entry_id, dry_run=dry_run))
            except Exception as exc:
                failed.append(
                    {
                        "structured_entry_id": structured_entry_id,
                        "error": self._summarize_error(exc),
                    }
                )
        return {
            "selected_ids": ids,
            "applied": applied,
            "failed": failed,
            "dry_run": dry_run,
        }

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
    def _apply_overrides(
        extraction: ExtractionResult,
        *,
        project: str | None = None,
        entry_type: str | None = None,
        tags: list[str] | None = None,
    ) -> ExtractionResult:
        """Apply user-provided overrides to an extraction result.

        - ``project`` replaces the extracted project (if provided).
        - ``entry_type`` replaces the extracted entry type (if provided).
        - ``tags`` are merged with extracted tags, preserving order and
          removing duplicates.
        - Confidence is **never** changed.

        Args:
            extraction: The original extraction result.
            project: Optional project name override.
            entry_type: Optional entry type name (must be a valid EntryType value).
            tags: Optional user-supplied tags to merge.

        Returns:
            A new ExtractionResult with overrides applied.
        """
        updates: dict = {}

        if project is not None:
            updates["project"] = project

        if entry_type is not None:
            updates["entry_type"] = EntryType(entry_type)

        if tags:
            seen: set[str] = set()
            merged: list[str] = []
            for tag in list(extraction.tags) + list(tags):
                normalized = tag.strip().lower()
                if normalized and normalized not in seen:
                    seen.add(normalized)
                    merged.append(normalized)
            updates["tags"] = merged

        if not updates:
            return extraction

        return extraction.model_copy(update=updates)

    @staticmethod
    def _format_review_entry(row: dict) -> dict:
        """Convert a review query row into CLI-friendly data."""
        tags = []
        try:
            payload = json.loads(row.get("structured_json") or "{}")
        except json.JSONDecodeError:
            payload = {}
        if isinstance(payload.get("tags"), list):
            tags = [str(tag) for tag in payload["tags"]]

        return {
            "structured_entry_id": row["structured_entry_id"],
            "raw_entry_id": row["raw_entry_id"],
            "entry_type": row["entry_type"],
            "project": row["project"],
            "summary": row["summary"],
            "confidence": row["confidence"],
            "tags": tags,
            "validation_status": row["validation_status"],
            "raw_content": row["raw_content"],
            "created_at": row["created_at"],
        }

    @staticmethod
    def _format_entry_row(row: dict) -> dict:
        """Convert an entries query row into CLI-friendly data."""
        tags = []
        try:
            payload = json.loads(row.get("structured_json") or "{}")
        except json.JSONDecodeError:
            payload = {}
        if isinstance(payload.get("tags"), list):
            tags = [str(tag) for tag in payload["tags"]]

        return {
            "structured_entry_id": row["structured_entry_id"],
            "raw_entry_id": row["raw_entry_id"],
            "entry_type": row["entry_type"],
            "project": row["project"],
            "summary": row["summary"],
            "confidence": row["confidence"],
            "tags": tags,
            "validation_status": row["validation_status"],
            "structured_json": row.get("structured_json", "{}"),
            "created_at": row["created_at"],
        }

    @staticmethod
    def _summarize_error(exc: Exception, raw_text: str | None = None) -> str:
        """Summarize extraction errors for audit logs without storing raw input."""
        message = " ".join(str(exc).split())
        if raw_text:
            message = message.replace(raw_text, "[redacted input]")
        if len(message) > 240:
            return f"{message[:237]}..."
        return message


def check_extractor_backend(
    config: Config,
    http_client: OllamaClient | None = None,
    deep: bool = False,
) -> dict:
    """Check the configured extractor backend without creating database entries."""
    if config.extractor_backend == "fake":
        return {
            "ok": True,
            "backend": "fake",
            "message": "FakeExtractor is available.",
            "model_name": "FakeExtractor",
            "prompt_version": None,
            "warnings": [],
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
                allow_remote=config.allow_remote_ollama,
            )
        except ValueError as exc:
            return {
                "ok": False,
                "backend": "ollama",
                "message": str(exc),
                "model_name": config.ollama_model or None,
                "prompt_version": None,
                "warnings": [],
            }

        health = extractor.deep_health_check() if deep else extractor.health_check()
        return {
            "ok": health.ok,
            "backend": "ollama",
            "message": health.message,
            "model_name": health.model_name,
            "prompt_version": health.prompt_version,
            "warnings": health.warnings,
        }

    return {
        "ok": False,
        "backend": config.extractor_backend,
        "message": f"Invalid extractor backend '{config.extractor_backend}'. Use 'fake' or 'ollama'.",
        "model_name": None,
        "prompt_version": None,
        "warnings": [],
    }
