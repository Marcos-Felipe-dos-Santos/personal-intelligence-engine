"""Repository for audit_logs table."""

from __future__ import annotations

from personal_intelligence_engine.app.domain.schemas import AuditLog
from personal_intelligence_engine.app.repositories.database import Database


class AuditRepository:
    """Persistence operations for audit logs."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def insert(self, log: AuditLog) -> None:
        """Insert a new audit log entry."""
        self._db.execute(
            """
            INSERT INTO audit_logs
                (id, raw_entry_id, action, actor, method, model_name, prompt_version,
                 input_hash, output_hash, status, error_message, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                log.id,
                log.raw_entry_id,
                log.action.value,
                log.actor,
                log.method,
                log.model_name,
                log.prompt_version,
                log.input_hash,
                log.output_hash,
                log.status.value,
                log.error_message,
                log.created_at,
            ),
        )
        self._db.commit()

    def get_by_raw_entry_id(self, raw_entry_id: str) -> list[AuditLog]:
        """Fetch all audit logs for a given raw entry."""
        rows = self._db.fetchall(
            "SELECT * FROM audit_logs WHERE raw_entry_id = ? ORDER BY created_at;",
            (raw_entry_id,),
        )
        return [AuditLog(**dict(row)) for row in rows]

    def get_all(self) -> list[AuditLog]:
        """Fetch all audit logs."""
        rows = self._db.fetchall("SELECT * FROM audit_logs ORDER BY created_at;")
        return [AuditLog(**dict(row)) for row in rows]
