"""CLI commands for PIE — Personal Intelligence Engine.

Entry point: `pie` (configured in pyproject.toml)
"""

from __future__ import annotations

from pathlib import Path

import click
from pydantic import ValidationError

from personal_intelligence_engine.app.adapters.fake_extractor import FakeExtractor
from personal_intelligence_engine.app.adapters.local_llm_extractor import LocalLLMExtractor
from personal_intelligence_engine.app.config import Config
from personal_intelligence_engine.app.evaluation.report import (
    render_extraction_evaluation_report,
    write_extraction_evaluation_report,
)
from personal_intelligence_engine.app.evaluation.runner import evaluate_extractor
from personal_intelligence_engine.app.main import PIEApp, check_extractor_backend

ROOT = Path(__file__).resolve().parents[3]
EXTRACTION_QUALITY_FIXTURES = ROOT / "tests" / "fixtures" / "extraction_quality_cases.json"


def _format_validation_error(exc: ValidationError) -> str:
    """Return a compact validation message for CLI users."""
    first_error = exc.errors()[0]
    location = ".".join(str(part) for part in first_error["loc"])
    message = first_error["msg"]
    if location:
        return f"Invalid input ({location}): {message}"
    return f"Invalid input: {message}"


def _format_cli_error(exc: Exception) -> str:
    """Convert common application exceptions into user-facing messages."""
    if isinstance(exc, ValidationError):
        return _format_validation_error(exc)
    if isinstance(exc, OSError):
        return f"Could not access configured path: {exc}"
    return str(exc)


def _shorten(value: str, limit: int = 90) -> str:
    """Return a compact single-line preview for CLI output."""
    preview = " ".join(value.split())
    if len(preview) <= limit:
        return preview
    return f"{preview[: limit - 3]}..."


def _render_reprocess_batch_summary(batch: dict, dry_run: bool) -> None:
    """Render batch reprocess totals without exposing raw content."""
    applied = batch["applied"]
    failed = batch["failed"]
    selected_ids = batch["selected_ids"]
    processed_label = "Previewed" if dry_run else "Applied"

    click.echo("Batch Summary:")
    click.echo(f"  Total selected: {len(selected_ids)}")
    click.echo(f"  Total {processed_label.lower()}: {len(applied)}")
    click.echo(f"  Total failed:   {len(failed)}")
    click.echo(f"  {processed_label} IDs:")
    if applied:
        for result in applied:
            click.echo(f"    - {result['structured_entry_id']}")
    else:
        click.echo("    - -")

    click.echo("  Failed IDs:")
    if failed:
        for failure in failed:
            click.echo(f"    - {failure['structured_entry_id']}: {_shorten(failure['error'], limit=160)}")
    else:
        click.echo("    - -")
    click.echo("")


@click.group()
@click.version_option(package_name="personal-intelligence-engine")
def cli() -> None:
    """PIE — Personal Intelligence Engine.

    A local-first engine for capturing, structuring, and
    projecting personal knowledge.
    """


@cli.command()
@click.argument("text")
@click.option("--source", default="cli", help="Source identifier for the entry.")
def add(text: str, source: str) -> None:
    """Add a new entry to PIE.

    TEXT is the raw content to capture.

    Example:
        pie add "Tive uma ideia para melhorar o pipeline"
    """
    app: PIEApp | None = None
    try:
        app = PIEApp()
        result = app.add_entry(text, source=source)

        click.echo("[OK] Entry created successfully!")
        click.echo(f"   Entry ID:      {result['entry_id']}")
        click.echo(f"   Structured ID: {result['structured_entry_id']}")
        click.echo(f"   Type:          {result['entry_type']}")
        click.echo(f"   Confidence:    {result['confidence']:.0%}")
        click.echo(f"   Validation:    {result['validation_status']}")
        click.echo(f"   Note:          {result['note_path']}")

        if result["validation_status"] == "needs_review":
            click.echo("")
            click.echo("[!] Low confidence -- this entry needs human review.")
    except (ValidationError, ValueError, OSError) as exc:
        raise click.ClickException(_format_cli_error(exc)) from exc
    finally:
        if app is not None:
            app.close()


