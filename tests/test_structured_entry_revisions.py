"""Tests for structured entry revision snapshots."""

import json

import pytest
from pydantic import ValidationError

from personal_intelligence_engine.app.domain.schemas import (
    StructuredEntryRevision,
    StructuredEntryRevisionCreate,
)
from personal_intelligence_engine.app.repositories.revisions_repository import RevisionsRepository


def _snapshot(**overrides) -> str:
    payload = {
        "entry_type": "general_note",
        "project": None,
        "summary": "Synthetic summary before edit.",
        "confidence": 0.5,
        "tags": ["synthetic"],
        "structured_json": "{}",
    }
    payload.update(overrides)
    return json.dumps(payload)


def test_structured_entry_revision_schema_accepts_valid_json():
    revision = StructuredEntryRevisionCreate(
        structured_entry_id="structured-id",
        raw_entry_id="raw-id",
        before_json=_snapshot(summary="Before"),
        after_json=_snapshot(summary="After"),
        changed_fields_json=json.dumps(["summary"]),
        reason="Synthetic correction.",
        actor="user",
    )

    assert revision.structured_entry_id == "structured-id"
    assert revision.raw_entry_id == "raw-id"


def test_structured_entry_revision_schema_rejects_invalid_json():
    with pytest.raises(ValidationError):
        StructuredEntryRevisionCreate(
            structured_entry_id="structured-id",
            raw_entry_id="raw-id",
            before_json="{invalid",
            after_json=_snapshot(summary="After"),
            changed_fields_json=json.dumps(["summary"]),
            actor="user",
        )


def test_structured_entry_revision_schema_rejects_raw_content_snapshot():
    with pytest.raises(ValidationError):
        StructuredEntryRevisionCreate(
            structured_entry_id="structured-id",
            raw_entry_id="raw-id",
            before_json=json.dumps({"raw_content": "Synthetic raw content"}),
            after_json=_snapshot(summary="After"),
            changed_fields_json=json.dumps(["summary"]),
            actor="user",
        )


def test_revisions_repository_creates_and_lists_revisions(app):
    result = app.add_entry("Nota sintetica sem projeto claro")
    structured_id = result["structured_entry_id"]
    raw_id = result["entry_id"]
    repository = RevisionsRepository(app.db)
    revision = StructuredEntryRevision(
        structured_entry_id=structured_id,
        raw_entry_id=raw_id,
        before_json=_snapshot(summary="Before"),
        after_json=_snapshot(summary="After"),
        changed_fields_json=json.dumps(["summary"]),
        reason="Synthetic correction.",
        actor="user",
    )

    repository.create_revision(revision)

    revisions = repository.list_revisions_for_structured_entry(structured_id)
    assert len(revisions) == 1
    assert revisions[0].id == revision.id
    assert revisions[0].structured_entry_id == structured_id
    assert revisions[0].raw_entry_id == raw_id
    assert json.loads(revisions[0].before_json)["summary"] == "Before"
    assert json.loads(revisions[0].after_json)["summary"] == "After"


def test_revision_snapshots_do_not_duplicate_raw_content(app):
    raw_content = "Nota sintetica privada apenas para teste"
    result = app.add_entry(raw_content)
    repository = RevisionsRepository(app.db)
    revision = StructuredEntryRevision(
        structured_entry_id=result["structured_entry_id"],
        raw_entry_id=result["entry_id"],
        before_json=_snapshot(summary="Before"),
        after_json=_snapshot(summary="After"),
        changed_fields_json=json.dumps(["summary"]),
        actor="user",
    )

    repository.create_revision(revision)
    revisions = repository.list_revisions_for_structured_entry(result["structured_entry_id"])

    assert raw_content not in revisions[0].before_json
    assert raw_content not in revisions[0].after_json
    assert raw_content not in revisions[0].changed_fields_json
