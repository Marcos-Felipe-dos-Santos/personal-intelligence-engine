"""Tests for PIE configuration helpers."""

from personal_intelligence_engine.app.config import Config


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