@cli.command()
def doctor() -> None:
    """Check the configured extractor backend without creating entries."""
    try:
        result = check_extractor_backend(Config())
    except (ValidationError, ValueError, OSError) as exc:
        raise click.ClickException(_format_cli_error(exc)) from exc

    status = "[OK]" if result["ok"] else "[ERROR]"
    click.echo(f"{status} Extractor backend: {result['backend']}")
    click.echo(f"   Message:       {result['message']}")
    if result.get("model_name"):
        click.echo(f"   Model:         {result['model_name']}")
    if result.get("prompt_version"):
        click.echo(f"   Prompt:        {result['prompt_version']}")

    if not result["ok"]:
        raise click.exceptions.Exit(1)


@cli.group()
def evaluate() -> None:
    """Run local synthetic evaluations."""


@evaluate.command(name="extraction")
@click.option(
    "--backend",
    default="fake",
    show_default=True,
    type=click.Choice(["fake", "ollama"], case_sensitive=False),
    help="Extractor backend to evaluate.",
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Optional Markdown output path.",
)
def evaluate_extraction(backend: str, output: Path | None) -> None:
    """Run extraction quality evaluation and render Markdown."""
    try:
        extractor = _build_evaluation_extractor(backend)
        run = evaluate_extractor(
            extractor,
            EXTRACTION_QUALITY_FIXTURES,
            backend=backend.strip().lower(),
        )

        if output is not None:
            saved_path = write_extraction_evaluation_report(run, output)
            click.echo(f"[OK] Extraction evaluation report saved: {saved_path}")
            return

        click.echo(render_extraction_evaluation_report(run))
    except (ValidationError, ValueError, OSError) as exc:
        raise click.ClickException(_format_cli_error(exc)) from exc


def _build_evaluation_extractor(backend: str):
    """Build an extractor for synthetic evaluation without opening the database."""
    normalized_backend = backend.strip().lower()
    if normalized_backend == "fake":
        return FakeExtractor()

    if normalized_backend == "ollama":
        config = Config(extractor_backend="ollama")
        return LocalLLMExtractor(
            base_url=config.ollama_base_url,
            model=config.ollama_model,
            timeout_seconds=config.llm_timeout_seconds,
            max_retries=config.llm_max_retries,
            retry_backoff_seconds=config.llm_retry_backoff_seconds,
        )

    raise ValueError(f"Invalid evaluation backend '{backend}'. Use 'fake' or 'ollama'.")


@cli.group()
def review() -> None:
    """Inspect entries waiting for human review."""


@review.command(name="list")
def review_list() -> None:
    """List entries marked as needs_review."""
    app: PIEApp | None = None
    try:
        app = PIEApp()
        entries = app.list_review_entries()
        if not entries:
            click.echo("[OK] No entries need review.")
            return

        click.echo("Entries needing review:")
        for entry in entries:
            click.echo("")
            click.echo(f"Structured Entry ID: {entry['structured_entry_id']}")
            click.echo(f"Raw Entry ID:        {entry['raw_entry_id']}")
            click.echo(f"Type:                {entry['entry_type']}")
            click.echo(f"Project:             {entry['project'] or '-'}")
            click.echo(f"Confidence:          {entry['confidence']:.0%}")
            click.echo(f"Created At:          {entry['created_at']}")
            click.echo(f"Summary:             {_shorten(entry['summary'])}")
    except (ValidationError, ValueError, OSError) as exc:
        raise click.ClickException(_format_cli_error(exc)) from exc
    finally:
        if app is not None:
            app.close()


@review.command(name="show")
@click.argument("structured_entry_id")
def review_show(structured_entry_id: str) -> None:
    """Show details for one entry marked as needs_review."""
    app: PIEApp | None = None
    try:
        app = PIEApp()
        entry = app.get_review_entry(structured_entry_id)

        click.echo(f"Structured Entry ID: {entry['structured_entry_id']}")
        click.echo(f"Raw Entry ID:        {entry['raw_entry_id']}")
        click.echo(f"Type:                {entry['entry_type']}")
        click.echo(f"Project:             {entry['project'] or '-'}")
        click.echo(f"Summary:             {entry['summary']}")
        click.echo(f"Confidence:          {entry['confidence']:.0%}")
        click.echo(f"Tags:                {', '.join(entry['tags']) if entry['tags'] else '-'}")
        click.echo(f"Validation Status:   {entry['validation_status']}")
        click.echo(f"Created At:          {entry['created_at']}")
        click.echo(f"Raw Content:         {_shorten(entry['raw_content'], limit=500)}")
    except (ValidationError, ValueError, OSError) as exc:
        raise click.ClickException(_format_cli_error(exc)) from exc
    finally:
        if app is not None:
            app.close()


