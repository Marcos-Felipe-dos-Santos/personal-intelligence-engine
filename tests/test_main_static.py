"""Static regression checks for the PIE application facade."""

from pathlib import Path


def test_main_has_no_method_local_json_imports():
    source = Path("personal_intelligence_engine/app/main.py").read_text(encoding="utf-8")

    assert "\n        import json\n" not in source
