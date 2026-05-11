# Phase 2C Issues: Lightweight Extraction Quality Evaluation

Phase 2C is a planning and evaluation phase. Its purpose is to measure extraction quality with synthetic data before making extractor or prompt changes.

Implementation status:

- Synthetic fixtures, expected outputs, deterministic scoring, local runner, Markdown report rendering, and the `pie evaluate extraction` CLI are implemented.
- Future work should stay lightweight and avoid RAG, embeddings, dashboards, and heavy model benchmarks.

Non-goals for this phase:

- No RAG.
- No embeddings.
- No vector database.
- No new external integrations.
- No fine-tuning.
- No broad model benchmark.

## Issue 1: Create Synthetic Evaluation Fixtures

### Objective

Create a small, representative set of synthetic text inputs for evaluating extraction quality.

### Scope

- Add synthetic fixtures for all current entry types.
- Include edge cases such as ambiguous notes, no project evidence, low-confidence text, and multi-signal text.
- Keep fixtures free of real personal data.
- Store fixtures in a format that can be reused by a future evaluation command or script.

### Out Of Scope

- Real user data.
- Large benchmark datasets.
- Automatically generated fixtures from an LLM.
- New extractor behavior.

### Acceptance Criteria

- Fixtures cover every `EntryType`.
- Fixtures are explicitly synthetic.
- Fixtures include at least one low-confidence or ambiguous case.
- Fixtures can be parsed as structured data by tests or scripts.

### Required Tests

- Validate fixture file syntax.
- Validate every fixture includes input text and an identifier.
- Validate fixture inputs contain no obvious real personal data patterns.

## Issue 2: Define Expected Outputs Per Entry Type

### Objective

Define expected extraction outputs for each synthetic fixture.

### Scope

- Specify expected `entry_type`.
- Specify expected `project` when there is clear evidence, otherwise `null`.
- Specify expected summary intent without requiring exact model wording.
- Specify expected tags and confidence bands.
- Document how ambiguous fixtures should be judged.

### Out Of Scope

- Perfect semantic equivalence scoring.
- Human review UI.
- Changes to Pydantic schemas.

### Acceptance Criteria

- Every fixture has an expected output.
- Expected outputs use the current extraction schema.
- Expected outputs avoid exact wording requirements where semantic variation is acceptable.
- Ambiguous cases document why they are ambiguous.

### Required Tests

- Validate expected outputs against the current Pydantic `ExtractionResult` schema.
- Validate `entry_type` values are from the current taxonomy.
- Validate confidence expectations are within `0.0` to `1.0`.

## Issue 3: Define Simple Scoring Rules

### Objective

Create a lightweight scoring model for extractor outputs.

### Scope

Score these fields:

- `entry_type`
- `project`
- `summary`
- `tags`
- `confidence`

Suggested approach:

- Exact match for `entry_type`.
- Exact or normalized match for `project`.
- Keyword or phrase overlap for `summary`.
- Set overlap for `tags`.
- Range or tolerance check for `confidence`.

### Out Of Scope

- Embedding similarity.
- Semantic search.
- LLM-as-judge scoring.
- Statistical benchmark claims.

### Acceptance Criteria

- Scoring is deterministic.
- Scoring output is easy to inspect.
- Each field score is visible independently.
- Total score is derived from field scores.

### Required Tests

- Unit tests for exact `entry_type` scoring.
- Unit tests for project null/non-null scoring.
- Unit tests for tag overlap.
- Unit tests for confidence tolerance or band scoring.
- Tests for deterministic total score.

## Issue 4: Create Lightweight Evaluation Command Or Script

### Objective

Create a small way to run synthetic evaluation locally.

### Scope

- Evaluate `FakeExtractor`.
- Optionally evaluate Ollama when configured.
- Load fixtures and expected outputs.
- Produce structured evaluation results.
- Keep the command/script local-only and dependency-light.

### Out Of Scope

- GitHub Actions model evaluation.
- Requiring Ollama in CI.
- Network services beyond optional local Ollama.
- Persistent evaluation tables in SQLite.

### Acceptance Criteria

- Evaluation can run without Ollama.
- Evaluation can optionally run with Ollama when configured.
- Missing Ollama produces a friendly skip or controlled error.
- Evaluation does not create PIE entries or reports in the main database.

### Required Tests

- Evaluation runs against `FakeExtractor`.
- Evaluation handles missing Ollama without failing tests.
- Evaluation uses synthetic fixtures only.
- Evaluation output includes per-fixture scores.

## Issue 5: Compare FakeExtractor Vs Ollama

### Objective

Compare deterministic and local LLM extraction results on the same synthetic fixtures.

### Scope

- Run both extractors on identical fixtures.
- Show side-by-side field scores.
- Identify fixture types where Ollama improves or regresses.
- Keep Ollama optional.

### Out Of Scope

- Ranking many local models.
- Automated model selection.
- Cloud model comparison.
- Prompt rewriting based on results.

### Acceptance Criteria

- FakeExtractor results are always available.
- Ollama comparison is included only when configured and healthy.
- Comparison report clearly labels backend, model name, and prompt version.
- No comparison uses real personal data.

### Required Tests

- Mock Ollama output for comparison tests.
- Validate comparison handles one backend missing.
- Validate backend labels are present.

## Issue 6: Generate Markdown Evaluation Report

### Objective

Generate a human-readable Markdown report from evaluation results.

### Scope

- Include total score.
- Include per-field scores.
- Include fixture-level pass/fail or needs-review status.
- Include backend, model name, prompt version, and run timestamp.
- Store output in a clearly synthetic/evaluation path.

### Out Of Scope

- PDF export.
- Dashboard.
- Historical trend storage.
- Publishing reports automatically.

### Acceptance Criteria

- Markdown report is readable in GitHub.
- Report does not include real personal data.
- Report cites fixture IDs.
- Report distinguishes `FakeExtractor` and Ollama results.

### Required Tests

- Markdown report file is created.
- Report contains fixture IDs.
- Report contains backend labels.
- Report contains score summaries.

## Issue 7: Document Local Model Selection Criteria

### Objective

Document practical criteria for choosing a local model for PIE extraction.

### Scope

- Explain JSON reliability.
- Explain latency and hardware constraints.
- Explain privacy considerations for local endpoints.
- Explain that model choice should be validated with synthetic fixtures.
- Avoid recommending one universal best model.

### Out Of Scope

- Sponsored recommendations.
- Cloud model recommendations.
- Exhaustive model benchmarks.
- Hardware buying guide.

### Acceptance Criteria

- Documentation is clear for a local-first user.
- Documentation distinguishes privacy, reliability, and performance.
- Documentation warns that results vary by model and machine.

### Required Tests

- Documentation link check if a docs link checker is later added.
- No automated tests required for content beyond basic repository checks.

## Issue 8: Document Evaluation Limitations

### Objective

Set expectations for what Phase 2C evaluation can and cannot prove.

### Scope

- Explain that synthetic fixtures do not prove real-world quality.
- Explain that scoring is approximate.
- Explain confidence calibration limits.
- Explain that semantic quality still needs human review.
- Explain that no memory should be trusted without source IDs.

### Out Of Scope

- Formal evaluation methodology.
- Statistical claims.
- Safety certification.

### Acceptance Criteria

- Limitations are visible near evaluation docs.
- Documentation avoids overstating quality.
- Documentation reinforces local-first and source-traceability principles.

### Required Tests

- No new tests required unless documentation tooling is added later.
