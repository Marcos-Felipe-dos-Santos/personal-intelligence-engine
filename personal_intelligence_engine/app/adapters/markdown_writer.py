"""Markdown file writer adapter for PIE."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from personal_intelligence_engine.app.domain.schemas import (
    GeneratedFile,
    StructuredEntry,
)
from personal_intelligence_engine.app.domain.types import LOW_CONFIDENCE_THRESHOLD


class MarkdownWriter:
    """Writes structured entries as Markdown files with YAML frontmatter."""

    def __init__(self, notes_dir: Path) -> None:
        self._notes_dir = notes_dir

    def write_note(self, entry: StructuredEntry, raw_content: str) -> GeneratedFile:
        """Generate a Markdown note file for a structured entry.

        Args:
            entry: The structured entry to render.
            raw_content: The original raw text content.

        Returns:
            GeneratedFile record for the generated Markdown.
        """
        self._notes_dir.mkdir(parents=True, exist_ok=True)

        # Parse tags from structured_json
        tags = self._get_tags(entry)

        # Build Markdown content
        md_content = self._render_markdown(entry, raw_content, tags)

        # Write file
        filename = f"{entry.id}.md"
        filepath = self._notes_dir / filename
        filepath.write_text(md_content, encoding="utf-8")

        content_hash = hashlib.sha256(md_content.encode("utf-8")).hexdigest()

        return GeneratedFile(
            raw_entry_id=entry.raw_entry_id,
            file_type="markdown_note",
            path=str(filepath),
            content_hash=content_hash,
        )

    def _render_markdown(
        self,
        entry: StructuredEntry,
        raw_content: str,
        tags: list[str],
    ) -> str:
        """Render the full Markdown document."""
        lines: list[str] = []

        # YAML frontmatter
        lines.append("---")
        lines.append(f"id: {entry.id}")
        lines.append(f"raw_entry_id: {entry.raw_entry_id}")
        lines.append(f"type: {entry.entry_type.value if hasattr(entry.entry_type, 'value') else entry.entry_type}")
        lines.append(f"project: {entry.project or 'none'}")
        lines.append(f"confidence: {entry.confidence}")
        lines.append(f"status: {entry.validation_status.value if hasattr(entry.validation_status, 'value') else entry.validation_status}")
        lines.append(f"created_at: {entry.created_at}")
        if tags:
            lines.append(f"tags: [{', '.join(tags)}]")
        lines.append("---")
        lines.append("")

        # Title
        entry_type_display = entry.entry_type.value if hasattr(entry.entry_type, "value") else entry.entry_type
        lines.append(f"# {entry_type_display.replace('_', ' ').title()}")
        lines.append("")

        # Low confidence warning
        if entry.confidence < LOW_CONFIDENCE_THRESHOLD:
            lines.append(f"> ⚠️ **Low confidence** ({entry.confidence:.0%}). This entry needs human review.")
            lines.append("")

        # Summary
        lines.append("## Summary")
        lines.append("")
        lines.append(entry.summary)
        lines.append("")

        # Raw content
        lines.append("## Raw Content")
        lines.append("")
        lines.append(f"```\n{raw_content}\n```")
        lines.append("")

        # Tags
        if tags:
            lines.append("## Tags")
            lines.append("")
            lines.append(", ".join(f"`{t}`" for t in tags))
            lines.append("")

        # Entry ID reference
        lines.append("---")
        lines.append(f"*Entry ID: `{entry.id}`*")
        lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _get_tags(entry: StructuredEntry) -> list[str]:
        """Extract tags from structured_json."""
        try:
            data = json.loads(entry.structured_json)
            return data.get("tags", [])
        except (json.JSONDecodeError, TypeError):
            return []
