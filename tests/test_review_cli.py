"""CLI tests for read-only human review commands."""

import re
import sqlite3

from click.testing import CliRunner

from personal_intelligence_engine.app.cli.commands import cli


def _configure_temp_env(monkeypatch, work_dir) -> None:
    monkeypatch.setenv("PIE_DATABASE_PATH", str(work_dir / "pie.db"))
    monkeypatch.setenv("PIE_NOTES_DIR", str(work_dir / "notes"))
    monkeypatch.setenv("PIE_REPORTS_DIR", str(work_dir / "reports"))
    monkeypatch.setenv("PIE_EXTRACTOR_BACKEND", "fake")


def _add_entry(text: str) -> str:
    result = CliRunner().invoke(cli, ["add", text])
    assert result.exit_code == 0, result.output

    match = re.search(r"Structured ID:\s+([0-9a-f-]+)", result.output)
    assert match is not None
    return match.group(1)


def _fetch_counts(database_path) -> tuple[int, int, int]:
    with sqlite3.connect(database_path) as connection:
        raw_count = connection.execute("SELECT COUNT(*) FROM raw_entries;").fetchone()[0]
        structured_count = connection.execute("SELECT COUNT(*) FROM structured_entries;").fetchone()[0]
        audit_count = connection.execute("SELECT COUNT(*) FROM audit_logs;").fetchone()[0]
    return raw_count, structured_count, audit_count


def _fetch_review_state(database_path, structured_id: str) -> dict:
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """
            SELECT
                s.id AS structured_entry_id,
                s.raw_entry_id AS raw_entry_id,
                s.validation_status AS validation_status,
                r.status AS raw_status,
                r.content AS raw_content
            FROM structured_entries s
            JOIN raw_entries r ON r.id = s.raw_entry_id
            WHERE s.id = ?;
            """,
            (structured_id,),
        ).fetchone()
    assert row is not None
    return dict(row)


