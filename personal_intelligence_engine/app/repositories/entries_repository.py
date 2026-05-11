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
        """Fetch all structured entries created on a given date (YYYY-MM-DD)."""
        rows = self._db.fetchall(
            "SELECT * FROM structured_entries WHERE created_at LIKE ? ORDER BY created_at;",
            (f"{date_str}%",),
        )
        return [StructuredEntry(**dict(row)) for row in rows]

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
