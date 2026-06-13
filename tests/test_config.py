"""Tests for PIE configuration helpers."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from personal_intelligence_engine.app.cli.commands import cli
from personal_intelligence_engine.app.config import Config


def test_no_pie_home_keeps_cwd_behavior(monkeypatch):
    monkeypatch.delenv("PIE_HOME", raising=False)
    cfg = Config()
    assert cfg.pie_home is None
    assert cfg.database_path == Path("pie.db")


def test_pie_home_resolves_paths_under_root(tmp_path):
    cfg = Config(pie_home=str(tmp_path))
    assert cfg.database_path == tmp_path / "pie.db"
    assert cfg.notes_dir == tmp_path / "notes"
    assert cfg.reports_dir == tmp_path / "reports"


def test_pie_home_absolute_path_wins(tmp_path):
    abs_db = tmp_path / "custom" / "mydb.db"
    cfg = Config(pie_home=str(tmp_path), database_path=str(abs_db))
    assert cfg.database_path == abs_db


def test_pie_home_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("PIE_HOME", str(tmp_path))
    cfg = Config()
    assert cfg.database_path == tmp_path / "pie.db"


def test_doctor_shows_pie_home(monkeypatch, tmp_path):
    monkeypatch.setenv("PIE_HOME", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"])
    assert str(tmp_path) in result.output


def test_ensure_dirs_creates_all_runtime_directories(work_dir):
    config = Config(
        database_path=work_dir / "data" / "pie.db",
        notes_dir=work_dir / "notes",
        reports_dir=work_dir / "reports",
        backup_dir=work_dir / "backups",
        export_dir=work_dir / "exports",
        migrations_dir=work_dir / "migrations",
    )

    config.ensure_dirs()

    assert config.database_path.parent.exists()
    assert config.notes_dir.exists()
    assert config.reports_dir.exists()
    assert config.backup_dir.exists()
    assert config.export_dir.exists()