def _fetch_review_approved_logs(database_path, raw_entry_id: str) -> list[dict]:
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT *
            FROM audit_logs
            WHERE raw_entry_id = ? AND action = 'review_approved'
            ORDER BY created_at;
            """,
            (raw_entry_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def test_review_list_shows_needs_review_entry(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Nota sintetica sem projeto claro")

    result = CliRunner().invoke(cli, ["review", "list"])

    assert result.exit_code == 0
    assert "Entries needing review" in result.output
    assert structured_id in result.output
    assert "general_note" in result.output
    assert "50%" in result.output
    assert "Nota sintetica sem projeto claro" in result.output


def test_review_list_does_not_show_processed_entry(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    processed_id = _add_entry("Eu decidi usar SQLite no projeto sintetico")
    needs_review_id = _add_entry("Nota sintetica sem projeto claro")

    result = CliRunner().invoke(cli, ["review", "list"])

    assert result.exit_code == 0
    assert needs_review_id in result.output
    assert processed_id not in result.output


def test_review_list_without_results_shows_friendly_message(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    _add_entry("Eu decidi usar SQLite no projeto sintetico")

    result = CliRunner().invoke(cli, ["review", "list"])

    assert result.exit_code == 0
    assert "No entries need review" in result.output


def test_review_show_displays_entry_details(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Nota sintetica sem projeto claro")

    result = CliRunner().invoke(cli, ["review", "show", structured_id])

    assert result.exit_code == 0
    assert f"Structured Entry ID: {structured_id}" in result.output
    assert "Raw Entry ID:" in result.output
    assert "Type:" in result.output
    assert "general_note" in result.output
    assert "Project:" in result.output
    assert "Summary:" in result.output
    assert "Confidence:" in result.output
    assert "50%" in result.output
    assert "Tags:" in result.output
    assert "unclassified" in result.output
    assert "Validation Status:" in result.output
    assert "needs_review" in result.output
    assert "Raw Content:" in result.output
    assert "Nota sintetica sem projeto claro" in result.output
    assert "Created At:" in result.output


def test_review_show_missing_id_returns_friendly_error(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)

    result = CliRunner().invoke(cli, ["review", "show", "missing-id"])

    assert result.exit_code != 0
    assert "No review entry found for structured entry ID 'missing-id'" in result.output
    assert "Traceback" not in result.output


def test_review_commands_do_not_modify_database(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Nota sintetica sem projeto claro")
    before_list = _fetch_counts(work_dir / "pie.db")

    list_result = CliRunner().invoke(cli, ["review", "list"])
    show_result = CliRunner().invoke(cli, ["review", "show", structured_id])

    assert list_result.exit_code == 0
    assert show_result.exit_code == 0
    assert _fetch_counts(work_dir / "pie.db") == before_list


def test_review_approve_marks_entry_processed_and_valid(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Nota sintetica sem projeto claro")

    result = CliRunner().invoke(cli, ["review", "approve", structured_id])

    assert result.exit_code == 0
    assert "Review entry approved" in result.output
    assert structured_id in result.output

    state = _fetch_review_state(work_dir / "pie.db", structured_id)
    assert state["raw_status"] == "processed"
    assert state["validation_status"] == "valid"


def test_review_approve_removes_entry_from_review_list(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Nota sintetica sem projeto claro")

    approve_result = CliRunner().invoke(cli, ["review", "approve", structured_id])
    list_result = CliRunner().invoke(cli, ["review", "list"])

    assert approve_result.exit_code == 0
    assert list_result.exit_code == 0
    assert structured_id not in list_result.output
    assert "No entries need review" in list_result.output


def test_review_approve_creates_audit_log_with_raw_entry_id(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Nota sintetica sem projeto claro")
    raw_entry_id = _fetch_review_state(work_dir / "pie.db", structured_id)["raw_entry_id"]

    result = CliRunner().invoke(cli, ["review", "approve", structured_id])

    assert result.exit_code == 0
    logs = _fetch_review_approved_logs(work_dir / "pie.db", raw_entry_id)
    assert len(logs) == 1
    assert logs[0]["raw_entry_id"] == raw_entry_id
    assert logs[0]["action"] == "review_approved"
    assert logs[0]["actor"] == "user"
    assert logs[0]["method"] == "human_review"
    assert logs[0]["status"] == "success"
    assert logs[0]["model_name"] is None
    assert logs[0]["prompt_version"] is None
    assert logs[0]["error_message"] is None


def test_review_approve_preserves_raw_content(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    raw_content = "Nota sintetica sem projeto claro"
    structured_id = _add_entry(raw_content)

    before = _fetch_review_state(work_dir / "pie.db", structured_id)
    result = CliRunner().invoke(cli, ["review", "approve", structured_id])
    after = _fetch_review_state(work_dir / "pie.db", structured_id)

    assert result.exit_code == 0
    assert before["raw_content"] == raw_content
    assert after["raw_content"] == raw_content


def test_review_approve_missing_id_returns_friendly_error(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)

    result = CliRunner().invoke(cli, ["review", "approve", "missing-id"])

    assert result.exit_code != 0
    assert "No structured entry found for ID 'missing-id'" in result.output
    assert "Traceback" not in result.output


def test_review_approve_already_processed_entry_is_idempotent(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Eu decidi usar SQLite no projeto sintetico")
    raw_entry_id = _fetch_review_state(work_dir / "pie.db", structured_id)["raw_entry_id"]
    before_counts = _fetch_counts(work_dir / "pie.db")

    result = CliRunner().invoke(cli, ["review", "approve", structured_id])

    assert result.exit_code == 0
    assert "already processed or valid" in result.output
    assert _fetch_counts(work_dir / "pie.db") == before_counts
    assert _fetch_review_approved_logs(work_dir / "pie.db", raw_entry_id) == []


def test_review_approve_twice_does_not_duplicate_audit_log(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Nota sintetica sem projeto claro")
    raw_entry_id = _fetch_review_state(work_dir / "pie.db", structured_id)["raw_entry_id"]

    first_result = CliRunner().invoke(cli, ["review", "approve", structured_id])
    second_result = CliRunner().invoke(cli, ["review", "approve", structured_id])

    assert first_result.exit_code == 0
    assert second_result.exit_code == 0
    assert "already processed or valid" in second_result.output
    assert len(_fetch_review_approved_logs(work_dir / "pie.db", raw_entry_id)) == 1


def test_review_show_after_approve_returns_friendly_error(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Nota sintetica sem projeto claro")

    approve_result = CliRunner().invoke(cli, ["review", "approve", structured_id])
    show_result = CliRunner().invoke(cli, ["review", "show", structured_id])

    assert approve_result.exit_code == 0
    assert show_result.exit_code != 0
    assert "No review entry found for structured entry ID" in show_result.output
    assert "Traceback" not in show_result.output
