"""Shared test fixtures for PIE tests."""

import shutil
import tempfile
from pathlib import Path

import pytest

from personal_intelligence_engine.app.config import Config
from personal_intelligence_engine.app.main import PIEApp

# Resolve migrations directory once
_MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


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
        migrations_dir=_MIGRATIONS_DIR,
        extractor_backend="fake",
    )
    app = PIEApp(config=config)
    yield app
    app.close()
