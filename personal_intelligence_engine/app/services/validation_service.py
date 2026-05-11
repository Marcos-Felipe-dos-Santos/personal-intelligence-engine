"""Validation service — validates extraction results and creates structured entries."""

from __future__ import annotations

from personal_intelligence_engine.app.domain.schemas import (
    ExtractionResult,
    StructuredEntry,
)
from personal_intelligence_engine.app.domain.types import (
    LOW_CONFIDENCE_THRESHOLD,
    ValidationStatus,
)
from personal_intelligence_engine.app.repositories.entries_repository import EntriesRepository


class ValidationService:
    """Validates extraction results and persists structured entries."""

    def __init__(self, entries_repo: EntriesRepository) -> None:
        self._entries_repo = entries_repo

    def validate_and_save(
        self,
        raw_entry_id: str,
        extraction: ExtractionResult,
    ) -> StructuredEntry:
        """Validate an extraction result and save as structured entry.

        If confidence is below the threshold, marks as needs_review.

        Args:
            raw_entry_id: ID of the source raw entry.
            extraction: The extraction result to validate.

        Returns:
            The persisted StructuredEntry.
        """
        validation_status = ValidationStatus.VALID
        if extraction.confidence < LOW_CONFIDENCE_THRESHOLD:
            validation_status = ValidationStatus.NEEDS_REVIEW

        structured = StructuredEntry(
            raw_entry_id=raw_entry_id,
            entry_type=extraction.entry_type,
            project=extraction.project,
            summary=extraction.summary,
            confidence=extraction.confidence,
            structured_json=extraction.to_structured_json(),
            validation_status=validation_status,
        )

        self._entries_repo.insert_structured_entry(structured)
        return structured