@review.command(name="history")
@click.argument("structured_entry_id")
def review_history(structured_entry_id: str) -> None:
    """Show audit history for one structured entry."""
    app: PIEApp | None = None
    try:
        app = PIEApp()
        history = app.get_review_history(structured_entry_id)

        click.echo(f"Structured Entry ID: {history['structured_entry_id']}")
        click.echo(f"Raw Entry ID:        {history['raw_entry_id']}")
        events = history["events"]
        if not events:
            click.echo("[OK] No audit history found for this entry.")
            return

        click.echo("Audit History:")
        for event in events:
            click.echo("")
            click.echo(f"Created At:     {event['created_at']}")
            click.echo(f"Action:         {event['action']}")
            click.echo(f"Status:         {event['status']}")
            click.echo(f"Actor:          {event['actor']}")
            click.echo(f"Method:         {event['method'] or '-'}")
            if event["model_name"]:
                click.echo(f"Model:          {event['model_name']}")
            if event["prompt_version"]:
                click.echo(f"Prompt Version: {event['prompt_version']}")
            if event["error_message"]:
                click.echo(f"Error:          {_shorten(event['error_message'], limit=160)}")
    except (ValidationError, ValueError, OSError) as exc:
        raise click.ClickException(_format_cli_error(exc)) from exc
    finally:
        if app is not None:
            app.close()


@review.command(name="approve")
@click.argument("structured_entry_id")
def review_approve(structured_entry_id: str) -> None:
    """Approve one entry marked as needs_review."""
    app: PIEApp | None = None
    try:
        app = PIEApp()
        result = app.approve_review_entry(structured_entry_id)

        if result["status"] == "already_processed":
            click.echo(f"[OK] {result['message']}")
        else:
            click.echo("[OK] Review entry approved.")
            click.echo(f"   Structured Entry ID: {result['structured_entry_id']}")
            click.echo(f"   Raw Entry ID:        {result['raw_entry_id']}")
            click.echo("   Status:              processed")
            click.echo("   Validation:          valid")
    except (ValidationError, ValueError, OSError) as exc:
        raise click.ClickException(_format_cli_error(exc)) from exc
    finally:
        if app is not None:
            app.close()


@review.command(name="reject")
@click.argument("structured_entry_id")
def review_reject(structured_entry_id: str) -> None:
    """Reject one entry marked as needs_review."""
    app: PIEApp | None = None
    try:
        app = PIEApp()
        result = app.reject_review_entry(structured_entry_id)

        if result["status"] == "already_processed":
            click.echo(f"[OK] {result['message']}")
        else:
            click.echo("[OK] Review entry rejected.")
            click.echo(f"   Structured Entry ID: {result['structured_entry_id']}")
            click.echo(f"   Raw Entry ID:        {result['raw_entry_id']}")
            click.echo("   Status:              processed")
            click.echo("   Validation:          invalid")
    except (ValidationError, ValueError, OSError) as exc:
        raise click.ClickException(_format_cli_error(exc)) from exc
    finally:
        if app is not None:
            app.close()


@cli.group()
def report() -> None:
    """Generate reports from PIE entries."""


@report.command()
@click.option(
    "--date",
    required=True,
    help="Date for the report in YYYY-MM-DD format.",
)
def daily(date: str) -> None:
    """Generate a daily report.

    Example:
        pie report daily --date 2026-05-09
    """
    app: PIEApp | None = None
    try:
        app = PIEApp()
        result = app.generate_daily_report(date)

        click.echo("[OK] Daily report generated!")
        click.echo(f"   Report ID:    {result['report_id']}")
        click.echo(f"   Date:         {result['date']}")
        click.echo(f"   Entries:      {result['entry_count']}")
        click.echo(f"   File:         {result['file_path']}")
    except (ValidationError, ValueError, OSError) as exc:
        raise click.ClickException(_format_cli_error(exc)) from exc
    finally:
        if app is not None:
            app.close()


