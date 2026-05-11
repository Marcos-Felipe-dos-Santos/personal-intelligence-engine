"""Optional local LLM extractor adapter backed by Ollama."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from pydantic import ValidationError

from personal_intelligence_engine.app.domain.schemas import ExtractionResult

PROMPT_VERSION = "extraction_prompt_v1"
_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "extraction_prompt.md"
_DEFAULT_PROMPT = """You extract structured data from personal notes.
Return only valid JSON with entry_type, project, summary, confidence, tags, and extra.
Do not invent data. Use null when the text provides no evidence.
"""


class LocalLLMExtractorError(ValueError):
    """Raised when optional local LLM extraction fails in a controlled way."""


class LocalLLMConfigurationError(LocalLLMExtractorError):
    """Raised when local LLM configuration is invalid."""


class LocalLLMTransientError(LocalLLMExtractorError):
    """Raised when a retryable local LLM transport failure occurs."""


class LocalLLMResponseError(LocalLLMExtractorError):
    """Raised when the local LLM returns an invalid extraction response."""


@dataclass(frozen=True)
class LocalLLMHealthCheck:
    """Result of checking a configured local LLM backend."""

    ok: bool
    message: str
    model_name: str | None = None
    prompt_version: str | None = None


class OllamaClient(Protocol):
    """Minimal HTTP client contract used by LocalLLMExtractor."""

    def generate(
        self,
        *,
        base_url: str,
        model: str,
        prompt: str,
        timeout_seconds: float,
    ) -> dict[str, Any]:
        """Generate a response from an Ollama-compatible endpoint."""
        ...

    def list_models(
        self,
        *,
        base_url: str,
        timeout_seconds: float,
    ) -> list[str]:
        """List locally available Ollama models."""
        ...


class UrllibOllamaClient:
    """Small stdlib HTTP client for Ollama's generate endpoint."""

    def generate(
        self,
        *,
        base_url: str,
        model: str,
        prompt: str,
        timeout_seconds: float,
    ) -> dict[str, Any]:
        """Call Ollama /api/generate and return the JSON envelope."""
        url = f"{base_url.rstrip('/')}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except TimeoutError as exc:
            raise LocalLLMTransientError("Ollama request timed out.") from exc
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace").strip()
            message = f"Ollama request failed with HTTP {exc.code}."
            if detail:
                message = f"{message} {detail}"
            raise LocalLLMExtractorError(message) from exc
        except urllib.error.URLError as exc:
            raise LocalLLMTransientError("Ollama is unavailable. Is the local server running?") from exc
        except OSError as exc:
            raise LocalLLMTransientError("Ollama is unavailable. Is the local server running?") from exc

        if not body.strip():
            raise LocalLLMResponseError("Ollama returned an empty response.")

        try:
            envelope = json.loads(body)
        except json.JSONDecodeError as exc:
            raise LocalLLMResponseError("Ollama returned invalid JSON.") from exc

        if not isinstance(envelope, dict):
            raise LocalLLMResponseError("Ollama returned an invalid response envelope.")

        return envelope

    def list_models(
        self,
        *,
        base_url: str,
        timeout_seconds: float,
    ) -> list[str]:
        """Call Ollama /api/tags and return available model names."""
        url = f"{base_url.rstrip('/')}/api/tags"
        request = urllib.request.Request(url, method="GET")

        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except TimeoutError as exc:
            raise LocalLLMTransientError("Ollama health check timed out.") from exc
        except urllib.error.HTTPError as exc:
            raise LocalLLMExtractorError(f"Ollama health check failed with HTTP {exc.code}.") from exc
        except urllib.error.URLError as exc:
            raise LocalLLMTransientError("Ollama is unavailable. Is the local server running?") from exc
        except OSError as exc:
            raise LocalLLMTransientError("Ollama is unavailable. Is the local server running?") from exc

        if not body.strip():
            raise LocalLLMResponseError("Ollama health check returned an empty response.")

        try:
            envelope = json.loads(body)
        except json.JSONDecodeError as exc:
            raise LocalLLMResponseError("Ollama health check returned invalid JSON.") from exc

        models = envelope.get("models") if isinstance(envelope, dict) else None
        if not isinstance(models, list):
            raise LocalLLMResponseError("Ollama health check returned an invalid model list.")

        names: list[str] = []
        for model in models:
            if not isinstance(model, dict):
                continue
            name = model.get("name") or model.get("model")
            if isinstance(name, str) and name:
                names.append(name)
        return names


