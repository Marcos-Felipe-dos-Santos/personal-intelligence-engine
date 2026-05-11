"""Pydantic schemas for PIE domain models."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from personal_intelligence_engine.app.domain.types import (
    AuditAction,
    AuditStatus,
    EntryStatus,
    EntryType,
    ValidationStatus,
)


def _utc_now() -> str:
    """Return current UTC timestamp as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    """Generate a new UUID string."""
    return str(uuid4())


def _validate_json_string(value: str | None, field_name: str) -> str | None:
    """Validate optional JSON stored as text fields."""
    if value is None:
        return None
    try:
        json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{field_name} must contain valid JSON") from exc
    return value


# ---------------------------------------------------------------------------
# Raw Entry
# ---------------------------------------------------------------------------

class RawEntryCreate(BaseModel):
    """Input schema for creating a raw entry."""

    content: str = Field(..., min_length=1)
    source: str = Field(default="cli")
    metadata_json: str | None = None

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("content must not be empty")
        return v

    @field_validator("metadata_json")
    @classmethod
    def validate_metadata_json(cls, v: str | None) -> str | None:
        return _validate_json_string(v, "metadata_json")


class RawEntry(BaseModel):
    """Full raw entry as stored in the database."""

    id: str = Field(default_factory=_new_id)
    content: str
    source: str
    status: EntryStatus = EntryStatus.PENDING
    created_at: str = Field(default_factory=_utc_now)
    updated_at: str = Field(default_factory=_utc_now)
    metadata_json: str | None = None
    content_hash: str = ""

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("content must not be empty")
        return v

    @field_validator("metadata_json")
    @classmethod
    def validate_metadata_json(cls, v: str | None) -> str | None:
        return _validate_json_string(v, "metadata_json")


# ---------------------------------------------------------------------------
# Structured Entry
# ---------------------------------------------------------------------------

class StructuredEntryCreate(BaseModel):
    """Schema for creating a structured entry from extraction output."""

    raw_entry_id: str
    entry_type: EntryType
    project: str | None = None
    summary: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)
    structured_json: str = Field(default="{}")
    validation_status: ValidationStatus = ValidationStatus.VALID

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if v < 0.0 or v > 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return v

    @field_validator("structured_json")
    @classmethod
    def validate_structured_json(cls, v: str) -> str:
        return _validate_json_string(v, "structured_json") or "{}"


class StructuredEntry(BaseModel):
    """Full structured entry as stored in the database."""

    id: str = Field(default_factory=_new_id)
    raw_entry_id: str
    entry_type: EntryType
    project: str | None = None
    summary: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    structured_json: str = "{}"
    validation_status: ValidationStatus = ValidationStatus.VALID
    created_at: str = Field(default_factory=_utc_now)
    updated_at: str = Field(default_factory=_utc_now)

    @field_validator("structured_json")
    @classmethod
    def validate_structured_json(cls, v: str) -> str:
        return _validate_json_string(v, "structured_json") or "{}"


# ---------------------------------------------------------------------------
# Extraction Result (output from extractors)
# ---------------------------------------------------------------------------

class ExtractionResult(BaseModel):
    """Output from an extractor (fake or LLM)."""

    entry_type: EntryType
    project: str | None = None
    summary: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)

    def to_structured_json(self) -> str:
        """Serialize the full extraction result to JSON string."""
        return json.dumps(
            {
                "entry_type": self.entry_type.value,
                "project": self.project,
                "summary": self.summary,
                "confidence": self.confidence,
                "tags": self.tags,
                "extra": self.extra,
            },
            ensure_ascii=False,
        )


# ---------------------------------------------------------------------------
# Audit Log
# ---------------------------------------------------------------------------

class AuditLogCreate(BaseModel):
    """Schema for creating an audit log entry."""

    raw_entry_id: str | None = None
    action: AuditAction
    actor: str = "system"
    method: str | None = None
    model_name: str | None = None
    prompt_version: str | None = None
    input_hash: str | None = None
    output_hash: str | None = None
    status: AuditStatus = AuditStatus.SUCCESS
    error_message: str | None = None


class AuditLog(BaseModel):
    """Full audit log as stored in the database."""

    id: str = Field(default_factory=_new_id)
    raw_entry_id: str | None = None
    action: AuditAction
    actor: str = "system"
    method: str | None = None
    model_name: str | None = None
    prompt_version: str | None = None
    input_hash: str | None = None
    output_hash: str | None = None
    status: AuditStatus = AuditStatus.SUCCESS
    error_message: str | None = None
    created_at: str = Field(default_factory=_utc_now)


# ---------------------------------------------------------------------------
# Generated File
# ---------------------------------------------------------------------------

class GeneratedFile(BaseModel):
    """Record of a generated file (Markdown note, report, etc.)."""

    id: str = Field(default_factory=_new_id)
    raw_entry_id: str | None = None
    file_type: str
    path: str
    content_hash: str | None = None
    created_at: str = Field(default_factory=_utc_now)


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

class ReportCreate(BaseModel):
    """Schema for creating a report."""

    report_type: str = "daily"
    date_start: str
    date_end: str
    summary: str
    file_path: str | None = None
    source_entry_ids_json: str = "[]"

    @field_validator("source_entry_ids_json")
    @classmethod
    def validate_source_entry_ids_json(cls, v: str) -> str:
        return _validate_json_string(v, "source_entry_ids_json") or "[]"


class Report(BaseModel):
    """Full report as stored in the database."""

    id: str = Field(default_factory=_new_id)
    report_type: str = "daily"
    date_start: str
    date_end: str
    summary: str
    file_path: str | None = None
    source_entry_ids_json: str = "[]"
    created_at: str = Field(default_factory=_utc_now)

    @field_validator("source_entry_ids_json")
    @classmethod
    def validate_source_entry_ids_json(cls, v: str) -> str:
        return _validate_json_string(v, "source_entry_ids_json") or "[]"
