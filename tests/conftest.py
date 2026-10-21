"""Shared test fixtures for PIE tests."""

import os
import shutil
import tempfile
from pathlib import Path

import pytest

# Tests must never load the developer's local configuration.
os.environ["PYTHON_DOTENV_DISABLED"] = "1"

from personal_intelligence_engine.app.config import Config
from personal_intelligence_engine.app.main import PIEApp

# Resolve migrations directory once
_MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "personal_intelligence_engine" / "app" / "migrations"


@pytest.fixture(autouse=True)
def isolated_runtime(monkeypatch, tmp_path):
    """Keep default paths and inherited PIE settings away from personal data."""
    for name in list(os.environ):
        if name.startswith("PIE_"):
            monkeypatch.delenv(name)
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def work_dir():
    """Create a temporary directory for test data, cleaned up after test."""
    d = tempfile.mkdtemp(prefix="pie_test_")
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def app(work_dir):
    """Create a PIEApp with temporary directories."""
    config = Config(
        database_path=work_dir / "test.db",
        notes_dir=work_dir / "notes",
        reports_dir=work_dir / "reports",
        backup_dir=work_dir / "backups",
        export_dir=work_dir / "exports",
        migrations_dir=_MIGRATIONS_DIR,
        extractor_backend="fake",
    )
    app = PIEApp(config=config)
    yield app
    app.close()
