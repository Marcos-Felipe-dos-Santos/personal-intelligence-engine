"""Repository for structured_entry_revisions table."""

from __future__ import annotations

from personal_intelligence_engine.app.domain.schemas import StructuredEntryRevision
from personal_intelligence_engine.app.repositories.database import Database


class RevisionsRepository:
    """Persistence operations for structured entry revisions."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def create_revision(self, revision: StructuredEntryRevision) -> None:
        """Insert a structured entry revision snapshot."""
        self._db.execute(
            """
            INSERT INTO structured_entry_revisions
                (id, structured_entry_id, raw_entry_id, before_json, after_json,
                 changed_fields_json, reason, actor, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                revision.id,
                revision.structured_entry_id,
                revision.raw_entry_id,
                revision.before_json,
                revision.after_json,
                revision.changed_fields_json,
                revision.reason,
                revision.actor,
                revision.created_at,
            ),
        )
        self._db.commit()

    def list_revisions_for_structured_entry(
        self,
        structured_entry_id: str,
    ) -> list[StructuredEntryRevision]:
        """Fetch revisions for a structured entry in chronological order."""
        rows = self._db.fetchall(
            """
            SELECT *
            FROM structured_entry_revisions
            WHERE structured_entry_id = ?
            ORDER BY created_at;
            """,
            (structured_entry_id,),
        )
        return [StructuredEntryRevision(**dict(row)) for row in rows]
