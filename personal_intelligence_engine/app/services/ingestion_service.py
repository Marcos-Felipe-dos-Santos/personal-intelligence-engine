"""Ingestion service — creates raw entries from text input."""

from __future__ import annotations

import hashlib

from personal_intelligence_engine.app.domain.schemas import RawEntry, RawEntryCreate
from personal_intelligence_engine.app.repositories.entries_repository import EntriesRepository


class IngestionService:
    """Handles raw entry creation and persistence."""

    def __init__(self, entries_repo: EntriesRepository) -> None:
        self._entries_repo = entries_repo

    def ingest(self, create: RawEntryCreate) -> RawEntry:
        """Create and persist a raw entry.

        Args:
            create: Input data for the raw entry.

        Returns:
            The persisted RawEntry.
        """
        content_hash = hashlib.sha256(create.content.encode("utf-8")).hexdigest()

        entry = RawEntry(
            content=create.content,
            source=create.source,
            metadata_json=create.metadata_json,
            content_hash=content_hash,
        )

        self._entries_repo.insert_raw_entry(entry)
        return entry