@report.command(name="weekly")
@click.option(
    "--date",
    required=True,
    help="Date for the report in YYYY-MM-DD format (any day of the week).",
)
def weekly(date: str) -> None:
    """Generate a weekly report.

    Example:
        pie report weekly --date 2026-05-09
    """
    app: PIEApp | None = None
    try:
        app = PIEApp()
        result = app.generate_weekly_report(date)

        click.echo("[OK] Weekly report generated!")
        click.echo(f"   Report ID:    {result['report_id']}")
        click.echo(f"   Start Date:   {result['date_start']}")
        click.echo(f"   End Date:     {result['date_end']}")
        click.echo(f"   Entries:      {result['entry_count']}")
        click.echo(f"   File:         {result['file_path']}")
    except (ValidationError, ValueError, OSError) as exc:
        raise click.ClickException(_format_cli_error(exc)) from exc
    finally:
        if app is not None:
            app.close()


@report.command(name="project")
@click.option(
    "--project",
    required=True,
    help="Project name for the report.",
)
def project_report(project: str) -> None:
    """Generate a project report.

    Example:
        pie report project --project PIE
    """
    app: PIEApp | None = None
    try:
        app = PIEApp()
        result = app.generate_project_report(project)

        click.echo("[OK] Project report generated!")
        click.echo(f"   Report ID:    {result['report_id']}")
        click.echo(f"   Project:      {result['project']}")
        click.echo(f"   Entries:      {result['entry_count']}")
        click.echo(f"   File:         {result['file_path']}")
    except (ValidationError, ValueError, OSError) as exc:
        raise click.ClickException(_format_cli_error(exc)) from exc
    finally:
        if app is not None:
            app.close()


@cli.group()
def entries() -> None:
    """Inspect stored entries."""


@entries.command(name="list")
@click.option("--type", "entry_type", default=None, help="Filter by entry type.")
@click.option("--project", default=None, help="Filter by project.")
@click.option("--status", "validation_status", default=None, help="Filter by validation status.")
@click.option("--limit", default=50, show_default=True, type=int, help="Maximum entries to show.")
def entries_list(
    entry_type: str | None,
    project: str | None,
    validation_status: str | None,
    limit: int,
) -> None:
    """List structured entries with optional filters.

    Examples:
        pie entries list
        pie entries list --type decision
        pie entries list --project PIE --limit 10
    """
    app: PIEApp | None = None
    try:
        app = PIEApp()
        results = app.list_entries(
            entry_type=entry_type,
            project=project,
            validation_status=validation_status,
            limit=limit,
        )
        if not results:
            click.echo("No entries found.")
            return

        click.echo(f"Entries ({len(results)}):")
        for entry in results:
            click.echo("")
            click.echo(f"Structured Entry ID: {entry['structured_entry_id']}")
            click.echo(f"Raw Entry ID:        {entry['raw_entry_id']}")
            click.echo(f"Type:                {entry['entry_type']}")
            click.echo(f"Project:             {entry['project'] or '-'}")
            click.echo(f"Confidence:          {entry['confidence']:.0%}")
            click.echo(f"Validation:          {entry['validation_status']}")
            click.echo(f"Created At:          {entry['created_at']}")
            click.echo(f"Summary:             {_shorten(entry['summary'])}")
    except (ValidationError, ValueError, OSError) as exc:
        raise click.ClickException(_format_cli_error(exc)) from exc
    finally:
        if app is not None:
            app.close()


