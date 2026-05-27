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
        return self._get_structured_entries_by_local_range(local_date, local_date)

    def _get_structured_entries_by_local_range(self, start_date: date, end_date: date) -> list[StructuredEntry]:
        """Fetch structured entries whose UTC timestamps fall within a local date range."""
        local_start = datetime.combine(start_date, time.min, tzinfo=self._local_timezone)
        local_end = datetime.combine(end_date, time.max, tzinfo=self._local_timezone)
        utc_start = local_start.astimezone(timezone.utc)
        utc_end = local_end.astimezone(timezone.utc)

        candidates: list[StructuredEntry] = []
        current_date = utc_start.date()
        while current_date <= utc_end.date():
            candidates.extend(self._entries_repo.get_structured_entries_by_date(current_date.isoformat()))
            current_date += timedelta(days=1)

        seen = set()
        unique_candidates = []
        for entry in candidates:
            if entry.id not in seen:
                seen.add(entry.id)
                unique_candidates.append(entry)

        return [
            entry
            for entry in unique_candidates
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

    def generate_weekly_report(self, date_str: str) -> Report:
        """Generate a weekly report for the week containing the given date.

        Args:
            date_str: Date in YYYY-MM-DD format within the desired week.

        Returns:
            The persisted Report with file_path to the generated Markdown.
        """
        date_str = self._validate_date(date_str)
        self._reports_dir.mkdir(parents=True, exist_ok=True)

        local_date = date.fromisoformat(date_str)
        # Week runs Monday (weekday = 0) to Sunday (weekday = 6)
        monday = local_date - timedelta(days=local_date.weekday())
        sunday = monday + timedelta(days=6)
        monday_str = monday.isoformat()
        sunday_str = sunday.isoformat()

        entries = self._get_structured_entries_by_local_range(monday, sunday)
        entry_ids = [e.id for e in entries]

        md_content = self._render_weekly_report(monday_str, sunday_str, entries)

        filename = f"weekly_{monday_str}_to_{sunday_str}.md"
        filepath = self._reports_dir / filename
        filepath.write_text(md_content, encoding="utf-8")

        summary = self._build_summary(entries)
        report = Report(
            report_type="weekly",
            date_start=monday_str,
            date_end=sunday_str,
            summary=summary,
            file_path=str(filepath),
            source_entry_ids_json=json.dumps(entry_ids),
        )

        self._reports_repo.insert(report)
        return report

    def _render_weekly_report(self, monday_str: str, sunday_str: str, entries: list[StructuredEntry]) -> str:
        """Render a weekly report as Markdown."""
        lines: list[str] = []

        lines.append(f"# Weekly Report — {monday_str} to {sunday_str}")
        lines.append("")
        lines.append(f"**Week Interval:** Monday {monday_str} to Sunday {sunday_str}")
        lines.append(f"**Total entries:** {len(entries)}")
        lines.append("")

        if not entries:
            lines.append("No entries recorded for this week.")
            lines.append("")
            lines.append("## Limitations Warning")
            lines.append("")
            lines.append("This report is based entirely on local data captured during the specified period. It does not reflect external integrations or uncaptured activities.")
            lines.append("")
            return "\n".join(lines)

        # Group by type
        by_type: dict[str, list[StructuredEntry]] = {}
        valid_count = 0
        needs_review_count = 0
        for entry in entries:
            t = entry.entry_type.value if hasattr(entry.entry_type, "value") else str(entry.entry_type)
            by_type.setdefault(t, []).append(entry)

            val_status = entry.validation_status.value if hasattr(entry.validation_status, "value") else str(entry.validation_status)
            if val_status == "needs_review":
                needs_review_count += 1
            else:
                valid_count += 1

        # Summary table
        lines.append("## Summary by Type")
        lines.append("")
        lines.append("| Type | Count |")
        lines.append("|------|-------|")
        for entry_type, type_entries in sorted(by_type.items()):
            lines.append(f"| {entry_type} | {len(type_entries)} |")
        lines.append("")

        # Validation status counts
        lines.append("## Validation Status")
        lines.append("")
        lines.append(f"- **Approved/Valid entries:** {valid_count}")
        lines.append(f"- **Needs Review entries:** {needs_review_count}")
        lines.append("")

        # Sections for specific types
        sections = [
            ("Decisions", "decision", "No decisions recorded."),
            ("Problems", "problem", "No problems recorded."),
            ("Candidate Tasks", "candidate_task", "No candidate tasks recorded."),
            ("References", "reference", "No references recorded."),
        ]

        for title, type_key, empty_msg in sections:
            lines.append(f"## {title}")
            lines.append("")
            type_entries = by_type.get(type_key, [])
            if not type_entries:
                lines.append(empty_msg)
                lines.append("")
                continue

            for entry in type_entries:
                lines.append(f"### {entry.summary}")
                lines.append("")
                lines.append(f"- **Structured Entry ID:** `{entry.id}`")
                lines.append(f"- **Raw Entry ID:** `{entry.raw_entry_id}`")
                lines.append(f"- **Confidence:** {entry.confidence:.0%}")
                lines.append(f"- **Status:** {entry.validation_status.value}")
                if entry.project:
                    lines.append(f"- **Project:** {entry.project}")
                lines.append("")

        # Source Entry IDs
        lines.append("## Source Entry IDs")
        lines.append("")
        for entry in entries:
            lines.append(f"- Structured Entry ID: `{entry.id}`")
            lines.append(f"  Raw Entry ID: `{entry.raw_entry_id}`")
        lines.append("")

        # Limitations Warning
        lines.append("## Limitations Warning")
        lines.append("")
        lines.append("This report is based entirely on local data captured during the specified period. It does not reflect external integrations or uncaptured activities.")
        lines.append("")

        return "\n".join(lines)

    def generate_project_report(self, project: str) -> Report:
        """Generate a report for the structured entries of a specific project.

        Args:
            project: The name of the project.

        Returns:
            The persisted Report with file_path to the generated Markdown.
        """
        if not project.strip():
            raise ValueError("Project name cannot be empty.")
        self._reports_dir.mkdir(parents=True, exist_ok=True)

        entries = self._entries_repo.get_structured_entries_by_project(project)
        entry_ids = [e.id for e in entries]

        md_content = self._render_project_report(project, entries)

        # Sanitize project name for filename safety
        import re
        sanitized_project = re.sub(r'[^a-zA-Z0-9_\-]', '_', project)
        filename = f"project_{sanitized_project}.md"
        filepath = self._reports_dir / filename
        filepath.write_text(md_content, encoding="utf-8")

        # Create report record
        today_local_str = datetime.now(self._local_timezone).date().isoformat()
        summary = self._build_summary(entries)
        report = Report(
            report_type="project",
            date_start=today_local_str,
            date_end=today_local_str,
            summary=f"Project: {project}. {summary}",
            file_path=str(filepath),
            source_entry_ids_json=json.dumps(entry_ids),
        )

        self._reports_repo.insert(report)
        return report

    def _render_project_report(self, project: str, entries: list[StructuredEntry]) -> str:
        """Render a project report as Markdown."""
        lines: list[str] = []

        lines.append(f"# Project Report — {project}")
        lines.append("")
        lines.append(f"**Project:** {project}")
        lines.append(f"**Total entries:** {len(entries)}")
        lines.append("")

        if not entries:
            lines.append("No entries recorded for this project.")
            lines.append("")
            lines.append("## Limitations Warning")
            lines.append("")
            lines.append("This report is based entirely on local data captured for the specified project. It does not reflect external integrations or uncaptured activities.")
            lines.append("")
            return "\n".join(lines)

        # Group by type
        by_type: dict[str, list[StructuredEntry]] = {}
        needs_review_entries = []
        for entry in entries:
            t = entry.entry_type.value if hasattr(entry.entry_type, "value") else str(entry.entry_type)
            by_type.setdefault(t, []).append(entry)

            val_status = entry.validation_status.value if hasattr(entry.validation_status, "value") else str(entry.validation_status)
            if val_status == "needs_review":
                needs_review_entries.append(entry)

        # Summary table
        lines.append("## Summary by Type")
        lines.append("")
        lines.append("| Type | Count |")
        lines.append("|------|-------|")
        for entry_type, type_entries in sorted(by_type.items()):
            lines.append(f"| {entry_type} | {len(type_entries)} |")
        lines.append("")

        # Validation status section
        lines.append("## Validation Status")
        lines.append("")
        lines.append(f"- **Approved/Valid entries:** {len(entries) - len(needs_review_entries)}")
        lines.append(f"- **Needs Review entries:** {len(needs_review_entries)}")
        lines.append("")

        # Specific sections
        sections = [
            ("Decisions", "decision", "No decisions recorded."),
            ("Problems", "problem", "No problems recorded."),
            ("Candidate Tasks", "candidate_task", "No candidate tasks recorded."),
            ("Insights", "insight", "No insights recorded."),
            ("References", "reference", "No references recorded."),
        ]

        for title, type_key, empty_msg in sections:
            lines.append(f"## {title}")
            lines.append("")
            type_entries = by_type.get(type_key, [])
            if not type_entries:
                lines.append(empty_msg)
                lines.append("")
                continue

            for entry in type_entries:
                lines.append(f"### {entry.summary}")
                lines.append("")
                lines.append(f"- **Structured Entry ID:** `{entry.id}`")
                lines.append(f"- **Raw Entry ID:** `{entry.raw_entry_id}`")
                lines.append(f"- **Confidence:** {entry.confidence:.0%}")
                lines.append(f"- **Status:** {entry.validation_status.value}")
                lines.append("")

        # Entries needing review detail
        lines.append("## Entries Needing Review")
        lines.append("")
        if not needs_review_entries:
            lines.append("No entries need review for this project.")
            lines.append("")
        else:
            for entry in needs_review_entries:
                entry_type_val = entry.entry_type.value if hasattr(entry.entry_type, "value") else str(entry.entry_type)
                lines.append(f"### [{entry_type_val}] {entry.summary}")
                lines.append("")
                lines.append(f"- **Structured Entry ID:** `{entry.id}`")
                lines.append(f"- **Raw Entry ID:** `{entry.raw_entry_id}`")
                lines.append(f"- **Confidence:** {entry.confidence:.0%}")
                lines.append("")

        # Source Entry IDs
        lines.append("## Source Entry IDs")
        lines.append("")
        for entry in entries:
            lines.append(f"- Structured Entry ID: `{entry.id}`")
            lines.append(f"  Raw Entry ID: `{entry.raw_entry_id}`")
        lines.append("")

        # Limitations Warning
        lines.append("## Limitations Warning")
        lines.append("")
        lines.append("This report is based entirely on local data captured for the specified project. It does not reflect external integrations or uncaptured activities.")
        lines.append("")

        return "\n".join(lines)
