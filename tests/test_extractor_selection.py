"""Tests for extractor backend configuration."""

import pytest

from personal_intelligence_engine.app.adapters.fake_extractor import FakeExtractor
from personal_intelligence_engine.app.adapters.local_llm_extractor import LocalLLMExtractor
from personal_intelligence_engine.app.config import Config
from personal_intelligence_engine.app.main import PIEApp, check_extractor_backend


class HealthClient:
    def __init__(self, models=None):
        self.models = models if models is not None else ["test-model"]

    def generate(self, *, base_url, model, prompt, timeout_seconds):
        raise AssertionError("health check should not generate")

    def list_models(self, *, base_url, timeout_seconds):
        if isinstance(self.models, Exception):
            raise self.models
        return self.models


def _config(work_dir, **overrides) -> Config:
    values = {
        "database_path": work_dir / "test.db",
        "notes_dir": work_dir / "notes",
        "reports_dir": work_dir / "reports",
        "extractor_backend": "fake",
    }
    values.update(overrides)
    return Config(**values)


def test_default_config_uses_fake_backend(monkeypatch):
    monkeypatch.delenv("PIE_EXTRACTOR_BACKEND", raising=False)

    config = Config()

    assert config.extractor_backend == "fake"


def test_app_uses_fake_extractor_by_default(work_dir):
    app = PIEApp(config=_config(work_dir))
    try:
        assert isinstance(app.extractor, FakeExtractor)
    finally:
        app.close()


def test_env_fake_backend_uses_fake_extractor(monkeypatch, work_dir):
    monkeypatch.setenv("PIE_EXTRACTOR_BACKEND", "fake")
    monkeypatch.setenv("PIE_DATABASE_PATH", str(work_dir / "test.db"))
    monkeypatch.setenv("PIE_NOTES_DIR", str(work_dir / "notes"))
    monkeypatch.setenv("PIE_REPORTS_DIR", str(work_dir / "reports"))

    app = PIEApp()
    try:
        assert isinstance(app.extractor, FakeExtractor)
    finally:
        app.close()


def test_ollama_backend_uses_local_llm_extractor(work_dir):
    app = PIEApp(config=_config(work_dir, extractor_backend="ollama", ollama_model="test-model"))
    try:
        assert isinstance(app.extractor, LocalLLMExtractor)
    finally:
        app.close()


def test_invalid_backend_is_rejected(work_dir):
    with pytest.raises(ValueError, match="Invalid extractor backend"):
        PIEApp(config=_config(work_dir, extractor_backend="unknown"))


def test_fake_backend_health_check_passes(work_dir):
    result = check_extractor_backend(_config(work_dir))

    assert result["ok"] is True
    assert result["backend"] == "fake"
    assert "FakeExtractor is available" in result["message"]


def test_ollama_health_check_without_model_is_friendly(work_dir):
    result = check_extractor_backend(_config(work_dir, extractor_backend="ollama", ollama_model=""))

    assert result["ok"] is False
    assert result["backend"] == "ollama"
    assert "Ollama model is not configured" in result["message"]


def test_ollama_health_check_unavailable_is_friendly(work_dir):
    result = check_extractor_backend(
        _config(work_dir, extractor_backend="ollama", ollama_model="test-model"),
        http_client=HealthClient(models=OSError("connection refused")),
    )

    assert result["ok"] is False
    assert result["backend"] == "ollama"
    assert "Ollama is unavailable" in result["message"]


def test_ollama_health_check_with_model_passes(work_dir):
    result = check_extractor_backend(
        _config(work_dir, extractor_backend="ollama", ollama_model="test-model"),
        http_client=HealthClient(models=["test-model"]),
    )

    assert result["ok"] is True
    assert result["backend"] == "ollama"
    assert result["model_name"] == "test-model"
    assert result["prompt_version"] == "extraction_prompt_v1"
