"""Tests for FakeExtractor."""

import json

import pytest

from personal_intelligence_engine.app.adapters.fake_extractor import FakeExtractor
from personal_intelligence_engine.app.domain.types import EntryType


@pytest.fixture
def extractor():
    return FakeExtractor()


class TestFakeExtractor:
    """Tests for the deterministic FakeExtractor."""

    def test_returns_valid_json(self, extractor):
        """FakeExtractor returns a valid JSON-serializable result."""
        result = extractor.extract("Qualquer texto de teste")
        json_str = result.to_structured_json()
        parsed = json.loads(json_str)
        assert "entry_type" in parsed
        assert "summary" in parsed
        assert "confidence" in parsed

    def test_decision_keyword(self, extractor):
        """Text containing 'decidi' is classified as decision."""
        result = extractor.extract("Eu decidi usar SQLite para o projeto")
        assert result.entry_type == EntryType.DECISION
        assert result.confidence >= 0.70

    def test_idea_keyword(self, extractor):
        """Text containing 'ideia' is classified as idea."""
        result = extractor.extract("Tive uma ideia para melhorar o sistema")
        assert result.entry_type == EntryType.IDEA

    def test_problem_keywords(self, extractor):
        """Text containing problem keywords is classified as problem."""
        for text in [
            "Encontrei um problema no deploy",
            "Houve um erro no teste",
            "Tenho um bloqueio na integração",
        ]:
            result = extractor.extract(text)
            assert result.entry_type == EntryType.PROBLEM

    def test_task_keywords(self, extractor):
        """Text containing task keywords is classified as candidate_task."""
        for text in [
            "Preciso configurar o CI",
            "Tenho uma tarefa pendente",
            "Vou fazer a revisão do código",
        ]:
            result = extractor.extract(text)
            assert result.entry_type == EntryType.CANDIDATE_TASK

    def test_fallback_general_note(self, extractor):
        """Short unmatched text falls back to general_note."""
        result = extractor.extract("Olá mundo")
        assert result.entry_type == EntryType.GENERAL_NOTE
        assert result.confidence < 0.70

    def test_fallback_log(self, extractor):
        """Longer unmatched text falls back to log."""
        long_text = " ".join(["palavra"] * 25)
        result = extractor.extract(long_text)
        assert result.entry_type == EntryType.LOG
        assert result.confidence < 0.70

    def test_tags_are_list(self, extractor):
        """Tags should always be a list."""
        result = extractor.extract("Uma ideia urgente para o projeto")
        assert isinstance(result.tags, list)
        assert len(result.tags) > 0

    def test_summary_not_empty(self, extractor):
        """Summary should never be empty."""
        result = extractor.extract("Texto qualquer")
        assert len(result.summary) > 0
