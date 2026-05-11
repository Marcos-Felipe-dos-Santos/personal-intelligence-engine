"""Tests for daily report generation."""

from pathlib import Path

import pytest


def _get_entry_date(app, entry_id: str) -> str:
    """Extract the date portion from a structured entry's created_at."""
    structured = app.entries_repo.get_structured_entry_by_raw_id(entry_id)
    if structured:
        return structured.created_at[:10]
    return ""


class TestDailyReport:
    """Tests for daily report generation."""

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

    def test_report_cites_source_ids(self, app):
        """The report file cites the source entry IDs."""
        r1 = app.add_entry("Preciso fazer o deploy")
        date_str = _get_entry_date(app, r1["entry_id"])

        result = app.generate_daily_report(date_str)
        report_content = Path(result["file_path"]).read_text(encoding="utf-8")

        # Report should contain the structured entry ID
        structured = app.entries_repo.get_structured_entry_by_raw_id(r1["entry_id"])
        assert structured.id in report_content

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
