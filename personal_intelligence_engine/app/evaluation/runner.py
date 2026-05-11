"""Local runner for synthetic extraction quality evaluation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

from personal_intelligence_engine.app.evaluation.scoring import score_extraction


class EvaluationExtractor(Protocol):
    """Minimal extractor contract needed by the evaluation runner."""

    def extract(self, content: str) -> Any:
        """Extract structured data from raw text."""


@dataclass(frozen=True)
class ExtractionEvaluationResult:
    """Per-fixture extraction evaluation result."""

    fixture_id: str
    expected_entry_type: str
    actual_entry_type: str
    total_score: float
    field_scores: dict[str, float]
    passed: bool
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "fixture_id": self.fixture_id,
            "expected_entry_type": self.expected_entry_type,
            "actual_entry_type": self.actual_entry_type,
            "total_score": self.total_score,
            "field_scores": self.field_scores,
            "passed": self.passed,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class ExtractionEvaluationRun:
    """Structured result for an extraction evaluation run."""

    backend: str
    fixture_count: int
    average_score: float
    passed_count: int
    results: list[ExtractionEvaluationResult]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "backend": self.backend,
            "fixture_count": self.fixture_count,
            "average_score": self.average_score,
            "passed_count": self.passed_count,
            "results": [result.to_dict() for result in self.results],
        }


def load_extraction_quality_cases(fixtures_path: str | Path) -> list[dict[str, Any]]:
    """Load synthetic extraction quality fixtures from JSON."""
    path = Path(fixtures_path)
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate_extractor(
    extractor: EvaluationExtractor,
    fixtures_path: str | Path,
    *,
    backend: str = "custom",
) -> ExtractionEvaluationRun:
    """Run synthetic fixtures against an extractor and score the outputs."""
    cases = load_extraction_quality_cases(fixtures_path)
    return evaluate_cases(extractor, cases, backend=backend)


def evaluate_cases(
    extractor: EvaluationExtractor,
    cases: list[dict[str, Any]],
    *,
    backend: str = "custom",
) -> ExtractionEvaluationRun:
    """Run in-memory synthetic cases against an extractor and score the outputs."""
    results: list[ExtractionEvaluationResult] = []

    for case in cases:
        actual = extractor.extract(case["input_text"])
        expected = case["expected"]
        score = score_extraction(expected, actual)
        actual_data = _as_mapping(actual)

        results.append(
            ExtractionEvaluationResult(
                fixture_id=case["id"],
                expected_entry_type=str(expected["entry_type"]),
                actual_entry_type=_normalize_entry_type(actual_data.get("entry_type")),
                total_score=score.total_score,
                field_scores=score.field_scores,
                passed=score.passed,
                notes=score.notes,
            )
        )

    average_score = 0.0
    if results:
        average_score = round(sum(result.total_score for result in results) / len(results), 4)

    return ExtractionEvaluationRun(
        backend=backend,
        fixture_count=len(results),
        average_score=average_score,
        passed_count=sum(1 for result in results if result.passed),
        results=results,
    )


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


def _normalize_entry_type(value: Any) -> str:
    if isinstance(value, Enum):
        return str(value.value)
    if value is None:
        return ""
    return str(value)
