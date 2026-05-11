"""Markdown reporting for synthetic extraction quality evaluation."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from personal_intelligence_engine.app.evaluation.runner import ExtractionEvaluationRun

DEFAULT_LIMITATIONS = [
    "This report uses synthetic fixtures only.",
    "Scores are deterministic lexical checks, not proof of semantic quality.",
    "No RAG, embeddings, dashboard, or external model benchmark is included.",
    "Optional local LLM results can vary by model, prompt, hardware, and runtime settings.",
    "Human review is still required before trusting extracted personal knowledge.",
]


def render_extraction_evaluation_report(
    run: ExtractionEvaluationRun,
    *,
    generated_at: datetime | None = None,
) -> str:
    """Render an extraction evaluation run as Markdown."""
    timestamp = generated_at or datetime.now(timezone.utc)
    passed = run.passed_count
    failed = run.fixture_count - run.passed_count

    lines = [
        "# Extraction Quality Evaluation Report",
        "",
        f"- **Generated at:** {timestamp.isoformat()}",
        f"- **Backend:** `{run.backend}`",
        f"- **Fixture count:** {run.fixture_count}",
        f"- **Average score:** {run.average_score:.2f}",
        f"- **Passed:** {passed}",
        f"- **Failed:** {failed}",
        "",
        "## Fixture Results",
        "",
        "| Fixture ID | Expected Type | Actual Type | Total Score | Field Scores | Status | Notes |",
        "| --- | --- | --- | ---: | --- | --- | --- |",
    ]

    for result in run.results:
        status = "PASS" if result.passed else "FAIL"
        notes = "; ".join(result.notes) if result.notes else "-"
        lines.append(
            "| "
            f"`{_escape_table_cell(result.fixture_id)}` | "
            f"`{_escape_table_cell(result.expected_entry_type)}` | "
            f"`{_escape_table_cell(result.actual_entry_type)}` | "
            f"{result.total_score:.2f} | "
            f"{_format_field_scores(result.field_scores)} | "
            f"{status} | "
            f"{_escape_table_cell(notes)} |"
        )

    lines.extend(
        [
            "",
            "## Limitations",
            "",
            *[f"- {limitation}" for limitation in DEFAULT_LIMITATIONS],
            "",
        ]
    )

    return "\n".join(lines)


def write_extraction_evaluation_report(
    run: ExtractionEvaluationRun,
    output_path: str | Path,
    *,
    generated_at: datetime | None = None,
) -> Path:
    """Write an extraction evaluation report to a Markdown file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_extraction_evaluation_report(run, generated_at=generated_at),
        encoding="utf-8",
    )
    return path


def _format_field_scores(field_scores: dict[str, float]) -> str:
    return "<br>".join(
        f"{_escape_table_cell(field)}={score:.2f}"
        for field, score in sorted(field_scores.items())
    )


def _escape_table_cell(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")
