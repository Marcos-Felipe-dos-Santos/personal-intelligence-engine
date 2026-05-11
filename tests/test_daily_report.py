"""Tests for daily report generation."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from personal_intelligence_engine.app.config import Config
from personal_intelligence_engine.app.domain.schemas import RawEntry, StructuredEntry
from personal_intelligence_engine.app.domain.types import EntryType, ValidationStatus


def _get_entry_date(app, entry_id: str) -> str:
    """Extract the date portion from a structured entry's created_at."""
    structured = app.entries_repo.get_structured_entry_by_raw_id(entry_id)
    if structured:
        return structured.created_at[:10]
    return ""


def _insert_structured_entry_at(app, *, raw_id: str, structured_id: str, created_at: str, summary: str) -> None:
    raw = RawEntry(
        id=raw_id,
        content=f"Synthetic raw content for {raw_id}",
        source="test",
        created_at=created_at,
        updated_at=created_at,
        content_hash="a" * 64,
    )
    app.entries_repo.insert_raw_entry(raw)
    app.entries_repo.insert_structured_entry(
        StructuredEntry(
            id=structured_id,
            raw_entry_id=raw_id,
            entry_type=EntryType.LOG,
            summary=summary,
            confidence=0.8,
            structured_json="{}",
            validation_status=ValidationStatus.VALID,
            created_at=created_at,
            updated_at=created_at,
        )
    )


class TestDailyReport:
    """Tests for daily report generation."""

    def test_default_timezone_is_sao_paulo(self, monkeypatch):
        """The default local report timezone is America/Sao_Paulo."""
        monkeypatch.delenv("PIE_LOCAL_TIMEZONE", raising=False)

        config = Config()

        assert config.local_timezone == "America/Sao_Paulo"

    def test_custom_timezone_env_is_accepted(self, monkeypatch):
        """A custom IANA timezone can be configured through PIE_LOCAL_TIMEZONE."""
        monkeypatch.setenv("PIE_LOCAL_TIMEZONE", "UTC")

        config = Config()

        assert config.local_timezone == "UTC"

    def test_invalid_timezone_is_rejected(self):
        """Invalid timezones fail with a controlled error."""
        with pytest.raises(ValueError, match="Invalid local timezone"):
            Config(local_timezone="Invalid/Timezone")

    def test_report_is_generated(self, app):
        """A daily report file is created."""
        r1 = app.add_entry("Primeira entrada do dia")
        date_str = _get_entry_date(app, r1["entry_id"])

        result = app.generate_daily_report(date_str)
        assert result["status"] == "ok"
        assert Path(result["file_path"]).exists()

    def test_report_contains_entries(self, app):
        """The report includes entries from the specified date."""
        r1 = app.add_entry("Decidi usar SQLite")
        app.add_entry("Tive uma ideia para o cache")
        date_str = _get_entry_date(app, r1["entry_id"])

        result = app.generate_daily_report(date_str)
        assert result["entry_count"] >= 2

    def test_report_date_uses_local_timezone_boundary(self, app):
        """A UTC timestamp near midnight is included in the correct local day."""
        _insert_structured_entry_at(
            app,
            raw_id="raw-local-previous-day",
            structured_id="structured-local-previous-day",
            created_at=datetime(2026, 5, 10, 2, 30, tzinfo=timezone.utc).isoformat(),
            summary="Synthetic entry that is still May 9 in Sao Paulo.",
        )
        _insert_structured_entry_at(
            app,
            raw_id="raw-local-current-day",
            structured_id="structured-local-current-day",
            created_at=datetime(2026, 5, 10, 12, 0, tzinfo=timezone.utc).isoformat(),
            summary="Synthetic entry that is May 10 in Sao Paulo.",
        )

        previous_day_report = app.generate_daily_report("2026-05-09")
        previous_content = Path(previous_day_report["file_path"]).read_text(encoding="utf-8")
        current_day_report = app.generate_daily_report("2026-05-10")
        current_content = Path(current_day_report["file_path"]).read_text(encoding="utf-8")

        assert previous_day_report["entry_count"] == 1
        assert "structured-local-previous-day" in previous_content
        assert "raw-local-previous-day" in previous_content
        assert "structured-local-current-day" not in previous_content

        assert current_day_report["entry_count"] == 1
        assert "structured-local-current-day" in current_content
        assert "raw-local-current-day" in current_content
        assert "structured-local-previous-day" not in current_content

    def test_report_cites_structured_and_raw_source_ids(self, app):
        """The report file cites structured and raw source entry IDs."""
        r1 = app.add_entry("Preciso fazer o deploy")
        date_str = _get_entry_date(app, r1["entry_id"])

        result = app.generate_daily_report(date_str)
        report_content = Path(result["file_path"]).read_text(encoding="utf-8")

        structured = app.entries_repo.get_structured_entry_by_raw_id(r1["entry_id"])
        assert "Structured Entry ID" in report_content
        assert "Raw Entry ID" in report_content
        assert structured.id in report_content
        assert structured.raw_entry_id in report_content
        assert r1["entry_id"] in report_content

    def test_report_has_summary_table(self, app):
        """The report contains a summary table by type."""
        app.add_entry("Eu decidi algo importante")
        app.add_entry("Tive uma ideia genial")

        r = app.add_entry("Outra entrada")
        date_str = _get_entry_date(app, r["entry_id"])

        result = app.generate_daily_report(date_str)
        content = Path(result["file_path"]).read_text(encoding="utf-8")
        assert "Summary by Type" in content
        assert "| Type |" in content

    def test_empty_date_report(self, app):
        """Report for a date with no entries is still generated."""
        result = app.generate_daily_report("2000-01-01")
        assert result["status"] == "ok"
        assert result["entry_count"] == 0

        content = Path(result["file_path"]).read_text(encoding="utf-8")
        assert "No entries" in content

    def test_invalid_date_rejected(self, app):
        """Invalid dates are rejected instead of creating arbitrary report paths."""
        with pytest.raises(ValueError, match="Invalid date"):
            app.generate_daily_report("2026-99-99")

    def test_report_does_not_invent_data(self, app):
        """Report only contains data from actual entries."""
        r1 = app.add_entry("Decidi usar Pydantic")
        date_str = _get_entry_date(app, r1["entry_id"])

        result = app.generate_daily_report(date_str)
        content = Path(result["file_path"]).read_text(encoding="utf-8")

        # Should not contain fabricated data
        assert "OpenAI" not in content
        assert "GPT" not in content

    def test_report_stored_in_database(self, app):
        """Report record is persisted in the database."""
        r1 = app.add_entry("Entrada de teste")
        date_str = _get_entry_date(app, r1["entry_id"])

        result = app.generate_daily_report(date_str)
        report = app.reports_repo.get_by_date_range("daily", date_str, date_str)
        assert report is not None
        assert report.id == result["report_id"]

    def test_no_real_data_needed(self, app):
        """Tests work without any real personal data."""
        # All data is synthetic — this test confirms the pattern works
        result = app.add_entry("Entrada sintética de teste para validação")
        date_str = _get_entry_date(app, result["entry_id"])
        report = app.generate_daily_report(date_str)
        assert report["status"] == "ok"
