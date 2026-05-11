"""CLI tests for synthetic extraction quality evaluation."""

from click.testing import CliRunner

from personal_intelligence_engine.app.cli.commands import cli


def test_evaluate_extraction_fake_prints_markdown(monkeypatch, work_dir):
    monkeypatch.setenv("PIE_DATABASE_PATH", str(work_dir / "pie.db"))

    result = CliRunner().invoke(cli, ["evaluate", "extraction", "--backend", "fake"])

    assert result.exit_code == 0
    assert "# Extraction Quality Evaluation Report" in result.output
    assert "- **Backend:** `fake`" in result.output
    assert "- **Fixture count:** 9" in result.output
    assert "- **Average score:**" in result.output
    assert "| Fixture ID | Expected Type | Actual Type | Total Score | Field Scores | Status | Notes |" in result.output
    assert not (work_dir / "pie.db").exists()


def test_evaluate_extraction_fake_saves_markdown(monkeypatch, work_dir):
    monkeypatch.setenv("PIE_DATABASE_PATH", str(work_dir / "pie.db"))
    output_path = work_dir / "reports" / "evaluation" / "fake.md"

    result = CliRunner().invoke(
        cli,
        ["evaluate", "extraction", "--backend", "fake", "--output", str(output_path)],
    )

    assert result.exit_code == 0
    assert "Extraction evaluation report saved" in result.output
    assert output_path.exists()
    assert not (work_dir / "pie.db").exists()

    report = output_path.read_text(encoding="utf-8")
    assert "# Extraction Quality Evaluation Report" in report
    assert "- **Backend:** `fake`" in report
    assert "- **Fixture count:** 9" in report
    assert "- **Average score:**" in report
    assert "| Fixture ID | Expected Type | Actual Type | Total Score | Field Scores | Status | Notes |" in report


def test_evaluate_extraction_invalid_backend_is_friendly():
    result = CliRunner().invoke(cli, ["evaluate", "extraction", "--backend", "cloud"])

    assert result.exit_code != 0
    assert "Invalid value for '--backend'" in result.output
    assert "Traceback" not in result.output


def test_evaluate_extraction_fake_does_not_require_ollama(monkeypatch, work_dir):
    monkeypatch.setenv("PIE_DATABASE_PATH", str(work_dir / "pie.db"))
    monkeypatch.setenv("PIE_OLLAMA_MODEL", "")

    result = CliRunner().invoke(cli, ["evaluate", "extraction", "--backend", "fake"])

    assert result.exit_code == 0
    assert "- **Backend:** `fake`" in result.output
    assert "Ollama model is not configured" not in result.output