@entries.command(name="show")
@click.argument("structured_entry_id")
def entries_show(structured_entry_id: str) -> None:
    """Show details for one structured entry.

    Example:
        pie entries show a1b2c3d4-e5f6-...
    """
    app: PIEApp | None = None
    try:
        app = PIEApp()
        entry = app.get_entry_detail(structured_entry_id)

        click.echo(f"Structured Entry ID: {entry['structured_entry_id']}")
        click.echo(f"Raw Entry ID:        {entry['raw_entry_id']}")
        click.echo(f"Type:                {entry['entry_type']}")
        click.echo(f"Project:             {entry['project'] or '-'}")
        click.echo(f"Summary:             {entry['summary']}")
        click.echo(f"Confidence:          {entry['confidence']:.0%}")
        click.echo(f"Tags:                {', '.join(entry['tags']) if entry['tags'] else '-'}")
        click.echo(f"Validation Status:   {entry['validation_status']}")
        click.echo(f"Created At:          {entry['created_at']}")
        click.echo(f"Updated At:          {entry['updated_at']}")
        click.echo(f"Raw Content:         {_shorten(entry['raw_content'], limit=500)}")

        # Show a compact view of structured_json
        try:
            import json
            payload = json.loads(entry.get("structured_json") or "{}")
            formatted = json.dumps(payload, indent=2, ensure_ascii=False)
            click.echo(f"Structured JSON:     {_shorten(formatted, limit=500)}")
        except (json.JSONDecodeError, TypeError):
            click.echo("Structured JSON:     -")
    except (ValidationError, ValueError, OSError) as exc:
        raise click.ClickException(_format_cli_error(exc)) from exc
    finally:
        if app is not None:
            app.close()


@entries.command(name="reprocess")
@click.argument("structured_entry_id", required=False)
@click.option("--status", default=None, help="Filter entries to reprocess by status/validation status.")
@click.option(
    "--limit",
    default=20,
    show_default=True,
    type=click.IntRange(min=1),
    help="Maximum entries to reprocess when status is specified.",
)
@click.option("--dry-run", is_flag=True, help="Show comparison of changes without applying them.")
def entries_reprocess(
    structured_entry_id: str | None,
    status: str | None,
    limit: int,
    dry_run: bool,
) -> None:
    """Reprocess existing stored entries.

    Must specify either a structured_entry_id or --status (but not both).

    Examples:
        pie entries reprocess a1b2c3d4-e5f6-7890-abcd-ef1234567890 --dry-run
        pie entries reprocess --status needs_review
    """
    if structured_entry_id is None and status is None:
        raise click.UsageError("Must specify either STRUCTURED_ENTRY_ID or --status.")
    if structured_entry_id is not None and status is not None:
        raise click.UsageError("Cannot specify both STRUCTURED_ENTRY_ID and --status.")

    # Recommend backup before applying changes
    if not dry_run:
        click.echo("[INFO] Recomenda-se realizar um backup do banco de dados (ex: 'pie backup create') antes de aplicar o reprocessamento.")
        click.echo("")

    app: PIEApp | None = None
    try:
        app = PIEApp()
        if structured_entry_id is not None:
            # Reprocess single entry
            result = app.reprocess_entry(structured_entry_id, dry_run=dry_run)
            results = [result]
            batch = None
        else:
            # Reprocess by status
            batch = app.reprocess_entries_by_status(status, limit=limit, dry_run=dry_run)
            results = batch["applied"]
            if not results:
                if not batch["failed"]:
                    click.echo(f"Nenhuma entrada encontrada com o status '{status}'.")
                    return
                _render_reprocess_batch_summary(batch, dry_run)
                raise click.ClickException("All selected entries failed during reprocessing.")

        # Show comparison/summary of results
        for res in results:
            entry_id = res["structured_entry_id"]
            comp = res["comparison"]
            has_changes = res["has_changes"]
            mode_str = " (Dry Run)" if dry_run else ""

            click.echo(f"Structured Entry ID: {entry_id}{mode_str}")
            if not has_changes:
                click.echo("  No changes detected.")
                click.echo("")
                continue

            for field, val in comp.items():
                before = val["before"]
                after = val["after"]
                if before != after:
                    before_str = f"'{before}'" if before is not None else "-"
                    after_str = f"'{after}'" if after is not None else "-"
                    if field == "confidence":
                        before_str = f"{before:.0%}"
                        after_str = f"{after:.0%}"
                    elif field == "tags":
                        before_str = ", ".join(before) if before else "-"
                        after_str = ", ".join(after) if after else "-"

                    click.echo(f"  - {field.replace('_', ' ').title()}: {before_str} -> {after_str}")
            click.echo("")

        if batch is not None:
            _render_reprocess_batch_summary(batch, dry_run)

        if not dry_run:
            if batch is not None and batch["failed"]:
                click.echo("[WARNING] Reprocessamento concluido com falhas parciais.")
            else:
                click.echo("[OK] Reprocessamento aplicado com sucesso!")
            click.echo("[WARNING] As notas Markdown em 'notes/' não foram regeneradas automaticamente e podem estar desatualizadas.")

    except (ValidationError, ValueError, OSError) as exc:
        raise click.ClickException(_format_cli_error(exc)) from exc
    finally:
        if app is not None:
            app.close()


