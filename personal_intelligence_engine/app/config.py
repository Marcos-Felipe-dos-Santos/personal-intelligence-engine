"""Application configuration for PIE."""

from __future__ import annotations

import os
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv

# Load .env from project root if available
_project_root = Path(__file__).resolve().parent.parent.parent
_env_file = _project_root / ".env"
if _env_file.exists():
    load_dotenv(_env_file)


class Config:
    """Central configuration — reads from environment with sensible defaults."""

    def __init__(
        self,
        database_path: str | Path | None = None,
        notes_dir: str | Path | None = None,
        reports_dir: str | Path | None = None,
        migrations_dir: str | Path | None = None,
        log_level: str | None = None,
        extractor_backend: str | None = None,
        ollama_base_url: str | None = None,
        ollama_model: str | None = None,
        llm_timeout_seconds: int | float | str | None = None,
        llm_max_retries: int | str | None = None,
        llm_retry_backoff_seconds: int | float | str | None = None,
        local_timezone: str | None = None,
        backup_dir: str | Path | None = None,
        export_dir: str | Path | None = None,
        allow_remote_ollama: bool | str | None = None,
        pie_home: str | Path | None = None,
    ) -> None:
        raw_home = pie_home or os.getenv("PIE_HOME")
        if raw_home:
            self.pie_home: Path | None = Path(raw_home).expanduser().resolve()
        else:
            self.pie_home = None

        self.database_path = self._resolve_path(database_path, "PIE_DATABASE_PATH", "pie.db")
        self.notes_dir = self._resolve_path(notes_dir, "PIE_NOTES_DIR", "notes")
        self.reports_dir = self._resolve_path(reports_dir, "PIE_REPORTS_DIR", "reports")
        self.migrations_dir = Path(migrations_dir or _project_root / "migrations")
        self.backup_dir = self._resolve_path(backup_dir, "PIE_BACKUP_DIR", "backups")
        self.export_dir = self._resolve_path(export_dir, "PIE_EXPORT_DIR", "exports")
        self.log_level = log_level or os.getenv("PIE_LOG_LEVEL", "INFO")
        self.extractor_backend = (extractor_backend or os.getenv("PIE_EXTRACTOR_BACKEND", "fake")).strip().lower()
        self.ollama_base_url = (ollama_base_url or os.getenv("PIE_OLLAMA_BASE_URL", "http://localhost:11434")).strip()
        self.ollama_model = (ollama_model if ollama_model is not None else os.getenv("PIE_OLLAMA_MODEL", "")).strip()
        self.llm_timeout_seconds = self._parse_timeout(
            llm_timeout_seconds if llm_timeout_seconds is not None else os.getenv("PIE_LLM_TIMEOUT_SECONDS", "30")
        )
        self.llm_max_retries = self._parse_non_negative_int(
            llm_max_retries if llm_max_retries is not None else os.getenv("PIE_LLM_MAX_RETRIES", "2"),
            "PIE_LLM_MAX_RETRIES",
        )
        self.llm_retry_backoff_seconds = self._parse_non_negative_float(
            (
                llm_retry_backoff_seconds
                if llm_retry_backoff_seconds is not None
                else os.getenv("PIE_LLM_RETRY_BACKOFF_SECONDS", "1")
            ),
            "PIE_LLM_RETRY_BACKOFF_SECONDS",
        )
        self.local_timezone = self._validate_timezone(
            local_timezone or os.getenv("PIE_LOCAL_TIMEZONE", "America/Sao_Paulo")
        )
        self.allow_remote_ollama = self._parse_bool(
            allow_remote_ollama if allow_remote_ollama is not None else os.getenv("PIE_ALLOW_REMOTE_OLLAMA", "false")
        )

    def _resolve_path(self, value: str | Path | None, env_var: str, default_name: str) -> Path:
        raw = value or os.getenv(env_var, default_name)
        p = Path(raw)
        if p.is_absolute():
            return p
        if self.pie_home:
            return self.pie_home / p
        return p

    def ensure_dirs(self) -> None:
        """Create output directories if they don't exist."""
        if self.database_path.parent != self.database_path:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.notes_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.export_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _parse_timeout(value: int | float | str) -> float:
        """Parse a positive timeout value in seconds."""
        try:
            timeout = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("PIE_LLM_TIMEOUT_SECONDS must be a positive number.") from exc
        if timeout <= 0:
            raise ValueError("PIE_LLM_TIMEOUT_SECONDS must be a positive number.")
        return timeout

    @staticmethod
    def _parse_non_negative_int(value: int | str, name: str) -> int:
        """Parse a non-negative integer setting."""
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} must be a non-negative integer.") from exc
        if parsed < 0:
            raise ValueError(f"{name} must be a non-negative integer.")
        return parsed

    @staticmethod
    def _parse_non_negative_float(value: int | float | str, name: str) -> float:
        """Parse a non-negative float setting."""
        try:
            parsed = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} must be a non-negative number.") from exc
        if parsed < 0:
            raise ValueError(f"{name} must be a non-negative number.")
        return parsed

    @staticmethod
    def _parse_bool(value: bool | str) -> bool:
        """Parse a boolean-ish setting; anything outside true/1/yes → False."""
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"true", "1", "yes"}

    @staticmethod
    def _validate_timezone(value: str) -> str:
        """Validate an IANA timezone name."""
        timezone_name = value.strip()
        try:
            ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(
                f"Invalid local timezone '{timezone_name}'. Set PIE_LOCAL_TIMEZONE to a valid IANA timezone."
            ) from exc
        return timezone_name
