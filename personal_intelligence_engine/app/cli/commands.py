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


if __name__ == "__main__":
    cli()
