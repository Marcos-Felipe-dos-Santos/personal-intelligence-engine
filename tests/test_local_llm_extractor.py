"""Tests for the optional local LLM extractor adapter."""

from __future__ import annotations

import json

import pytest

from personal_intelligence_engine.app.adapters.local_llm_extractor import (
    LocalLLMExtractor,
    LocalLLMExtractorError,
)
from personal_intelligence_engine.app.domain.types import EntryType


class FakeOllamaClient:
    def __init__(self, envelope, models=None):
        self.envelopes = envelope if isinstance(envelope, list) else [envelope]
        self.models = models if models is not None else ["test-model"]
        self.calls = []
        self.health_calls = []

    def generate(self, *, base_url, model, prompt, timeout_seconds):
        self.calls.append(
            {
                "base_url": base_url,
                "model": model,
                "prompt": prompt,
                "timeout_seconds": timeout_seconds,
            }
        )
        envelope = self.envelopes[min(len(self.calls) - 1, len(self.envelopes) - 1)]
        if isinstance(envelope, Exception):
            raise envelope
        return envelope

    def list_models(self, *, base_url, timeout_seconds):
        self.health_calls.append({"base_url": base_url, "timeout_seconds": timeout_seconds})
        if isinstance(self.models, Exception):
            raise self.models
        return self.models


def _extractor(envelope, *, max_retries=2, client=None) -> LocalLLMExtractor:
    http_client = client or FakeOllamaClient(envelope)
    return LocalLLMExtractor(
        base_url="http://localhost:11434",
        model="test-model",
        timeout_seconds=1,
        max_retries=max_retries,
        retry_backoff_seconds=0,
        http_client=http_client,
    )


def test_local_llm_extractor_parses_valid_json():
    payload = {
        "entry_type": "idea",
        "project": None,
        "summary": "Synthetic idea for improving local extraction.",
        "confidence": 0.82,
        "tags": ["idea", "local"],
        "extra": {},
    }
    extractor = _extractor({"response": json.dumps(payload)})

    result = extractor.extract("Tive uma ideia para melhorar a extracao local")

    assert result.entry_type == EntryType.IDEA
    assert result.project is None
    assert result.confidence == 0.82
    assert result.tags == ["idea", "local"]


def test_local_llm_extractor_rejects_invalid_json():
    client = FakeOllamaClient({"response": "{invalid"})
    extractor = _extractor(None, client=client)

    with pytest.raises(LocalLLMExtractorError, match="not valid JSON"):
        extractor.extract("Synthetic text")

    assert len(client.calls) == 1


def test_local_llm_extractor_treats_timeout_as_controlled_error():
    extractor = _extractor(TimeoutError("synthetic timeout"))

    with pytest.raises(LocalLLMExtractorError, match="timed out"):
        extractor.extract("Synthetic text")


def test_local_llm_extractor_retries_timeout_then_succeeds():
    payload = {
        "entry_type": "idea",
        "summary": "Synthetic retry success",
        "confidence": 0.8,
        "tags": [],
        "extra": {},
    }
    client = FakeOllamaClient([TimeoutError("first timeout"), {"response": json.dumps(payload)}])
    extractor = _extractor(None, client=client)

    result = extractor.extract("Synthetic text")

    assert result.summary == "Synthetic retry success"
    assert len(client.calls) == 2


def test_local_llm_extractor_retries_connection_error_then_succeeds():
    payload = {
        "entry_type": "problem",
        "summary": "Synthetic connection retry success",
        "confidence": 0.77,
        "tags": [],
        "extra": {},
    }
    client = FakeOllamaClient([OSError("connection refused"), {"response": json.dumps(payload)}])
    extractor = _extractor(None, client=client)

    result = extractor.extract("Synthetic text")

    assert result.summary == "Synthetic connection retry success"
    assert len(client.calls) == 2


def test_local_llm_extractor_respects_retry_limit():
    client = FakeOllamaClient([TimeoutError("timeout 1"), TimeoutError("timeout 2")])
    extractor = _extractor(None, max_retries=1, client=client)

    with pytest.raises(LocalLLMExtractorError, match="timed out"):
        extractor.extract("Synthetic text")

    assert len(client.calls) == 2


def test_local_llm_extractor_treats_unavailable_ollama_as_controlled_error():
    extractor = _extractor(OSError("connection refused"))

    with pytest.raises(LocalLLMExtractorError, match="Ollama is unavailable"):
        extractor.extract("Synthetic text")


def test_local_llm_extractor_rejects_empty_response():
    extractor = _extractor({"response": "   "})

    with pytest.raises(LocalLLMExtractorError, match="empty response"):
        extractor.extract("Synthetic text")


def test_local_llm_extractor_rejects_schema_invalid_entry_type():
    payload = {
        "entry_type": "invalid_type",
        "summary": "Synthetic summary",
        "confidence": 0.7,
        "tags": [],
        "extra": {},
    }
    client = FakeOllamaClient({"response": json.dumps(payload)})
    extractor = _extractor(None, client=client)

    with pytest.raises(LocalLLMExtractorError, match="entry_type"):
        extractor.extract("Synthetic text")

    assert len(client.calls) == 1


def test_local_llm_extractor_rejects_schema_invalid_confidence():
    payload = {
        "entry_type": "idea",
        "summary": "Synthetic summary",
        "confidence": 1.5,
        "tags": [],
        "extra": {},
    }
    extractor = _extractor({"response": json.dumps(payload)})

    with pytest.raises(LocalLLMExtractorError, match="confidence"):
        extractor.extract("Synthetic text")


def test_local_llm_extractor_requires_model():
    with pytest.raises(LocalLLMExtractorError, match="PIE_OLLAMA_MODEL"):
        LocalLLMExtractor(base_url="http://localhost:11434", model="")


def test_local_llm_extractor_rejects_invalid_base_url():
    with pytest.raises(LocalLLMExtractorError, match="base URL is invalid"):
        LocalLLMExtractor(base_url="localhost:11434", model="test-model")


def test_local_llm_health_check_passes_when_model_exists():
    client = FakeOllamaClient({"response": "{}"}, models=["test-model"])
    extractor = _extractor(None, client=client)

    result = extractor.health_check()

    assert result.ok is True
    assert result.model_name == "test-model"
    assert result.prompt_version == "extraction_prompt_v1"


def test_local_llm_health_check_reports_unavailable_ollama():
    client = FakeOllamaClient({"response": "{}"}, models=OSError("connection refused"))
    extractor = _extractor(None, client=client)

    result = extractor.health_check()

    assert result.ok is False
    assert "Ollama is unavailable" in result.message
