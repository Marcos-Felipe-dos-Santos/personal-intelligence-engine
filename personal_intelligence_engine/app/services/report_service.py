"""Report service — generates daily and other reports."""

from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from personal_intelligence_engine.app.domain.schemas import Report, StructuredEntry
from personal_intelligence_engine.app.repositories.entries_repository import EntriesRepository
from personal_intelligence_engine.app.repositories.reports_repository import ReportsRepository


class ReportService:
    """Generates reports from structured entries."""

    def __init__(
        self,
        entries_repo: EntriesRepository,
        reports_repo: ReportsRepository,
        reports_dir: Path,
        local_timezone: str = "America/Sao_Paulo",
    ) -> None:
        self._entries_repo = entries_repo
        self._reports_repo = reports_repo
        self._reports_dir = reports_dir
        self._local_timezone = ZoneInfo(local_timezone)

    def generate_daily_report(self, date_str: str) -> Report:
        """Generate a daily report for the given date.

        Args:
            date_str: Date in YYYY-MM-DD format.

        Returns:
            The persisted Report with file_path to the generated Markdown.
        """
        date_str = self._validate_date(date_str)
        self._reports_dir.mkdir(parents=True, exist_ok=True)

        # Fetch entries for the local day, while timestamps remain stored in UTC.
        entries = self._get_structured_entries_by_local_date(date_str)
        entry_ids = [e.id for e in entries]

        # Build report content
        md_content = self._render_daily_report(date_str, entries)

        # Write report file
        filename = f"daily_{date_str}.md"
        filepath = self._reports_dir / filename
        filepath.write_text(md_content, encoding="utf-8")

        # Create report record
        summary = self._build_summary(entries)
        report = Report(
            report_type="daily",
            date_start=date_str,
            date_end=date_str,
            summary=summary,
            file_path=str(filepath),
            source_entry_ids_json=json.dumps(entry_ids),
        )

        self._reports_repo.insert(report)
        return report

    @staticmethod
    def _validate_date(date_str: str) -> str:
        """Validate and normalize a YYYY-MM-DD report date."""
        try:
            parsed = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValueError("Invalid date. Use YYYY-MM-DD.") from exc

        if parsed.isoformat() != date_str:
            raise ValueError("Invalid date. Use YYYY-MM-DD.")

        return date_str

    def _get_structured_entries_by_local_date(self, date_str: str) -> list[StructuredEntry]:
        """Fetch structured entries whose UTC timestamps fall within a local day."""
        local_date = date.fromisoformat(date_str)
        local_start = datetime.combine(local_date, time.min, tzinfo=self._local_timezone)
        local_end = datetime.combine(local_date, time.max, tzinfo=self._local_timezone)
        utc_start = local_start.astimezone(timezone.utc)
        utc_end = local_end.astimezone(timezone.utc)

        candidates: list[StructuredEntry] = []
        current_date = utc_start.date()
        while current_date <= utc_end.date():
            candidates.extend(self._entries_repo.get_structured_entries_by_date(current_date.isoformat()))
            current_date += timedelta(days=1)

        return [
            entry
            for entry in candidates
            if utc_start <= self._parse_utc_timestamp(entry.created_at) <= utc_end
        ]

    @staticmethod
    def _parse_utc_timestamp(value: str) -> datetime:
        """Parse an ISO timestamp and normalize it to UTC."""
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    def _render_daily_report(self, date_str: str, entries: list[StructuredEntry]) -> str:
        """Render a daily report as Markdown."""
        lines: list[str] = []

        lines.append(f"# Daily Report — {date_str}")
        lines.append("")
        lines.append(f"**Total entries:** {len(entries)}")
        lines.append("")

        if not entries:
            lines.append("No entries recorded for this date.")
            lines.append("")
            return "\n".join(lines)

        # Group by type
        by_type: dict[str, list[StructuredEntry]] = {}
        for entry in entries:
            t = entry.entry_type.value if hasattr(entry.entry_type, "value") else str(entry.entry_type)
            by_type.setdefault(t, []).append(entry)

        # Summary table
        lines.append("## Summary by Type")
        lines.append("")
        lines.append("| Type | Count |")
        lines.append("|------|-------|")
        for entry_type, type_entries in sorted(by_type.items()):
            lines.append(f"| {entry_type} | {len(type_entries)} |")
        lines.append("")

        # Entries detail
        lines.append("## Entries")
        lines.append("")
        for entry in entries:
            entry_type_val = entry.entry_type.value if hasattr(entry.entry_type, "value") else str(entry.entry_type)
            validation_val = entry.validation_status.value if hasattr(entry.validation_status, "value") else str(entry.validation_status)
            lines.append(f"### [{entry_type_val}] {entry.summary}")
            lines.append("")
            lines.append(f"- **Structured Entry ID:** `{entry.id}`")
            lines.append(f"- **Raw Entry ID:** `{entry.raw_entry_id}`")
            lines.append(f"- **Confidence:** {entry.confidence:.0%}")
            lines.append(f"- **Status:** {validation_val}")
            if entry.project:
                lines.append(f"- **Project:** {entry.project}")
            lines.append("")

        # Source IDs
        lines.append("## Source Entry IDs")
        lines.append("")
        for entry in entries:
            lines.append(f"- Structured Entry ID: `{entry.id}`")
            lines.append(f"  Raw Entry ID: `{entry.raw_entry_id}`")
        lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _build_summary(entries: list[StructuredEntry]) -> str:
        """Build a text summary for the report record."""
        if not entries:
            return "No entries for this date."
        types = set()
        for e in entries:
            t = e.entry_type.value if hasattr(e.entry_type, "value") else str(e.entry_type)
            types.add(t)
        return f"{len(entries)} entries across types: {', '.join(sorted(types))}."
