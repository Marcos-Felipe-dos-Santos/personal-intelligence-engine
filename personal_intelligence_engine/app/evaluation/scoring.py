"""Deterministic scoring for synthetic extraction quality fixtures.

The scorer intentionally uses simple field-level rules. It does not use an LLM,
embeddings, semantic search, or any external service.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

FIELDS = ("entry_type", "project", "summary", "tags", "confidence")
PASSING_SCORE = 0.80


@dataclass(frozen=True)
class ExtractionQualityScore:
    """Structured result for comparing one actual extraction with one expectation."""

    total_score: float
    field_scores: dict[str, float]
    passed: bool
    notes: list[str] = field(default_factory=list)


def score_extraction(expected: dict[str, Any], actual: dict[str, Any] | Any) -> ExtractionQualityScore:
    """Score an extractor output against one synthetic expected output.

    Rules:
    - `entry_type`: exact normalized match.
    - `project`: exact normalized match, including expected null versus blank/None.
    - `summary`: fraction of expected keywords present in the actual summary.
    - `tags`: fraction of expected tags present in actual tags.
    - `confidence`: 1.0 when actual confidence is inside the expected range, otherwise 0.0.
    """
    actual_data = _as_mapping(actual)
    notes: list[str] = []

    field_scores = {
        "entry_type": _score_entry_type(expected, actual_data, notes),
        "project": _score_project(expected, actual_data, notes),
        "summary": _score_summary(expected, actual_data, notes),
        "tags": _score_tags(expected, actual_data, notes),
        "confidence": _score_confidence(expected, actual_data, notes),
    }
    total_score = round(sum(field_scores[field_name] for field_name in FIELDS) / len(FIELDS), 4)

    return ExtractionQualityScore(
        total_score=total_score,
        field_scores=field_scores,
        passed=total_score >= PASSING_SCORE,
        notes=notes,
    )


def _score_entry_type(expected: dict[str, Any], actual: dict[str, Any], notes: list[str]) -> float:
    expected_type = _normalize_scalar(expected.get("entry_type"))
    actual_type = _normalize_scalar(actual.get("entry_type"))

    if expected_type == actual_type:
        return 1.0

    notes.append(f"entry_type mismatch: expected {expected_type!r}, got {actual_type!r}")
    return 0.0


def _score_project(expected: dict[str, Any], actual: dict[str, Any], notes: list[str]) -> float:
    expected_project = _normalize_optional_text(expected.get("project"))
    actual_project = _normalize_optional_text(actual.get("project"))

    if expected_project == actual_project:
        return 1.0

    notes.append(f"project mismatch: expected {expected_project!r}, got {actual_project!r}")
    return 0.0


def _score_summary(expected: dict[str, Any], actual: dict[str, Any], notes: list[str]) -> float:
    keywords = [_normalize_text(keyword) for keyword in expected.get("summary_keywords", [])]
    keywords = [keyword for keyword in keywords if keyword]
    if not keywords:
        return 1.0

    summary = _normalize_text(actual.get("summary"))
    matched = [keyword for keyword in keywords if keyword in summary]
    score = len(matched) / len(keywords)

    if score < 1.0:
        missing = sorted(set(keywords) - set(matched))
        notes.append(f"summary missing keywords: {', '.join(missing)}")

    return round(score, 4)


def _score_tags(expected: dict[str, Any], actual: dict[str, Any], notes: list[str]) -> float:
    expected_tags = {_normalize_text(tag) for tag in expected.get("expected_tags", []) if _normalize_text(tag)}
    if not expected_tags:
        return 1.0

    actual_tags = {_normalize_text(tag) for tag in actual.get("tags", []) if _normalize_text(tag)}
    matched = expected_tags & actual_tags
    score = len(matched) / len(expected_tags)

    if score < 1.0:
        missing = sorted(expected_tags - matched)
        notes.append(f"tags missing: {', '.join(missing)}")

    return round(score, 4)


def _score_confidence(expected: dict[str, Any], actual: dict[str, Any], notes: list[str]) -> float:
    confidence_range = expected.get("confidence_range", {})
    minimum = confidence_range.get("min")
    maximum = confidence_range.get("max")
    confidence = actual.get("confidence")

    if not _is_number(minimum) or not _is_number(maximum) or not _is_number(confidence):
        notes.append("confidence could not be scored")
        return 0.0

    if float(minimum) <= float(confidence) <= float(maximum):
        return 1.0

    notes.append(f"confidence outside range: expected {minimum}..{maximum}, got {confidence}")
    return 0.0


def _as_mapping(actual: dict[str, Any] | Any) -> dict[str, Any]:
    if isinstance(actual, dict):
        return actual

    return {
        "entry_type": getattr(actual, "entry_type", None),
        "project": getattr(actual, "project", None),
        "summary": getattr(actual, "summary", None),
        "confidence": getattr(actual, "confidence", None),
        "tags": getattr(actual, "tags", []),
    }


def _normalize_scalar(value: Any) -> str:
    if isinstance(value, Enum):
        value = value.value
    return _normalize_text(value)


def _normalize_optional_text(value: Any) -> str | None:
    if value is None:
        return None

    normalized = _normalize_text(value)
    return normalized or None


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().casefold()


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)
