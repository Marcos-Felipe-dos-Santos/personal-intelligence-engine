"""Tests for the synthetic extraction quality evaluation runner."""

import json
from pathlib import Path

from personal_intelligence_engine.app.adapters.fake_extractor import FakeExtractor
from personal_intelligence_engine.app.domain.schemas import ExtractionResult
from personal_intelligence_engine.app.domain.types import EntryType
from personal_intelligence_engine.app.evaluation.runner import (
    evaluate_cases,
    evaluate_extractor,
    load_extraction_quality_cases,
)

FIXTURES_PATH = Path(__file__).resolve().parent / "fixtures" / "extraction_quality_cases.json"


class ControlledExtractor:
    """Small synthetic extractor for deterministic runner tests."""

    def extract(self, content: str) -> ExtractionResult:
        return ExtractionResult(
            entry_type=EntryType.DECISION,
            project="PIE",
            summary=f"Decision summary for {content} with FakeExtractor, padrao and Ollama.",
            confidence=0.90,
            tags=["decision", "pie", "ollama"],
        )


def test_runner_loads_synthetic_fixtures():
    cases = load_extraction_quality_cases(FIXTURES_PATH)

    assert cases
    assert all("input_text" in case for case in cases)
    assert all("expected" in case for case in cases)


def test_runner_returns_structured_results_for_controlled_extractor():
    cases = [
        {
            "id": "synthetic_decision",
            "input_text": "Synthetic PIE decision text.",
            "expected": {
                "entry_type": "decision",
                "project": "PIE",
                "summary_keywords": ["FakeExtractor", "padrao", "Ollama"],
                "expected_tags": ["decision", "pie", "ollama"],
                "confidence_range": {"min": 0.80, "max": 0.95},
                "notes": "Synthetic case.",
            },
        }
    ]

    run = evaluate_cases(ControlledExtractor(), cases, backend="controlled")

    assert run.backend == "controlled"
    assert run.fixture_count == 1
    assert run.average_score == 1.0
    assert run.passed_count == 1

    result = run.results[0]
    assert result.fixture_id == "synthetic_decision"
    assert result.expected_entry_type == "decision"
    assert result.actual_entry_type == "decision"
    assert result.total_score == 1.0
    assert result.field_scores["entry_type"] == 1.0
    assert result.passed is True
    assert result.notes == []


def test_runner_output_is_json_serializable():
    cases = [
        {
            "id": "synthetic_decision",
            "input_text": "Synthetic PIE decision text.",
            "expected": {
                "entry_type": "decision",
                "project": "PIE",
                "summary_keywords": ["FakeExtractor"],
                "expected_tags": ["decision"],
                "confidence_range": {"min": 0.80, "max": 0.95},
                "notes": "Synthetic case.",
            },
        }
    ]

    run = evaluate_cases(ControlledExtractor(), cases, backend="controlled")

    encoded = json.dumps(run.to_dict())
    assert "synthetic_decision" in encoded
    assert "field_scores" in encoded


def test_runner_evaluates_real_quality_fixtures_with_fake_extractor():
    run = evaluate_extractor(FakeExtractor(), FIXTURES_PATH, backend="fake")

    assert run.backend == "fake"
    assert run.fixture_count == 9
    assert len(run.results) == 9
    assert 0 <= run.average_score <= 1
    for result in run.results:
        assert result.fixture_id
        assert result.expected_entry_type
        assert result.actual_entry_type
        assert 0 <= result.total_score <= 1
        assert set(result.field_scores) == {"entry_type", "project", "summary", "tags", "confidence"}
        assert isinstance(result.passed, bool)
        assert isinstance(result.notes, list)
