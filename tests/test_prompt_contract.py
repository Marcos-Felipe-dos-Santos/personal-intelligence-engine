"""Prompt contract tests using synthetic regression fixtures."""

import json
from pathlib import Path

from personal_intelligence_engine.app.domain.schemas import ExtractionResult
from personal_intelligence_engine.app.domain.types import EntryType

ROOT = Path(__file__).resolve().parent.parent
PROMPT_PATH = ROOT / "personal_intelligence_engine" / "app" / "prompts" / "extraction_prompt.md"
FIXTURES_PATH = Path(__file__).resolve().parent / "fixtures" / "prompt_regression_cases.json"


def test_extraction_prompt_documents_required_contract():
    prompt = PROMPT_PATH.read_text(encoding="utf-8")

    assert "Return only JSON" in prompt
    assert "Do not invent" in prompt
    assert "null" in prompt
    assert "confidence" in prompt
    assert "tags" in prompt
    for entry_type in EntryType:
        assert f"`{entry_type.value}`" in prompt


def test_prompt_regression_fixtures_match_extraction_schema():
    cases = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))

    assert len(cases) >= 5
    for case in cases:
        result = ExtractionResult(**case["expected"])
        assert result.entry_type in EntryType
        assert 0 <= result.confidence <= 1
        assert case["input"]
        assert "@" not in case["input"]
