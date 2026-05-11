"""Repository for reports table."""

from __future__ import annotations

from personal_intelligence_engine.app.domain.schemas import Report
from personal_intelligence_engine.app.repositories.database import Database


class ReportsRepository:
    """Persistence operations for reports."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def insert(self, report: Report) -> None:
        """Insert a new report record."""
        self._db.execute(
            """
            INSERT INTO reports
                (id, report_type, date_start, date_end, summary, file_path,
                 source_entry_ids_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                report.id,
                report.report_type,
                report.date_start,
                report.date_end,
                report.summary,
                report.file_path,
                report.source_entry_ids_json,
                report.created_at,
            ),
        )
        self._db.commit()

    def get_by_date_range(self, report_type: str, date_start: str, date_end: str) -> Report | None:
        """Fetch a report by type and date range."""
        row = self._db.fetchone(
            "SELECT * FROM reports WHERE report_type = ? AND date_start = ? AND date_end = ?;",
            (report_type, date_start, date_end),
        )
        if row is None:
            return None
        return Report(**dict(row))
