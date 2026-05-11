"""Tests for CLI error handling."""

from click.testing import CliRunner

from personal_intelligence_engine.app.cli.commands import cli


def _configure_temp_env(monkeypatch, work_dir) -> None:
    """Point CLI-generated data at a temporary directory."""
    monkeypatch.setenv("PIE_DATABASE_PATH", str(work_dir / "pie.db"))
    monkeypatch.setenv("PIE_NOTES_DIR", str(work_dir / "notes"))
    monkeypatch.setenv("PIE_REPORTS_DIR", str(work_dir / "reports"))
    monkeypatch.setenv("PIE_EXTRACTOR_BACKEND", "fake")


def test_add_rejects_blank_input_without_traceback(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    result = CliRunner().invoke(cli, ["add", "   "])

    assert result.exit_code != 0
    assert "Input text cannot be empty" in result.output
    assert "Traceback" not in result.output


def test_report_daily_rejects_invalid_date_without_traceback(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    result = CliRunner().invoke(cli, ["report", "daily", "--date", "2026-99-99"])

    assert result.exit_code != 0
    assert "Invalid date. Use YYYY-MM-DD." in result.output
    assert "Traceback" not in result.output


def test_add_reports_invalid_configured_path_without_traceback(monkeypatch, work_dir):
    bad_notes_path = work_dir / "notes"
    bad_notes_path.write_text("not a directory", encoding="utf-8")

    _configure_temp_env(monkeypatch, work_dir)
    monkeypatch.setenv("PIE_NOTES_DIR", str(bad_notes_path))

    result = CliRunner().invoke(cli, ["add", "Tive uma ideia"])

    assert result.exit_code != 0
    assert "Could not access configured path" in result.output
    assert "Traceback" not in result.output


def test_add_with_ollama_config_error_is_friendly(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    monkeypatch.setenv("PIE_EXTRACTOR_BACKEND", "ollama")
    monkeypatch.setenv("PIE_OLLAMA_MODEL", "")

    result = CliRunner().invoke(cli, ["add", "Tive uma ideia sintetica"])

    assert result.exit_code != 0
    assert "Ollama model is not configured" in result.output
    assert "Traceback" not in result.output


def test_doctor_fake_backend_passes(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)

    result = CliRunner().invoke(cli, ["doctor"])

    assert result.exit_code == 0
    assert "Extractor backend: fake" in result.output
    assert "FakeExtractor is available" in result.output
    assert not (work_dir / "pie.db").exists()


def test_doctor_ollama_missing_model_fails_cleanly(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    monkeypatch.setenv("PIE_EXTRACTOR_BACKEND", "ollama")
    monkeypatch.setenv("PIE_OLLAMA_MODEL", "")

    result = CliRunner().invoke(cli, ["doctor"])

    assert result.exit_code == 1
    assert "Extractor backend: ollama" in result.output
    assert "Ollama model is not configured" in result.output
    assert "Traceback" not in result.output
