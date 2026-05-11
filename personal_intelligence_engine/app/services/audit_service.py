"""Audit service — records pipeline events in the audit log."""

from __future__ import annotations

from personal_intelligence_engine.app.domain.schemas import AuditLog, AuditLogCreate
from personal_intelligence_engine.app.repositories.audit_repository import AuditRepository


class AuditService:
    """Records audit events for traceability."""

    def __init__(self, audit_repo: AuditRepository) -> None:
        self._audit_repo = audit_repo

    def log(self, create: AuditLogCreate) -> AuditLog:
        """Create and persist an audit log entry.

        Args:
            create: Input data for the audit log.

        Returns:
            The persisted AuditLog.
        """
        audit = AuditLog(
            raw_entry_id=create.raw_entry_id,
            action=create.action,
            actor=create.actor,
            method=create.method,
            model_name=create.model_name,
            prompt_version=create.prompt_version,
            input_hash=create.input_hash,
            output_hash=create.output_hash,
            status=create.status,
            error_message=create.error_message,
        )
        self._audit_repo.insert(audit)
        return audit

    def get_logs_for_entry(self, raw_entry_id: str) -> list[AuditLog]:
        """Fetch all audit logs for a raw entry."""
        return self._audit_repo.get_by_raw_entry_id(raw_entry_id)
