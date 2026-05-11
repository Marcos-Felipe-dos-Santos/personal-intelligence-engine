"""Tests for Markdown generation."""

from pathlib import Path


class TestMarkdownGeneration:
    """Tests for Markdown note generation."""

    def test_markdown_file_created(self, app):
        """A Markdown file is created for each entry."""
        result = app.add_entry("Tive uma ideia brilhante")
        note_path = Path(result["note_path"])
        assert note_path.exists()
        assert note_path.suffix == ".md"

    def test_markdown_has_frontmatter(self, app):
        """Markdown contains YAML frontmatter with required fields."""
        result = app.add_entry("Decidi usar Pydantic")
        note_path = Path(result["note_path"])
        content = note_path.read_text(encoding="utf-8")

        # Check frontmatter markers
        assert content.startswith("---")
        assert content.count("---") >= 2

        # Check required frontmatter fields
        assert "id:" in content
        assert "raw_entry_id:" in content
        assert "type:" in content
        assert "confidence:" in content
        assert "status:" in content
        assert "created_at:" in content

    def test_markdown_has_summary(self, app):
        """Markdown contains a summary section."""
        result = app.add_entry("Preciso fazer o deploy")
        note_path = Path(result["note_path"])
        content = note_path.read_text(encoding="utf-8")
        assert "## Summary" in content

    def test_markdown_has_raw_content(self, app):
        """Markdown contains the raw content."""
        text = "Texto original da entrada para teste"
        result = app.add_entry(text)
        note_path = Path(result["note_path"])
        content = note_path.read_text(encoding="utf-8")
        assert text in content

    def test_markdown_has_entry_id(self, app):
        """Markdown contains the entry ID."""
        result = app.add_entry("Teste de ID")
        note_path = Path(result["note_path"])
        content = note_path.read_text(encoding="utf-8")
        assert result["structured_entry_id"] in content

    def test_low_confidence_warning_in_markdown(self, app):
        """Low confidence entries show a warning in Markdown."""
        result = app.add_entry("Texto genérico sem palavras-chave")
        assert result["confidence"] < 0.70

        note_path = Path(result["note_path"])
        content = note_path.read_text(encoding="utf-8")
        assert "Low confidence" in content or "low confidence" in content.lower()

    def test_high_confidence_no_warning(self, app):
        """High confidence entries do NOT show a low confidence warning."""
        result = app.add_entry("Eu decidi implementar o cache")
        assert result["confidence"] >= 0.70

        note_path = Path(result["note_path"])
        content = note_path.read_text(encoding="utf-8")
        assert "Low confidence" not in content
