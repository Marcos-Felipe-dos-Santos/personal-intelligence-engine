"""Markdown service — generates Markdown notes for structured entries."""

from __future__ import annotations

from personal_intelligence_engine.app.adapters.markdown_writer import MarkdownWriter
from personal_intelligence_engine.app.domain.schemas import GeneratedFile, StructuredEntry
from personal_intelligence_engine.app.repositories.entries_repository import EntriesRepository


class MarkdownService:
    """Orchestrates Markdown note generation."""

    def __init__(
        self,
        writer: MarkdownWriter,
        entries_repo: EntriesRepository,
    ) -> None:
        self._writer = writer
        self._entries_repo = entries_repo

    def generate_note(
        self,
        entry: StructuredEntry,
        raw_content: str,
    ) -> GeneratedFile:
        """Generate a Markdown note and record it.

        Args:
            entry: The structured entry to render.
            raw_content: The original raw text.

        Returns:
            GeneratedFile record for the generated note.
        """
        generated = self._writer.write_note(entry, raw_content)
        self._entries_repo.insert_generated_file(generated)
        return generated
