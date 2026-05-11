"""Tests for deterministic extraction quality scoring."""

from personal_intelligence_engine.app.domain.schemas import ExtractionResult
from personal_intelligence_engine.app.domain.types import EntryType
from personal_intelligence_engine.app.evaluation.scoring import score_extraction


def make_expected() -> dict:
    return {
        "entry_type": "decision",
        "project": "PIE",
        "summary_keywords": ["FakeExtractor", "padrao", "Ollama"],
        "expected_tags": ["decision", "pie", "ollama"],
        "confidence_range": {"min": 0.80, "max": 0.98},
        "notes": "Synthetic expected output.",
    }


def make_actual(**overrides):
    actual = {
        "entry_type": "decision",
        "project": "PIE",
        "summary": "Decision to keep FakeExtractor as padrao and enable Ollama only by configuration.",
        "confidence": 0.90,
        "tags": ["decision", "pie", "ollama"],
    }
    actual.update(overrides)
    return actual


def test_scoring_perfect_match_passes():
    result = score_extraction(make_expected(), make_actual())

    assert result.total_score == 1.0
    assert result.passed is True
    assert all(score == 1.0 for score in result.field_scores.values())
    assert result.notes == []


def test_scoring_entry_type_mismatch_lowers_score():
    result = score_extraction(make_expected(), make_actual(entry_type="idea"))

    assert result.field_scores["entry_type"] == 0.0
    assert result.total_score == 0.8
    assert result.passed is True
    assert any("entry_type mismatch" in note for note in result.notes)


def test_scoring_tags_partial_match_uses_expected_tag_overlap():
    result = score_extraction(make_expected(), make_actual(tags=["decision", "pie"]))

    assert result.field_scores["tags"] == 0.6667
    assert 0 <= result.total_score <= 1
    assert any("tags missing" in note for note in result.notes)


def test_scoring_confidence_outside_range_fails_confidence_field():
    result = score_extraction(make_expected(), make_actual(confidence=0.50))

    assert result.field_scores["confidence"] == 0.0
    assert 0 <= result.total_score <= 1
    assert any("confidence outside range" in note for note in result.notes)


def test_scoring_project_null_expected_matches_blank_or_none_actual():
    expected = make_expected()
    expected["project"] = None

    none_result = score_extraction(expected, make_actual(project=None))
    blank_result = score_extraction(expected, make_actual(project=" "))

    assert none_result.field_scores["project"] == 1.0
    assert blank_result.field_scores["project"] == 1.0


def test_scoring_summary_without_keyword_lowers_summary_field():
    result = score_extraction(make_expected(), make_actual(summary="Decision about local configuration."))

    assert result.field_scores["summary"] == 0.0
    assert result.total_score == 0.8
    assert any("summary missing keywords" in note for note in result.notes)


def test_scoring_accepts_extraction_result_objects():
    actual = ExtractionResult(
        entry_type=EntryType.DECISION,
        project="PIE",
        summary="Decision to keep FakeExtractor as padrao and enable Ollama only by configuration.",
        confidence=0.90,
        tags=["decision", "pie", "ollama"],
    )

    result = score_extraction(make_expected(), actual)

    assert result.total_score == 1.0


def test_scoring_total_score_stays_between_zero_and_one():
    result = score_extraction(
        make_expected(),
        make_actual(
            entry_type="problem",
            project=None,
            summary="No matching terms here.",
            confidence=0.10,
            tags=[],
        ),
    )

    assert 0 <= result.total_score <= 1
    assert result.passed is False
