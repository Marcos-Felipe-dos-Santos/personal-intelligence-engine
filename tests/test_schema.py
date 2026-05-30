"""Tests for Pydantic schemas."""

import pytest
from pydantic import ValidationError

from personal_intelligence_engine.app.domain.schemas import (
    ExtractionResult,
    RawEntry,
    RawEntryCreate,
    Report,
    StructuredEntryCreate,
)
from personal_intelligence_engine.app.domain.types import EntryType


class TestRawEntryCreate:
    """Tests for RawEntryCreate schema."""

    def test_valid_entry(self):
        entry = RawEntryCreate(content="Test content", source="cli")
        assert entry.content == "Test content"
        assert entry.source == "cli"

    def test_empty_content_rejected(self):
        with pytest.raises(ValidationError):
            RawEntryCreate(content="", source="cli")

    def test_blank_content_rejected(self):
        with pytest.raises(ValidationError):
            RawEntryCreate(content="   ", source="cli")

    def test_invalid_metadata_json_rejected(self):
        with pytest.raises(ValidationError):
            RawEntryCreate(content="Test", source="cli", metadata_json="{invalid")

    def test_default_source(self):
        entry = RawEntryCreate(content="Test")
        assert entry.source == "cli"


class TestRawEntry:
    """Tests for persisted RawEntry schema."""

    def test_empty_content_hash_is_valid(self):
        entry = RawEntry(content="x", source="cli", content_hash="")
        assert entry.content_hash == ""

    def test_sixty_four_character_content_hash_is_valid(self):
        entry = RawEntry(content="x", source="cli", content_hash="a" * 64)
        assert entry.content_hash == "a" * 64

    def test_short_content_hash_is_rejected(self):
        with pytest.raises(
            ValidationError,
            match="content_hash must be exactly 64 hex characters",
        ):
            RawEntry(content="x", source="cli", content_hash="short")


class TestStructuredEntryCreate:
    """Tests for StructuredEntryCreate schema."""

    def test_valid_entry(self):
        entry = StructuredEntryCreate(
            raw_entry_id="test-id",
            entry_type=EntryType.IDEA,
            summary="A great idea",
            confidence=0.85,
        )
        assert entry.entry_type == EntryType.IDEA
        assert entry.confidence == 0.85

    def test_invalid_entry_type_rejected(self):
        with pytest.raises(ValidationError):
            StructuredEntryCreate(
                raw_entry_id="test-id",
                entry_type="invalid_type",
                summary="Test",
                confidence=0.5,
            )

    def test_confidence_below_zero_rejected(self):
        with pytest.raises(ValidationError):
            StructuredEntryCreate(
                raw_entry_id="test-id",
                entry_type=EntryType.LOG,
                summary="Test",
                confidence=-0.1,
            )

    def test_confidence_above_one_rejected(self):
        with pytest.raises(ValidationError):
            StructuredEntryCreate(
                raw_entry_id="test-id",
                entry_type=EntryType.LOG,
                summary="Test",
                confidence=1.1,
            )

    def test_confidence_at_boundaries(self):
        # Exactly 0.0 should be valid
        entry_zero = StructuredEntryCreate(
            raw_entry_id="test-id",
            entry_type=EntryType.LOG,
            summary="Test",
            confidence=0.0,
        )
        assert entry_zero.confidence == 0.0

        # Exactly 1.0 should be valid
        entry_one = StructuredEntryCreate(
            raw_entry_id="test-id",
            entry_type=EntryType.LOG,
            summary="Test",
            confidence=1.0,
        )
        assert entry_one.confidence == 1.0

    def test_invalid_structured_json_rejected(self):
        with pytest.raises(ValidationError):
            StructuredEntryCreate(
                raw_entry_id="test-id",
                entry_type=EntryType.LOG,
                summary="Test",
                confidence=0.5,
                structured_json="{invalid",
            )

    def test_all_entry_types_accepted(self):
        for entry_type in EntryType:
            entry = StructuredEntryCreate(
                raw_entry_id="test-id",
                entry_type=entry_type,
                summary="Test",
                confidence=0.5,
            )
            assert entry.entry_type == entry_type


class TestExtractionResult:
    """Tests for ExtractionResult schema."""

    def test_to_structured_json(self):
        result = ExtractionResult(
            entry_type=EntryType.IDEA,
            summary="Test idea",
            confidence=0.85,
            tags=["idea", "test"],
        )
        json_str = result.to_structured_json()
        assert '"entry_type": "idea"' in json_str
        assert '"summary": "Test idea"' in json_str


class TestReport:
    """Tests for report schemas."""

    def test_invalid_source_entry_ids_json_rejected(self):
        with pytest.raises(ValidationError):
            Report(
                date_start="2026-05-09",
                date_end="2026-05-09",
                summary="Test",
                source_entry_ids_json="{invalid",
            )
