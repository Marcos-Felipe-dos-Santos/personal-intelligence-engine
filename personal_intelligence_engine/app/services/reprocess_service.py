"""Reprocess service — reprocesses existing raw entries to update structured data."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from personal_intelligence_engine.app.config import Config
from personal_intelligence_engine.app.domain.schemas import (
    AuditLogCreate,
    StructuredEntryRevision,
)
from personal_intelligence_engine.app.domain.types import AuditAction, AuditStatus
from personal_intelligence_engine.app.repositories.database import Database
from personal_intelligence_engine.app.repositories.entries_repository import EntriesRepository
from personal_intelligence_engine.app.repositories.revisions_repository import RevisionsRepository
from personal_intelligence_engine.app.services.audit_service import AuditService
from personal_intelligence_engine.app.services.extraction_service import ExtractionService, Extractor


class ReprocessService:
    """Orchestrates safe reprocessing of stored personal knowledge entries."""

    def __init__(
        self,
        config: Config,
        db: Database,
        entries_repo: EntriesRepository,
        revisions_repo: RevisionsRepository,
        extraction: ExtractionService,
        audit: AuditService,
        extractor: Extractor,
    ) -> None:
        self.config = config
        self.db = db
        self.entries_repo = entries_repo
        self.revisions_repo = revisions_repo
        self.extraction = extraction
        self.audit = audit
        self.extractor = extractor

    def reprocess_entry(self, structured_entry_id: str, dry_run: bool = True) -> dict[str, Any]:
        """Reprocess a single structured entry by re-running extraction and validation.

        Args:
            structured_entry_id: The ID of the structured entry to reprocess.
            dry_run: If True, do not apply changes or write to database/logs.

        Returns:
            A dict containing comparison information, IDs, and change status.
        """
        structured = self.entries_repo.get_entry_detail(structured_entry_id)
        if not structured:
            raise ValueError(f"No entry found for structured entry ID '{structured_entry_id}'.")

        raw_entry_id = structured["raw_entry_id"]
        raw_content = structured["raw_content"]

        # Re-run extraction
        extraction = self.extraction.extract(raw_content)

        # Validate result
        validation_status = "valid"
        if extraction.confidence < 0.70:
            validation_status = "needs_review"

        # Determine old tags
        try:
            old_payload = json.loads(structured.get("structured_json") or "{}")
        except (json.JSONDecodeError, TypeError):
            old_payload = {}
        old_tags = old_payload.get("tags") or []

        new_payload_str = extraction.to_structured_json()
        new_tags = extraction.tags

        comparison = {
            "entry_type": {"before": structured["entry_type"], "after": extraction.entry_type.value},
            "project": {"before": structured["project"], "after": extraction.project},
            "summary": {"before": structured["summary"], "after": extraction.summary},
            "confidence": {"before": structured["confidence"], "after": extraction.confidence},
            "validation_status": {"before": structured["validation_status"], "after": validation_status},
            "tags": {"before": old_tags, "after": new_tags},
        }

        has_changes = False
        for val in comparison.values():
            if val["before"] != val["after"]:
                has_changes = True

        if dry_run:
            return {
                "structured_entry_id": structured_entry_id,
                "raw_entry_id": raw_entry_id,
                "comparison": comparison,
                "has_changes": has_changes,
                "dry_run": True,
            }

        # Apply changes
        before_dict = {
            "id": structured["structured_entry_id"],
            "raw_entry_id": raw_entry_id,
            "entry_type": structured["entry_type"],
            "project": structured["project"],
            "summary": structured["summary"],
            "confidence": structured["confidence"],
            "structured_json": structured["structured_json"],
            "validation_status": structured["validation_status"],
            "created_at": structured["created_at"],
            "updated_at": structured.get("updated_at") or structured["created_at"],
        }

        updated_at = datetime.now(timezone.utc).isoformat()

        after_dict = {
            "id": structured["structured_entry_id"],
            "raw_entry_id": raw_entry_id,
            "entry_type": extraction.entry_type.value,
            "project": extraction.project,
            "summary": extraction.summary,
            "confidence": extraction.confidence,
            "structured_json": new_payload_str,
            "validation_status": validation_status,
            "created_at": structured["created_at"],
            "updated_at": updated_at,
        }

        # Identify changed fields
        changed_fields = []
        for key in ["entry_type", "project", "summary", "confidence", "structured_json", "validation_status"]:
            if before_dict[key] != after_dict[key]:
                changed_fields.append(key)

        with self.db.transaction():
            # Create revision record
            revision = StructuredEntryRevision(
                id=str(uuid.uuid4()),
                structured_entry_id=structured_entry_id,
                raw_entry_id=raw_entry_id,
                before_json=json.dumps(before_dict, ensure_ascii=False),
                after_json=json.dumps(after_dict, ensure_ascii=False),
                changed_fields_json=json.dumps(changed_fields, ensure_ascii=False),
                reason="reprocess",
                actor="system",
            )
            self.revisions_repo.create_revision(revision)

            # Update structured entry in DB
            self.entries_repo.update_structured_entry(
                structured_entry_id=structured_entry_id,
                entry_type=extraction.entry_type.value,
                project=extraction.project,
                summary=extraction.summary,
                confidence=extraction.confidence,
                structured_json=new_payload_str,
                validation_status=validation_status,
                updated_at=updated_at,
            )

            # Update raw entry status
            raw_status = "processed"
            if extraction.confidence < 0.70:
                raw_status = "needs_review"
            self.entries_repo.update_raw_entry_status(raw_entry_id, raw_status, updated_at)

            # Log audit logs
            method_name = self._extractor_method()
            model_name = self._extractor_model_name()
            prompt_version = self._extractor_prompt_version()

            self.audit.log(AuditLogCreate(
                raw_entry_id=raw_entry_id,
                action=AuditAction.EXTRACTION_COMPLETED,
                actor="system",
                method=f"reprocess:{method_name}",
                model_name=model_name,
                prompt_version=prompt_version,
                status=AuditStatus.SUCCESS,
            ))

            self.audit.log(AuditLogCreate(
                raw_entry_id=raw_entry_id,
                action=AuditAction.VALIDATION_COMPLETED,
                actor="system",
                method="reprocess",
                status=AuditStatus.SUCCESS,
            ))

            if extraction.confidence < 0.70:
                self.audit.log(AuditLogCreate(
                    raw_entry_id=raw_entry_id,
                    action=AuditAction.LOW_CONFIDENCE,
                    actor="system",
                    status=AuditStatus.WARNING,
                    error_message=f"Confidence {extraction.confidence:.2f} below threshold 0.70",
                ))

        return {
            "structured_entry_id": structured_entry_id,
            "raw_entry_id": raw_entry_id,
            "comparison": comparison,
            "has_changes": has_changes,
            "dry_run": False,
        }

    def _extractor_method(self) -> str:
        if self.config.extractor_backend == "ollama":
            return "ollama"
        return "fake_extractor"

    def _extractor_model_name(self) -> str:
        if self.config.extractor_backend == "ollama":
            return self.config.ollama_model
        return "FakeExtractor"

    def _extractor_prompt_version(self) -> str | None:
        prompt_version = getattr(self.extractor, "prompt_version", None)
        if isinstance(prompt_version, str) and prompt_version:
            return prompt_version
        return None
