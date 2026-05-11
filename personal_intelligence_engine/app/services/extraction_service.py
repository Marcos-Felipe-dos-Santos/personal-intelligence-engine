"""Extraction service — orchestrates text extraction via adapters."""

from __future__ import annotations

from typing import Protocol

from personal_intelligence_engine.app.adapters.fake_extractor import FakeExtractor
from personal_intelligence_engine.app.domain.schemas import ExtractionResult


class Extractor(Protocol):
    """Minimal interface expected from extractor adapters."""

    def extract(self, content: str) -> ExtractionResult:
        """Extract structured data from raw text."""
        ...


class ExtractionService:
    """Runs extraction on raw text using the configured extractor.

    Currently uses FakeExtractor. The extractor can be swapped for
    a real LLM adapter in future phases by changing the constructor arg.
    """

    def __init__(self, extractor: Extractor | None = None) -> None:
        self._extractor = extractor or FakeExtractor()

    def extract(self, content: str) -> ExtractionResult:
        """Extract structured data from raw text.

        Args:
            content: Raw text content.

        Returns:
            ExtractionResult with entry_type, summary, confidence, tags.
        """
        return self._extractor.extract(content)
