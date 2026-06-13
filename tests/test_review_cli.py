"""CLI tests for read-only human review commands."""

import re
import sqlite3

from click.testing import CliRunner

from personal_intelligence_engine.app.cli.commands import cli
from personal_intelligence_engine.app.repositories.audit_repository import AuditRepository


def _configure_temp_env(monkeypatch, work_dir) -> None:
    monkeypatch.setenv("PIE_DATABASE_PATH", str(work_dir / "pie.db"))
    monkeypatch.setenv("PIE_NOTES_DIR", str(work_dir / "notes"))
    monkeypatch.setenv("PIE_REPORTS_DIR", str(work_dir / "reports"))
    monkeypatch.setenv("PIE_EXTRACTOR_BACKEND", "fake")


def _add_entry(text: str, auto_approve: bool = False) -> str:
    args = ["add", text]
    if auto_approve:
        args.append("--auto-approve")
    result = CliRunner().invoke(cli, args)
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


def _fetch_review_rejected_logs(database_path, raw_entry_id: str) -> list[dict]:
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT *
            FROM audit_logs
            WHERE raw_entry_id = ? AND action = 'review_rejected'
            ORDER BY created_at;
            """,
            (raw_entry_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def _delete_audit_logs(database_path, raw_entry_id: str) -> None:
    with sqlite3.connect(database_path) as connection:
        connection.execute("DELETE FROM audit_logs WHERE raw_entry_id = ?;", (raw_entry_id,))
        connection.commit()


def test_review_list_shows_needs_review_entry(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Nota sintetica sem projeto claro")

    result = CliRunner().invoke(cli, ["review", "list"])

    assert result.exit_code == 0
    assert "Entries needing review" in result.output
    assert structured_id in result.output
    assert "general_note" in result.output
    assert "30%" in result.output
    assert "Nota sintetica sem projeto claro" in result.output


def test_review_list_does_not_show_processed_entry(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    processed_id = _add_entry("Eu decidi usar SQLite no projeto sintetico", auto_approve=True)
    needs_review_id = _add_entry("Nota sintetica sem projeto claro")

    result = CliRunner().invoke(cli, ["review", "list"])

    assert result.exit_code == 0
    assert needs_review_id in result.output
    assert processed_id not in result.output


def test_review_list_without_results_shows_friendly_message(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    _add_entry("Eu decidi usar SQLite no projeto sintetico", auto_approve=True)

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
    assert "30%" in result.output
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
    structured_id = _add_entry("Eu decidi usar SQLite no projeto sintetico", auto_approve=True)
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


def test_review_approve_rolls_back_if_audit_log_fails(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Nota sintetica sem projeto claro")
    before = _fetch_review_state(work_dir / "pie.db", structured_id)
    original_insert = AuditRepository.insert

    def fail_review_approved(self, log):
        if log.action.value == "review_approved":
            raise RuntimeError("simulated approve audit failure")
        return original_insert(self, log)

    monkeypatch.setattr(AuditRepository, "insert", fail_review_approved)

    result = CliRunner().invoke(cli, ["review", "approve", structured_id])

    assert result.exit_code != 0
    after = _fetch_review_state(work_dir / "pie.db", structured_id)
    assert after["raw_status"] == before["raw_status"]
    assert after["validation_status"] == before["validation_status"]
    assert _fetch_review_approved_logs(work_dir / "pie.db", before["raw_entry_id"]) == []


def test_review_show_after_approve_returns_friendly_error(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Nota sintetica sem projeto claro")

    approve_result = CliRunner().invoke(cli, ["review", "approve", structured_id])
    show_result = CliRunner().invoke(cli, ["review", "show", structured_id])

    assert approve_result.exit_code == 0
    assert show_result.exit_code != 0
    assert "No review entry found for structured entry ID" in show_result.output
    assert "Traceback" not in show_result.output


def test_review_reject_marks_entry_processed_and_invalid(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Nota sintetica sem projeto claro")

    result = CliRunner().invoke(cli, ["review", "reject", structured_id])

    assert result.exit_code == 0
    assert "Review entry rejected" in result.output
    assert structured_id in result.output

    state = _fetch_review_state(work_dir / "pie.db", structured_id)
    assert state["raw_status"] == "processed"
    assert state["validation_status"] == "invalid"


def test_review_reject_removes_entry_from_review_list(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Nota sintetica sem projeto claro")

    reject_result = CliRunner().invoke(cli, ["review", "reject", structured_id])
    list_result = CliRunner().invoke(cli, ["review", "list"])

    assert reject_result.exit_code == 0
    assert list_result.exit_code == 0
    assert structured_id not in list_result.output
    assert "No entries need review" in list_result.output


def test_review_reject_creates_audit_log_with_raw_entry_id(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Nota sintetica sem projeto claro")
    raw_entry_id = _fetch_review_state(work_dir / "pie.db", structured_id)["raw_entry_id"]

    result = CliRunner().invoke(cli, ["review", "reject", structured_id])

    assert result.exit_code == 0
    logs = _fetch_review_rejected_logs(work_dir / "pie.db", raw_entry_id)
    assert len(logs) == 1
    assert logs[0]["raw_entry_id"] == raw_entry_id
    assert logs[0]["action"] == "review_rejected"
    assert logs[0]["actor"] == "user"
    assert logs[0]["method"] == "human_review"
    assert logs[0]["status"] == "success"
    assert logs[0]["model_name"] is None
    assert logs[0]["prompt_version"] is None
    assert logs[0]["error_message"] is None


def test_review_reject_preserves_raw_content_and_structured_entry(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    raw_content = "Nota sintetica sem projeto claro"
    structured_id = _add_entry(raw_content)

    before = _fetch_review_state(work_dir / "pie.db", structured_id)
    result = CliRunner().invoke(cli, ["review", "reject", structured_id])
    after = _fetch_review_state(work_dir / "pie.db", structured_id)

    assert result.exit_code == 0
    assert before["raw_content"] == raw_content
    assert after["raw_content"] == raw_content
    assert after["structured_entry_id"] == structured_id


def test_review_reject_missing_id_returns_friendly_error(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)

    result = CliRunner().invoke(cli, ["review", "reject", "missing-id"])

    assert result.exit_code != 0
    assert "No structured entry found for ID 'missing-id'" in result.output
    assert "Traceback" not in result.output


def test_review_reject_already_processed_entry_is_idempotent(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Eu decidi usar SQLite no projeto sintetico", auto_approve=True)
    raw_entry_id = _fetch_review_state(work_dir / "pie.db", structured_id)["raw_entry_id"]
    before_counts = _fetch_counts(work_dir / "pie.db")

    result = CliRunner().invoke(cli, ["review", "reject", structured_id])

    assert result.exit_code == 0
    assert "already processed, valid, or invalid" in result.output
    assert _fetch_counts(work_dir / "pie.db") == before_counts
    assert _fetch_review_rejected_logs(work_dir / "pie.db", raw_entry_id) == []


def test_review_reject_twice_does_not_duplicate_audit_log(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Nota sintetica sem projeto claro")
    raw_entry_id = _fetch_review_state(work_dir / "pie.db", structured_id)["raw_entry_id"]

    first_result = CliRunner().invoke(cli, ["review", "reject", structured_id])
    second_result = CliRunner().invoke(cli, ["review", "reject", structured_id])

    assert first_result.exit_code == 0
    assert second_result.exit_code == 0
    assert "already processed, valid, or invalid" in second_result.output
    assert len(_fetch_review_rejected_logs(work_dir / "pie.db", raw_entry_id)) == 1


def test_review_reject_rolls_back_if_audit_log_fails(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Nota sintetica sem projeto claro")
    before = _fetch_review_state(work_dir / "pie.db", structured_id)
    original_insert = AuditRepository.insert

    def fail_review_rejected(self, log):
        if log.action.value == "review_rejected":
            raise RuntimeError("simulated reject audit failure")
        return original_insert(self, log)

    monkeypatch.setattr(AuditRepository, "insert", fail_review_rejected)

    result = CliRunner().invoke(cli, ["review", "reject", structured_id])

    assert result.exit_code != 0
    after = _fetch_review_state(work_dir / "pie.db", structured_id)
    assert after["raw_status"] == before["raw_status"]
    assert after["validation_status"] == before["validation_status"]
    assert _fetch_review_rejected_logs(work_dir / "pie.db", before["raw_entry_id"]) == []


def test_review_show_after_reject_returns_friendly_error(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Nota sintetica sem projeto claro")

    reject_result = CliRunner().invoke(cli, ["review", "reject", structured_id])
    show_result = CliRunner().invoke(cli, ["review", "show", structured_id])

    assert reject_result.exit_code == 0
    assert show_result.exit_code != 0
    assert "No review entry found for structured entry ID" in show_result.output
    assert "Traceback" not in show_result.output


def test_review_approve_still_works_after_reject_command_added(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Nota sintetica sem projeto claro")

    result = CliRunner().invoke(cli, ["review", "approve", structured_id])

    assert result.exit_code == 0
    assert "Review entry approved" in result.output
    state = _fetch_review_state(work_dir / "pie.db", structured_id)
    assert state["raw_status"] == "processed"
    assert state["validation_status"] == "valid"


def test_review_history_shows_audit_events(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Nota sintetica sem projeto claro")

    result = CliRunner().invoke(cli, ["review", "history", structured_id])

    assert result.exit_code == 0
    assert f"Structured Entry ID: {structured_id}" in result.output
    assert "Raw Entry ID:" in result.output
    assert "Audit History:" in result.output
    assert "Action:         entry_created" in result.output
    assert "Action:         extraction_completed" in result.output
    assert "Action:         validation_completed" in result.output
    assert "Action:         low_confidence" in result.output
    assert "Action:         markdown_generated" in result.output
    assert "Status:         success" in result.output


def test_review_history_events_are_chronological(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Nota sintetica sem projeto claro")

    result = CliRunner().invoke(cli, ["review", "history", structured_id])

    assert result.exit_code == 0
    assert result.output.index("Action:         entry_created") < result.output.index(
        "Action:         extraction_completed"
    )
    assert result.output.index("Action:         extraction_completed") < result.output.index(
        "Action:         validation_completed"
    )
    assert result.output.index("Action:         validation_completed") < result.output.index(
        "Action:         low_confidence"
    )


def test_review_history_includes_review_approved_after_approve(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Nota sintetica sem projeto claro")

    approve_result = CliRunner().invoke(cli, ["review", "approve", structured_id])
    history_result = CliRunner().invoke(cli, ["review", "history", structured_id])

    assert approve_result.exit_code == 0
    assert history_result.exit_code == 0
    assert "Action:         review_approved" in history_result.output
    assert "Method:         human_review" in history_result.output


def test_review_history_includes_review_rejected_after_reject(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Nota sintetica sem projeto claro")

    reject_result = CliRunner().invoke(cli, ["review", "reject", structured_id])
    history_result = CliRunner().invoke(cli, ["review", "history", structured_id])

    assert reject_result.exit_code == 0
    assert history_result.exit_code == 0
    assert "Action:         review_rejected" in history_result.output
    assert "Method:         human_review" in history_result.output


def test_review_history_missing_id_returns_friendly_error(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)

    result = CliRunner().invoke(cli, ["review", "history", "missing-id"])

    assert result.exit_code != 0
    assert "No structured entry found for ID 'missing-id'" in result.output
    assert "Traceback" not in result.output


def test_review_history_without_audit_logs_shows_friendly_message(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Nota sintetica sem projeto claro")
    raw_entry_id = _fetch_review_state(work_dir / "pie.db", structured_id)["raw_entry_id"]
    _delete_audit_logs(work_dir / "pie.db", raw_entry_id)

    result = CliRunner().invoke(cli, ["review", "history", structured_id])

    assert result.exit_code == 0
    assert "No audit history found for this entry" in result.output


def test_review_history_is_read_only(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Nota sintetica sem projeto claro")
    before_counts = _fetch_counts(work_dir / "pie.db")

    result = CliRunner().invoke(cli, ["review", "history", structured_id])

    assert result.exit_code == 0
    assert _fetch_counts(work_dir / "pie.db") == before_counts


def test_review_history_does_not_print_raw_content(monkeypatch, work_dir):
    _configure_temp_env(monkeypatch, work_dir)
    raw_content = "Nota sintetica confidencial somente para teste"
    structured_id = _add_entry(raw_content)

    result = CliRunner().invoke(cli, ["review", "history", structured_id])

    assert result.exit_code == 0
    assert raw_content not in result.output


def _fetch_revisions(database_path, structured_entry_id: str) -> list[dict]:
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT *
            FROM structured_entry_revisions
            WHERE structured_entry_id = ?
            ORDER BY created_at;
            """,
            (structured_entry_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def test_review_edit_creates_revision(work_dir, monkeypatch):
    import json

    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Nota sintetica sem projeto claro")

    result = CliRunner().invoke(cli, ["review", "edit", structured_id, "--summary", "Summary corrigida manualmente"])

    assert result.exit_code == 0
    revisions = _fetch_revisions(work_dir / "pie.db", structured_id)
    assert len(revisions) == 1
    assert revisions[0]["structured_entry_id"] == structured_id
    before = json.loads(revisions[0]["before_json"])
    after = json.loads(revisions[0]["after_json"])
    assert "summary" in before
    assert after["summary"] == "Summary corrigida manualmente"


def test_review_edit_preserves_raw(work_dir, monkeypatch):
    _configure_temp_env(monkeypatch, work_dir)
    raw_content = "Nota sintetica sem projeto claro"
    structured_id = _add_entry(raw_content)
    before = _fetch_review_state(work_dir / "pie.db", structured_id)

    result = CliRunner().invoke(cli, ["review", "edit", structured_id, "--summary", "Summary nova"])

    assert result.exit_code == 0
    after = _fetch_review_state(work_dir / "pie.db", structured_id)
    assert before["raw_content"] == raw_content
    assert after["raw_content"] == raw_content


def test_review_edit_audit_log(work_dir, monkeypatch):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Nota sintetica sem projeto claro")
    raw_entry_id = _fetch_review_state(work_dir / "pie.db", structured_id)["raw_entry_id"]

    result = CliRunner().invoke(cli, ["review", "edit", structured_id, "--summary", "Summary nova"])

    assert result.exit_code == 0
    with sqlite3.connect(work_dir / "pie.db") as conn:
        conn.row_factory = sqlite3.Row
        logs = conn.execute(
            "SELECT * FROM audit_logs WHERE raw_entry_id = ? AND action = 'review_edited';",
            (raw_entry_id,),
        ).fetchall()
    assert len(logs) == 1
    assert logs[0]["actor"] == "user"
    assert logs[0]["method"] == "human_review"
    assert logs[0]["status"] == "success"


def test_review_edit_nonexistent_entry(work_dir, monkeypatch):
    _configure_temp_env(monkeypatch, work_dir)

    result = CliRunner().invoke(cli, ["review", "edit", "missing-id", "--summary", "x"])

    assert result.exit_code != 0
    assert "No structured entry found for ID 'missing-id'" in result.output
    assert "Traceback" not in result.output


def test_review_edit_no_fields_raises_error(work_dir, monkeypatch):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Nota sintetica sem projeto claro")

    result = CliRunner().invoke(cli, ["review", "edit", structured_id])

    assert result.exit_code != 0
    assert "at least one field" in result.output.lower()
    assert "Traceback" not in result.output


def test_review_edit_regenerates_markdown(work_dir, monkeypatch):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Nota sintetica sem projeto claro")
    new_summary = "Summary corrigida e melhorada para o markdown"

    result = CliRunner().invoke(cli, ["review", "edit", structured_id, "--summary", new_summary])

    assert result.exit_code == 0
    md_path = work_dir / "notes" / f"{structured_id}.md"
    assert md_path.exists()
    md_content = md_path.read_text(encoding="utf-8")
    assert new_summary in md_content


def test_review_edit_deleted_entry_raises_error(work_dir, monkeypatch):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Nota sintetica sem projeto claro")
    CliRunner().invoke(cli, ["entries", "delete", "--yes", structured_id])

    result = CliRunner().invoke(cli, ["review", "edit", structured_id, "--summary", "Nova summary"])

    assert result.exit_code != 0
    assert "No structured entry found for ID" in result.output
    assert "Traceback" not in result.output


def test_review_edit_empty_summary_raises_error(work_dir, monkeypatch):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Nota sintetica sem projeto claro")

    result = CliRunner().invoke(cli, ["review", "edit", structured_id, "--summary", ""])

    assert result.exit_code != 0
    assert "summary must not be empty" in result.output
    assert "Traceback" not in result.output


def test_review_edit_no_changes_returns_friendly_message(work_dir, monkeypatch):
    _configure_temp_env(monkeypatch, work_dir)
    structured_id = _add_entry("Nota sintetica sem projeto claro")
    with sqlite3.connect(work_dir / "pie.db") as conn:
        row = conn.execute("SELECT summary FROM structured_entries WHERE id = ?;", (structured_id,)).fetchone()
    current_summary = row[0]

    result = CliRunner().invoke(cli, ["review", "edit", structured_id, "--summary", current_summary])

    assert result.exit_code == 0
    assert "no changes" in result.output.lower()
    revisions = _fetch_revisions(work_dir / "pie.db", structured_id)
    assert len(revisions) == 0
