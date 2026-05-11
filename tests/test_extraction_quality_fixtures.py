"""Integrity tests for synthetic extraction quality fixtures."""

import json
import re
from pathlib import Path

from personal_intelligence_engine.app.domain.types import EntryType

FIXTURES_PATH = Path(__file__).resolve().parent / "fixtures" / "extraction_quality_cases.json"

REQUIRED_CASE_FIELDS = {"id", "input_text", "expected"}
REQUIRED_EXPECTED_FIELDS = {
    "entry_type",
    "project",
    "summary_keywords",
    "expected_tags",
    "confidence_range",
    "notes",
}
SENSITIVE_PATTERNS = [
    re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE),
    re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b(?:api[_-]?key|token|secret|password)\b", re.IGNORECASE),
    re.compile(r"\bC:\\Users\\", re.IGNORECASE),
]


def load_cases() -> list[dict]:
    return json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))


def test_extraction_quality_fixture_file_exists():
    assert FIXTURES_PATH.exists()


def test_extraction_quality_fixture_json_is_valid():
    cases = load_cases()

    assert isinstance(cases, list)
    assert cases


def test_extraction_quality_cases_have_required_fields():
    cases = load_cases()

    for case in cases:
        assert case.keys() >= REQUIRED_CASE_FIELDS
        assert isinstance(case["id"], str)
        assert case["id"].strip()
        assert isinstance(case["input_text"], str)
        assert case["input_text"].strip()

        expected = case["expected"]
        assert expected.keys() >= REQUIRED_EXPECTED_FIELDS
        assert isinstance(expected["summary_keywords"], list)
        assert expected["summary_keywords"]
        assert isinstance(expected["expected_tags"], list)
        assert expected["expected_tags"]
        assert isinstance(expected["notes"], str)
        assert expected["notes"].strip()


def test_extraction_quality_fixtures_cover_all_entry_types():
    cases = load_cases()
    covered_types = {case["expected"]["entry_type"] for case in cases}
    expected_types = {entry_type.value for entry_type in EntryType}

    assert covered_types == expected_types


def test_extraction_quality_confidence_ranges_are_valid():
    cases = load_cases()

    for case in cases:
        confidence_range = case["expected"]["confidence_range"]
        assert set(confidence_range) == {"min", "max"}

        minimum = confidence_range["min"]
        maximum = confidence_range["max"]
        assert isinstance(minimum, int | float)
        assert isinstance(maximum, int | float)
        assert 0 <= minimum <= maximum <= 1


def test_extraction_quality_ids_are_unique():
    cases = load_cases()
    ids = [case["id"] for case in cases]

    assert len(ids) == len(set(ids))


def test_extraction_quality_fixtures_do_not_contain_obvious_personal_data():
    cases = load_cases()

    for case in cases:
        searchable_text = json.dumps(case, ensure_ascii=False)
        for pattern in SENSITIVE_PATTERNS:
            assert not pattern.search(searchable_text), case["id"]