@cli.command()
@click.argument("query")
@click.option("--type", "entry_type", default=None, help="Filter by entry type.")
@click.option("--project", default=None, help="Filter by project.")
@click.option("--status", "validation_status", default=None, help="Filter by validation status.")
@click.option("--limit", default=50, show_default=True, type=int, help="Maximum results to show.")
def search(
    query: str,
    entry_type: str | None,
    project: str | None,
    validation_status: str | None,
    limit: int,
) -> None:
    """Search entries by text.

    Searches across raw content, summary, project, and tags.

    Examples:
        pie search "SQLite"
        pie search "SQLite" --type decision
        pie search "pipeline" --project PIE
    """
    app: PIEApp | None = None
    try:
        app = PIEApp()
        results = app.search_entries(
            query,
            entry_type=entry_type,
            project=project,
            validation_status=validation_status,
            limit=limit,
        )
        if not results:
            click.echo("No search results found.")
            return

        click.echo(f"Search results ({len(results)}):")
        for entry in results:
            click.echo("")
            click.echo(f"Structured Entry ID: {entry['structured_entry_id']}")
            click.echo(f"Raw Entry ID:        {entry['raw_entry_id']}")
            click.echo(f"Type:                {entry['entry_type']}")
            click.echo(f"Project:             {entry['project'] or '-'}")
            click.echo(f"Confidence:          {entry['confidence']:.0%}")
            click.echo(f"Validation:          {entry['validation_status']}")
            click.echo(f"Match Source:        {entry['match_source']}")
            click.echo(f"Summary:             {_shorten(entry['summary'])}")
            click.echo(f"Snippet:             {_shorten(entry['raw_content'], limit=120)}")
    except (ValidationError, ValueError, OSError) as exc:
        raise click.ClickException(_format_cli_error(exc)) from exc
    finally:
        if app is not None:
            app.close()


@cli.group()
def backup() -> None:
    """Manage local database backups."""


@backup.command(name="create")
def backup_create() -> None:
    """Create a secure copy of the local SQLite database.

    Example:
        pie backup create
    """
    config = Config()
    if not config.database_path.exists():
        raise click.ClickException(f"Could not access configured path: Database file '{config.database_path}' does not exist.")

    app: PIEApp | None = None
    try:
        app = PIEApp(config=config)
        result = app.create_backup()
        click.echo(f"Backup created: {result['backup_path']}")
    except (ValidationError, ValueError, OSError) as exc:
        raise click.ClickException(_format_cli_error(exc)) from exc
    finally:
        if app is not None:
            app.close()


@cli.group()
def export() -> None:
    """Export PIE Core data to portable formats."""


@export.command(name="json")
def export_json() -> None:
    """Export core tables to a single JSON file.

    Example:
        pie export json
    """
    app: PIEApp | None = None
    try:
        app = PIEApp()
        result = app.export_json()
        click.echo(f"JSON export created: {result['export_path']}")
    except (ValidationError, ValueError, OSError) as exc:
        raise click.ClickException(_format_cli_error(exc)) from exc
    finally:
        if app is not None:
            app.close()


@export.command(name="markdown")
def export_markdown() -> None:
    """Export structured entries grouped by type to Markdown.

    Example:
        pie export markdown
    """
    app: PIEApp | None = None
    try:
        app = PIEApp()
        result = app.export_markdown()
        click.echo(f"Markdown export created: {result['export_path']}")
    except (ValidationError, ValueError, OSError) as exc:
        raise click.ClickException(_format_cli_error(exc)) from exc
    finally:
        if app is not None:
            app.close()


if __name__ == "__main__":
    cli()
