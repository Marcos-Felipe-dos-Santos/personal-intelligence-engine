"""Tests for Markdown extraction quality evaluation reports."""

from datetime import datetime, timezone

from personal_intelligence_engine.app.evaluation.report import render_extraction_evaluation_report
from personal_intelligence_engine.app.evaluation.runner import (
    ExtractionEvaluationResult,
    ExtractionEvaluationRun,
)


def make_run() -> ExtractionEvaluationRun:
    return ExtractionEvaluationRun(
        backend="fake",
        fixture_count=2,
        average_score=0.875,
        passed_count=1,
        results=[
            ExtractionEvaluationResult(
                fixture_id="synthetic_decision",
                expected_entry_type="decision",
                actual_entry_type="decision",
                total_score=1.0,
                field_scores={
                    "entry_type": 1.0,
                    "project": 1.0,
                    "summary": 1.0,
                    "tags": 1.0,
                    "confidence": 1.0,
                },
                passed=True,
                notes=[],
            ),
            ExtractionEvaluationResult(
                fixture_id="synthetic_problem",
                expected_entry_type="problem",
                actual_entry_type="log",
                total_score=0.75,
                field_scores={
                    "entry_type": 0.0,
                    "project": 1.0,
                    "summary": 1.0,
                    "tags": 0.75,
                    "confidence": 1.0,
                },
                passed=False,
                notes=["entry_type mismatch: expected 'problem', got 'log'"],
            ),
        ],
    )


def test_render_extraction_evaluation_report_contains_summary():
    report = render_extraction_evaluation_report(
        make_run(),
        generated_at=datetime(2026, 5, 11, 12, 0, tzinfo=timezone.utc),
    )

    assert "# Extraction Quality Evaluation Report" in report
    assert "2026-05-11T12:00:00+00:00" in report
    assert "- **Backend:** `fake`" in report
    assert "- **Fixture count:** 2" in report
    assert "- **Average score:** 0.88" in report
    assert "- **Passed:** 1" in report
    assert "- **Failed:** 1" in report


def test_render_extraction_evaluation_report_contains_fixture_table():
    report = render_extraction_evaluation_report(make_run())

    assert "| Fixture ID | Expected Type | Actual Type | Total Score | Field Scores | Status | Notes |" in report
    assert "`synthetic_decision`" in report
    assert "`synthetic_problem`" in report
    assert "`decision`" in report
    assert "`problem`" in report
    assert "`log`" in report
    assert "entry_type=0.00" in report
    assert "PASS" in report
    assert "FAIL" in report


def test_render_extraction_evaluation_report_lists_limitations():
    report = render_extraction_evaluation_report(make_run())

    assert "## Limitations" in report
    assert "synthetic fixtures only" in report
    assert "No RAG, embeddings, dashboard, or external model benchmark" in report
    assert "Human review is still required" in report
