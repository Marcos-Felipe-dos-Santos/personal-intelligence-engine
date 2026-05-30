"""FakeExtractor — deterministic extractor for testing without LLM.

This adapter uses simple keyword rules to classify text into entry types.
It is designed to be swapped for a real LLM extractor in future phases
without modifying the service layer.

IMPORTANT: Confidence values from FakeExtractor are NOT calibrated for
semantic accuracy. They reflect only keyword-match specificity and should
not be compared directly with LLM-based extractor confidence scores.
"""

from __future__ import annotations

import re

from personal_intelligence_engine.app.domain.schemas import ExtractionResult
from personal_intelligence_engine.app.domain.types import EntryType


class FakeExtractor:
    """Deterministic text extractor using keyword matching.

    Rules:
        - "decidi" → decision
        - "ideia" → idea
        - "problema", "erro", "bloqueio" → problem
        - "tarefa", "preciso", "fazer" → candidate_task
        - "insight", "percebi", "descobri" → insight
        - "referência", "link", "artigo" → reference
        - "revisão", "review" → review
        - Otherwise → general_note (short text) or log (longer text)

    Confidence reflects keyword-match specificity, NOT semantic certainty:
        - Exact keyword match → 0.60 (above fallback, below review threshold)
        - Reference/review keywords → 0.55 (less specific patterns)
        - Fallback → 0.30 (clearly uncertain, triggers needs_review)
    """

    # Ordered list of (pattern, entry_type, confidence)
    _RULES: list[tuple[str, EntryType, float]] = [
        (r"\b(?:decidi|decided)\b", EntryType.DECISION, 0.60),
        (r"\b(?:ideia|idea)\b", EntryType.IDEA, 0.60),
        (r"\b(?:problema|erro|bloqueio|problem|error|blocker)\b", EntryType.PROBLEM, 0.60),
        (r"\b(?:tarefa|preciso|fazer|task|need to|todo)\b", EntryType.CANDIDATE_TASK, 0.60),
        (r"\b(?:insight|percebi|descobri|noticed|realized|discovered)\b", EntryType.INSIGHT, 0.60),
        (r"\b(?:referência|link|artigo|reference|article)\b", EntryType.REFERENCE, 0.55),
        (r"\b(?:revisão|review)\b", EntryType.REVIEW, 0.55),
    ]

    def extract(self, content: str) -> ExtractionResult:
        """Extract structured data from raw text content.

        Args:
            content: The raw text to analyze.

        Returns:
            ExtractionResult with entry_type, summary, confidence, and tags.
        """
        lower = content.lower()

        for pattern, entry_type, confidence in self._RULES:
            if re.search(pattern, lower):
                return ExtractionResult(
                    entry_type=entry_type,
                    summary=self._make_summary(content),
                    confidence=confidence,
                    tags=self._extract_tags(lower, entry_type),
                    extra={
                        "extractor": "FakeExtractor",
                        "confidence_note": "Deterministic keyword match — not calibrated for semantic accuracy.",
                        "match_rule": pattern,
                    },
                )

        # Fallback: short texts are general_note, longer texts are log
        is_short = len(content.split()) < 20
        return ExtractionResult(
            entry_type=EntryType.GENERAL_NOTE if is_short else EntryType.LOG,
            summary=self._make_summary(content),
            confidence=0.30,
            tags=["unclassified"],
            extra={
                "extractor": "FakeExtractor",
                "confidence_note": "Deterministic keyword match — not calibrated for semantic accuracy.",
                "match_rule": "fallback",
            },
        )

    @staticmethod
    def _make_summary(content: str, max_len: int = 120) -> str:
        """Create a summary by truncating content."""
        clean = " ".join(content.split())
        if len(clean) <= max_len:
            return clean
        return clean[:max_len].rsplit(" ", 1)[0] + "..."

    @staticmethod
    def _extract_tags(lower_content: str, entry_type: EntryType) -> list[str]:
        """Extract basic tags from content."""
        tags = [entry_type.value]
        tag_keywords = {
            "urgente": "urgent",
            "importante": "important",
            "projeto": "project",
            "bug": "bug",
            "feature": "feature",
        }
        for keyword, tag in tag_keywords.items():
            if keyword in lower_content:
                tags.append(tag)
        return tags
