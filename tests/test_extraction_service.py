"""Tests for ExtractionService adapter protocol behavior."""

from personal_intelligence_engine.app.domain.schemas import ExtractionResult
from personal_intelligence_engine.app.domain.types import EntryType
from personal_intelligence_engine.app.services.extraction_service import ExtractionService


class CompatibleExtractor:
    def extract(self, content: str) -> ExtractionResult:
        return ExtractionResult(
            entry_type=EntryType.GENERAL_NOTE,
            summary=f"Captured: {content}",
            confidence=0.71,
            tags=["synthetic"],
        )


def test_extraction_service_accepts_any_protocol_compatible_adapter():
    service = ExtractionService(CompatibleExtractor())

    result = service.extract("Synthetic adapter input")

    assert result.entry_type == EntryType.GENERAL_NOTE
    assert result.summary == "Captured: Synthetic adapter input"
    assert result.confidence == 0.71