class LocalLLMExtractor:
    """Extractor adapter for optional local LLM extraction via Ollama."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: float = 30,
        max_retries: int = 2,
        retry_backoff_seconds: float = 1,
        http_client: OllamaClient | None = None,
        prompt_path: Path | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        self.base_url = self._validate_base_url(base_url)
        self.model = model.strip()
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self.http_client = http_client or UrllibOllamaClient()
        self.prompt_template = self._load_prompt(prompt_path or _PROMPT_PATH)
        self.prompt_version = PROMPT_VERSION
        self._sleeper = sleeper or time.sleep

        if not self.model:
            raise LocalLLMConfigurationError("Ollama model is not configured. Set PIE_OLLAMA_MODEL.")
        if self.timeout_seconds <= 0:
            raise LocalLLMConfigurationError("LLM timeout must be a positive number.")
        if self.max_retries < 0:
            raise LocalLLMConfigurationError("LLM max retries must be zero or greater.")
        if self.retry_backoff_seconds < 0:
            raise LocalLLMConfigurationError("LLM retry backoff must be zero or greater.")

    def extract(self, content: str) -> ExtractionResult:
        """Extract structured data from text using the configured local LLM."""
        envelope = self._generate(content)
        raw_response = self._extract_response_text(envelope)
        payload = self._parse_extraction_json(raw_response)
        return self._validate_extraction(payload)

    def health_check(self) -> LocalLLMHealthCheck:
        """Check Ollama availability and configured model presence."""
        try:
            models = self.http_client.list_models(
                base_url=self.base_url,
                timeout_seconds=self.timeout_seconds,
            )
        except LocalLLMExtractorError as exc:
            return LocalLLMHealthCheck(
                ok=False,
                message=str(exc),
                model_name=self.model,
                prompt_version=self.prompt_version,
            )
        except TimeoutError:
            return LocalLLMHealthCheck(
                ok=False,
                message="Ollama health check timed out.",
                model_name=self.model,
                prompt_version=self.prompt_version,
            )
        except OSError:
            return LocalLLMHealthCheck(
                ok=False,
                message="Ollama is unavailable. Is the local server running?",
                model_name=self.model,
                prompt_version=self.prompt_version,
            )

        if self.model not in models:
            return LocalLLMHealthCheck(
                ok=False,
                message=f"Ollama model '{self.model}' was not found. Pull or configure the model before using it.",
                model_name=self.model,
                prompt_version=self.prompt_version,
            )

        return LocalLLMHealthCheck(
            ok=True,
            message=f"Ollama is available and model '{self.model}' is installed.",
            model_name=self.model,
            prompt_version=self.prompt_version,
        )

    def _generate(self, content: str) -> dict[str, Any]:
        prompt = self._build_prompt(content)
        last_error: LocalLLMTransientError | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return self.http_client.generate(
                    base_url=self.base_url,
                    model=self.model,
                    prompt=prompt,
                    timeout_seconds=self.timeout_seconds,
                )
            except LocalLLMTransientError as exc:
                last_error = exc
            except TimeoutError as exc:
                last_error = LocalLLMTransientError("Ollama request timed out.")
                last_error.__cause__ = exc
            except OSError as exc:
                last_error = LocalLLMTransientError("Ollama is unavailable. Is the local server running?")
                last_error.__cause__ = exc
            except LocalLLMExtractorError:
                raise

            if attempt < self.max_retries and self.retry_backoff_seconds > 0:
                self._sleeper(self.retry_backoff_seconds)

        if last_error is not None:
            raise last_error
        raise LocalLLMTransientError("Ollama request failed.")

    def _build_prompt(self, content: str) -> str:
        return f"{self.prompt_template.strip()}\n\nText to extract:\n```\n{content}\n```"

    @staticmethod
    def _extract_response_text(envelope: dict[str, Any]) -> str:
        response = envelope.get("response")
        if not isinstance(response, str) or not response.strip():
            raise LocalLLMResponseError("Ollama returned an empty response.")
        return response.strip()

    @staticmethod
    def _parse_extraction_json(raw_response: str) -> dict[str, Any]:
        try:
            payload = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            raise LocalLLMResponseError("LLM response was not valid JSON.") from exc

        if not isinstance(payload, dict):
            raise LocalLLMResponseError("LLM response JSON must be an object.")
        return payload

    @staticmethod
    def _validate_extraction(payload: dict[str, Any]) -> ExtractionResult:
        try:
            return ExtractionResult(**payload)
        except ValidationError as exc:
            first_error = exc.errors()[0]
            location = ".".join(str(part) for part in first_error["loc"])
            message = first_error["msg"]
            if location:
                raise LocalLLMResponseError(f"LLM response schema is invalid ({location}): {message}") from exc
            raise LocalLLMResponseError(f"LLM response schema is invalid: {message}") from exc

    @staticmethod
    def _load_prompt(prompt_path: Path) -> str:
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")
        return _DEFAULT_PROMPT

    @staticmethod
    def _validate_base_url(base_url: str) -> str:
        value = base_url.strip().rstrip("/")
        parsed = urllib.parse.urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise LocalLLMConfigurationError(
                "Ollama base URL is invalid. Set PIE_OLLAMA_BASE_URL to an http(s) URL."
            )
        return value
