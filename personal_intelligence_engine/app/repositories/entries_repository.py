"""Repository for raw_entries and structured_entries tables."""

from __future__ import annotations

from personal_intelligence_engine.app.domain.schemas import (
    GeneratedFile,
    RawEntry,
    StructuredEntry,
)
from personal_intelligence_engine.app.repositories.database import Database


class EntriesRepository:
    """Persistence operations for entries."""

    def __init__(self, db: Database) -> None:
        self._db = db

    # --- Raw Entries ---

    def insert_raw_entry(self, entry: RawEntry) -> None:
        """Insert a new raw entry."""
        self._db.execute(
            """
            INSERT INTO raw_entries (id, content, source, status, created_at, updated_at, metadata_json, content_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                entry.id,
                entry.content,
                entry.source,
                entry.status.value,
                entry.created_at,
                entry.updated_at,
                entry.metadata_json,
                entry.content_hash,
            ),
        )
        self._db.commit()

    def get_raw_entry(self, entry_id: str) -> RawEntry | None:
        """Fetch a raw entry by ID."""
        row = self._db.fetchone("SELECT * FROM raw_entries WHERE id = ?;", (entry_id,))
        if row is None:
            return None
        return RawEntry(**dict(row))

    def update_raw_entry_status(self, entry_id: str, status: str, updated_at: str) -> None:
        """Update the status of a raw entry."""
        self._db.execute(
            "UPDATE raw_entries SET status = ?, updated_at = ? WHERE id = ?;",
            (status, updated_at, entry_id),
        )
        self._db.commit()

    # --- Structured Entries ---

    def insert_structured_entry(self, entry: StructuredEntry) -> None:
        """Insert a new structured entry."""
        self._db.execute(
            """
            INSERT INTO structured_entries
                (id, raw_entry_id, entry_type, project, summary, confidence,
                 structured_json, validation_status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                entry.id,
                entry.raw_entry_id,
                entry.entry_type.value,
                entry.project,
                entry.summary,
                entry.confidence,
                entry.structured_json,
                entry.validation_status.value,
                entry.created_at,
                entry.updated_at,
            ),
        )
        self._db.commit()

    def get_structured_entry(self, entry_id: str) -> StructuredEntry | None:
        """Fetch a structured entry by ID."""
        row = self._db.fetchone("SELECT * FROM structured_entries WHERE id = ?;", (entry_id,))
        if row is None:
            return None
        return StructuredEntry(**dict(row))

    def get_structured_entry_by_raw_id(self, raw_entry_id: str) -> StructuredEntry | None:
        """Fetch a structured entry by its raw_entry_id."""
        row = self._db.fetchone(
            "SELECT * FROM structured_entries WHERE raw_entry_id = ?;",
            (raw_entry_id,),
        )
        if row is None:
            return None
        return StructuredEntry(**dict(row))

    def get_structured_entries_by_date(self, date_str: str) -> list[StructuredEntry]:
        """Fetch all non-deleted structured entries created on a given date (YYYY-MM-DD)."""
        rows = self._db.fetchall(
            "SELECT * FROM structured_entries WHERE created_at LIKE ? AND deleted_at IS NULL ORDER BY created_at;",
            (f"{date_str}%",),
        )
        return [StructuredEntry(**dict(row)) for row in rows]

    def list_entries_needing_review(self) -> list[dict]:
        """Fetch non-deleted structured entries whose raw entry is marked as needs_review."""
        rows = self._db.fetchall(
            """
            SELECT
                s.id AS structured_entry_id,
                s.raw_entry_id AS raw_entry_id,
                s.entry_type AS entry_type,
                s.project AS project,
                s.summary AS summary,
                s.confidence AS confidence,
                s.structured_json AS structured_json,
                s.validation_status AS validation_status,
                s.created_at AS created_at,
                r.content AS raw_content,
                r.status AS raw_status
            FROM structured_entries s
            JOIN raw_entries r ON r.id = s.raw_entry_id
            WHERE r.status = 'needs_review'
              AND s.deleted_at IS NULL
              AND r.deleted_at IS NULL
            ORDER BY s.created_at;
            """
        )
        return [dict(row) for row in rows]

    def get_review_entry(self, structured_entry_id: str) -> dict | None:
        """Fetch one structured entry in review by structured entry ID."""
        row = self._db.fetchone(
            """
            SELECT
                s.id AS structured_entry_id,
                s.raw_entry_id AS raw_entry_id,
                s.entry_type AS entry_type,
                s.project AS project,
                s.summary AS summary,
                s.confidence AS confidence,
                s.structured_json AS structured_json,
                s.validation_status AS validation_status,
                s.created_at AS created_at,
                r.content AS raw_content,
                r.status AS raw_status
            FROM structured_entries s
            JOIN raw_entries r ON r.id = s.raw_entry_id
            WHERE s.id = ? AND r.status = 'needs_review'
              AND s.deleted_at IS NULL
              AND r.deleted_at IS NULL;
            """,
            (structured_entry_id,),
        )
        if row is None:
            return None
        return dict(row)

    def get_review_candidate(self, structured_entry_id: str) -> dict | None:
        """Fetch one structured entry with raw status for review decisions."""
        row = self._db.fetchone(
            """
            SELECT
                s.id AS structured_entry_id,
                s.raw_entry_id AS raw_entry_id,
                s.entry_type AS entry_type,
                s.project AS project,
                s.summary AS summary,
                s.confidence AS confidence,
                s.structured_json AS structured_json,
                s.validation_status AS validation_status,
                s.created_at AS created_at,
                s.updated_at AS updated_at,
                r.content AS raw_content,
                r.status AS raw_status
            FROM structured_entries s
            JOIN raw_entries r ON r.id = s.raw_entry_id
            WHERE s.id = ?;
            """,
            (structured_entry_id,),
        )
        if row is None:
            return None
        return dict(row)

    def mark_review_entry_approved(
        self,
        *,
        structured_entry_id: str,
        raw_entry_id: str,
        updated_at: str,
    ) -> None:
        """Mark a review entry as processed and valid."""
        self._db.execute(
            "UPDATE raw_entries SET status = ?, updated_at = ? WHERE id = ?;",
            ("processed", updated_at, raw_entry_id),
        )
        self._db.execute(
            "UPDATE structured_entries SET validation_status = ?, updated_at = ? WHERE id = ?;",
            ("valid", updated_at, structured_entry_id),
        )
        self._db.commit()

    def mark_review_entry_rejected(
        self,
        *,
        structured_entry_id: str,
        raw_entry_id: str,
        updated_at: str,
    ) -> None:
        """Mark a review entry as processed and invalid."""
        self._db.execute(
            "UPDATE raw_entries SET status = ?, updated_at = ? WHERE id = ?;",
            ("processed", updated_at, raw_entry_id),
        )
        self._db.execute(
            "UPDATE structured_entries SET validation_status = ?, updated_at = ? WHERE id = ?;",
            ("invalid", updated_at, structured_entry_id),
        )
        self._db.commit()

    # --- Entries List / Show / Search ---

    def list_entries(
        self,
        *,
        entry_type: str | None = None,
        project: str | None = None,
        validation_status: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """List non-deleted structured entries with optional filters."""
        clauses: list[str] = ["s.deleted_at IS NULL", "r.deleted_at IS NULL"]
        params: list[str | int] = []

        if entry_type is not None:
            clauses.append("s.entry_type = ?")
            params.append(entry_type)
        if project is not None:
            clauses.append("s.project = ?")
            params.append(project)
        if validation_status is not None:
            clauses.append("s.validation_status = ?")
            params.append(validation_status)

        where = "WHERE " + " AND ".join(clauses)

        sql = f"""
            SELECT
                s.id              AS structured_entry_id,
                s.raw_entry_id    AS raw_entry_id,
                s.entry_type      AS entry_type,
                s.project         AS project,
                s.summary         AS summary,
                s.confidence      AS confidence,
                s.structured_json AS structured_json,
                s.validation_status AS validation_status,
                s.created_at      AS created_at
            FROM structured_entries s
            JOIN raw_entries r ON r.id = s.raw_entry_id
            {where}
            ORDER BY s.created_at DESC
            LIMIT ?;
        """
        params.append(limit)
        rows = self._db.fetchall(sql, tuple(params))
        return [dict(row) for row in rows]

    def get_entry_detail(self, structured_entry_id: str) -> dict | None:
        """Fetch full detail for one structured entry."""
        row = self._db.fetchone(
            """
            SELECT
                s.id              AS structured_entry_id,
                s.raw_entry_id    AS raw_entry_id,
                s.entry_type      AS entry_type,
                s.project         AS project,
                s.summary         AS summary,
                s.confidence      AS confidence,
                s.structured_json AS structured_json,
                s.validation_status AS validation_status,
                s.created_at      AS created_at,
                s.updated_at      AS updated_at,
                r.content         AS raw_content
            FROM structured_entries s
            JOIN raw_entries r ON r.id = s.raw_entry_id
            WHERE s.id = ?
              AND s.deleted_at IS NULL
              AND r.deleted_at IS NULL;
            """,
            (structured_entry_id,),
        )
        if row is None:
            return None
        return dict(row)

    def search_entries(
        self,
        query: str,
        *,
        entry_type: str | None = None,
        project: str | None = None,
        validation_status: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Search non-deleted entries by text across raw content, summary, project, and structured_json."""
        like_pattern = f"%{query}%"
        clauses = [
            "(r.content LIKE ? OR s.summary LIKE ? OR s.project LIKE ? OR s.structured_json LIKE ?)",
            "s.deleted_at IS NULL",
            "r.deleted_at IS NULL",
        ]
        params: list[str | int] = [like_pattern, like_pattern, like_pattern, like_pattern]

        if entry_type is not None:
            clauses.append("s.entry_type = ?")
            params.append(entry_type)
        if project is not None:
            clauses.append("s.project = ?")
            params.append(project)
        if validation_status is not None:
            clauses.append("s.validation_status = ?")
            params.append(validation_status)

        where = "WHERE " + " AND ".join(clauses)

        sql = f"""
            SELECT
                s.id              AS structured_entry_id,
                s.raw_entry_id    AS raw_entry_id,
                s.entry_type      AS entry_type,
                s.project         AS project,
                s.summary         AS summary,
                s.confidence      AS confidence,
                s.structured_json AS structured_json,
                s.validation_status AS validation_status,
                s.created_at      AS created_at,
                r.content         AS raw_content,
                CASE
                    WHEN s.summary LIKE ? THEN 'summary'
                    WHEN s.project LIKE ? THEN 'project'
                    WHEN s.structured_json LIKE ? THEN 'structured_json'
                    WHEN r.content LIKE ? THEN 'raw_content'
                    ELSE 'unknown'
                END AS match_source
            FROM structured_entries s
            JOIN raw_entries r ON r.id = s.raw_entry_id
            {where}
            ORDER BY s.created_at DESC
            LIMIT ?;
        """
        params_full = [like_pattern, like_pattern, like_pattern, like_pattern] + params + [limit]
        rows = self._db.fetchall(sql, tuple(params_full))
        return [dict(row) for row in rows]

    # --- Generated Files ---

    def insert_generated_file(self, gf: GeneratedFile) -> None:
        """Record a generated file."""
        self._db.execute(
            """
            INSERT INTO generated_files (id, raw_entry_id, file_type, path, content_hash, created_at)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (gf.id, gf.raw_entry_id, gf.file_type, gf.path, gf.content_hash, gf.created_at),
        )
        self._db.commit()

    def update_structured_entry(
        self,
        *,
        structured_entry_id: str,
        entry_type: str,
        project: str | None,
        summary: str,
        confidence: float,
        structured_json: str,
        validation_status: str,
        updated_at: str,
    ) -> None:
        """Update a structured entry with new extraction results."""
        self._db.execute(
            """
            UPDATE structured_entries
            SET entry_type = ?,
                project = ?,
                summary = ?,
                confidence = ?,
                structured_json = ?,
                validation_status = ?,
                updated_at = ?
            WHERE id = ?;
            """,
            (
                entry_type,
                project,
                summary,
                confidence,
                structured_json,
                validation_status,
                updated_at,
                structured_entry_id,
            ),
        )
        self._db.commit()

    def list_entries_by_status(self, status: str, limit: int) -> list[str]:
        """Fetch non-deleted structured entry IDs where validation_status or raw status matches."""
        rows = self._db.fetchall(
            """
            SELECT s.id
            FROM structured_entries s
            JOIN raw_entries r ON r.id = s.raw_entry_id
            WHERE (s.validation_status = ? OR r.status = ?)
              AND s.deleted_at IS NULL
              AND r.deleted_at IS NULL
            ORDER BY s.created_at DESC
            LIMIT ?;
            """,
            (status, status, limit),
        )
        return [row["id"] for row in rows]

    def get_structured_entries_by_project(self, project: str) -> list[StructuredEntry]:
        """Fetch all non-deleted structured entries for a specific project."""
        rows = self._db.fetchall(
            "SELECT * FROM structured_entries WHERE project = ? AND deleted_at IS NULL ORDER BY created_at DESC;",
            (project,),
        )
        return [StructuredEntry(**dict(row)) for row in rows]

    # --- Soft Delete / Restore / Purge ---

    def soft_delete_entry(self, structured_entry_id: str, deleted_at: str) -> str | None:
        """Soft-delete a structured entry and its linked raw entry.

        Returns the raw_entry_id if the entry was found, otherwise None.
        """
        row = self._db.fetchone(
            "SELECT raw_entry_id FROM structured_entries WHERE id = ? AND deleted_at IS NULL;",
            (structured_entry_id,),
        )
        if row is None:
            return None

        raw_entry_id = row["raw_entry_id"]

        self._db.execute(
            "UPDATE structured_entries SET deleted_at = ? WHERE id = ?;",
            (deleted_at, structured_entry_id),
        )
        self._db.execute(
            "UPDATE raw_entries SET deleted_at = ? WHERE id = ?;",
            (deleted_at, raw_entry_id),
        )
        self._db.commit()
        return raw_entry_id

    def restore_entry(self, structured_entry_id: str) -> str | None:
        """Restore a soft-deleted structured entry and its linked raw entry.

        Returns the raw_entry_id if the entry was found, otherwise None.
        """
        row = self._db.fetchone(
            "SELECT raw_entry_id FROM structured_entries WHERE id = ? AND deleted_at IS NOT NULL;",
            (structured_entry_id,),
        )
        if row is None:
            return None

        raw_entry_id = row["raw_entry_id"]

        self._db.execute(
            "UPDATE structured_entries SET deleted_at = NULL WHERE id = ?;",
            (structured_entry_id,),
        )
        self._db.execute(
            "UPDATE raw_entries SET deleted_at = NULL WHERE id = ?;",
            (raw_entry_id,),
        )
        self._db.commit()
        return raw_entry_id

    def purge_deleted_entries(self, before_date: str) -> int:
        """Permanently delete entries that were soft-deleted before the given date.

        Deletes structured_entries, then raw_entries (respecting FK order).
        Returns the number of raw entries purged.
        """
        # Find raw entry IDs to purge
        rows = self._db.fetchall(
            """
            SELECT DISTINCT r.id
            FROM raw_entries r
            WHERE r.deleted_at IS NOT NULL
              AND r.deleted_at < ?;
            """,
            (before_date,),
        )
        raw_ids = [row["id"] for row in rows]

        if not raw_ids:
            return 0

        placeholders = ",".join("?" for _ in raw_ids)

        # Delete structured_entry_revisions that reference these structured entries
        self._db.execute(
            f"""
            DELETE FROM structured_entry_revisions
            WHERE structured_entry_id IN (
                SELECT id FROM structured_entries WHERE raw_entry_id IN ({placeholders})
            );
            """,
            tuple(raw_ids),
        )

        # Delete generated files
        self._db.execute(
            f"DELETE FROM generated_files WHERE raw_entry_id IN ({placeholders});",
            tuple(raw_ids),
        )

        # Orphan audit logs (set raw_entry_id to NULL to prevent FK violation)
        self._db.execute(
            f"UPDATE audit_logs SET raw_entry_id = NULL WHERE raw_entry_id IN ({placeholders});",
            tuple(raw_ids),
        )

        # Delete structured entries
        self._db.execute(
            f"DELETE FROM structured_entries WHERE raw_entry_id IN ({placeholders});",
            tuple(raw_ids),
        )

        # Delete raw entries
        self._db.execute(
            f"DELETE FROM raw_entries WHERE id IN ({placeholders});",
            tuple(raw_ids),
        )

        self._db.commit()
        return len(raw_ids)
