"""Backup and Export service — handles backing up SQLite and exporting portable formats."""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from personal_intelligence_engine.app.config import Config
from personal_intelligence_engine.app.repositories.database import Database


class BackupExportService:
    """Manages database backup and portable JSON/Markdown export operations."""

    def __init__(self, config: Config, db: Database) -> None:
        self.config = config
        self.db = db

    def _get_timestamp(self) -> str:
        tz = ZoneInfo(self.config.local_timezone)
        return datetime.now(tz).strftime("%Y-%m-%dT%H%M%S")

    def create_backup(self) -> Path:
        """Create a page-by-page backup of the SQLite database using backup API.

        Returns:
            The Path to the created backup database file.
        """
        db_path = self.config.database_path
        if not db_path.exists():
            raise FileNotFoundError(f"Database file '{db_path}' does not exist.")

        backup_dir = self.config.backup_dir
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = self._get_timestamp()
        backup_file = backup_dir / f"pie-backup-{timestamp}.sqlite3"

        if backup_file.exists():
            raise FileExistsError(f"Backup file '{backup_file}' already exists.")

        # Safely copy database pages using SQLite's backup API
        src_conn = sqlite3.connect(str(db_path))
        dest_conn = sqlite3.connect(str(backup_file))
        try:
            src_conn.backup(dest_conn)
        finally:
            dest_conn.close()
            src_conn.close()

        return backup_file

    def export_json(self) -> Path:
        """Export main database tables into a single JSON file.

        Returns:
            The Path to the created JSON export file.
        """
        export_dir = self.config.export_dir
        export_dir.mkdir(parents=True, exist_ok=True)

        timestamp = self._get_timestamp()
        export_file = export_dir / f"pie-export-{timestamp}.json"

        if export_file.exists():
            raise FileExistsError(f"Export file '{export_file}' already exists.")

        tables = [
            "raw_entries",
            "structured_entries",
            "audit_logs",
            "generated_files",
            "reports",
            "structured_entry_revisions",
        ]

        data = {}
        conn = self.db.connection
        for table in tables:
            # Check if table exists in schema dynamically
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
                (table,)
            )
            if not cursor.fetchone():
                continue

            cursor = conn.execute(f"SELECT * FROM {table};")
            data[table] = [dict(row) for row in cursor.fetchall()]

        with open(export_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return export_file

    def export_markdown(self) -> Path:
        """Export structured entries grouped by entry_type as Markdown.

        Returns:
            The Path to the created Markdown export file.
        """
        export_dir = self.config.export_dir
        export_dir.mkdir(parents=True, exist_ok=True)

        timestamp = self._get_timestamp()
        export_file = export_dir / f"pie-export-{timestamp}.md"

        if export_file.exists():
            raise FileExistsError(f"Export file '{export_file}' already exists.")

        conn = self.db.connection
        query = """
            SELECT
                se.id AS structured_entry_id,
                se.raw_entry_id,
                se.entry_type,
                se.project,
                se.confidence,
                se.validation_status,
                se.summary,
                re.content AS raw_content
            FROM structured_entries se
            JOIN raw_entries re ON se.raw_entry_id = re.id
            ORDER BY se.entry_type ASC, se.created_at DESC;
        """
        cursor = conn.execute(query)
        rows = [dict(row) for row in cursor.fetchall()]

        total_entries = len(rows)

        grouped = defaultdict(list)
        for row in rows:
            grouped[row["entry_type"]].append(row)

        lines = []
        lines.append("# PIE Export")
        lines.append("")

        tz = ZoneInfo(self.config.local_timezone)
        human_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
        lines.append(f"**Generated on:** {human_time}")
        lines.append(f"**Total Entries:** {total_entries}")
        lines.append("")

        def _shorten(value: str, limit: int = 120) -> str:
            preview = " ".join(value.split())
            if len(preview) <= limit:
                return preview
            return f"{preview[:limit - 3]}..."

        for entry_type in sorted(grouped.keys()):
            type_title = entry_type.replace("_", " ").title()
            lines.append(f"## {type_title}")
            lines.append("")
            for entry in grouped[entry_type]:
                lines.append(f"- **Structured Entry ID:** {entry['structured_entry_id']}")
                lines.append(f"  - **Raw Entry ID:** {entry['raw_entry_id']}")
                lines.append(f"  - **Project:** {entry['project'] or '-'}")
                lines.append(f"  - **Confidence:** {entry['confidence']:.0%}")
                lines.append(f"  - **Validation Status:** {entry['validation_status']}")
                lines.append(f"  - **Summary:** {entry['summary']}")
                snippet = _shorten(entry["raw_content"])
                lines.append(f"  - **Snippet:** {snippet}")
                lines.append("")
            lines.append("---")
            lines.append("")

        if lines and lines[-1] == "" and len(lines) > 1 and lines[-2] == "---":
            lines = lines[:-2]

        markdown_content = "\n".join(lines).strip() + "\n"

        with open(export_file, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        return export_file
