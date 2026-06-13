# PIE Core 7-Day Controlled Usage Playbook

PIE is alpha experimental software. This playbook is a short, controlled way to use PIE Core with real local data for seven days, while limiting privacy risk and collecting practical feedback before new features are added.

## Goal

Use PIE Core as a local memory log for one week to learn:

- which capture patterns feel natural;
- where extraction quality is weak;
- where review/reprocess/report workflows are confusing;
- which missing features matter most for Core v1.

Keep the test small. Prefer useful operational notes over exhaustive life logging.

## Before First Use — Set PIE_HOME

Set `PIE_HOME` to a fixed absolute directory before your first real session. This ensures all paths (database, notes, reports, backups, exports) always resolve under the same root, regardless of which working directory you run `pie` from.

```bash
# Add to your shell profile (~/.bashrc, ~/.zshrc, or equivalent):
export PIE_HOME="$HOME/.pie"
```

Once set, all paths default to `$PIE_HOME/pie.db`, `$PIE_HOME/notes/`, etc. You can still override individual paths with `PIE_DATABASE_PATH`, `PIE_NOTES_DIR`, etc. — absolute values always take precedence over `PIE_HOME`.

If you choose not to set `PIE_HOME`, PIE falls back to resolving paths from the current working directory (legacy behaviour). In that case, always run `pie` from the same directory to avoid silently creating separate databases.

## Daily Routine

1. Run `pie doctor` before the first real entry of the day and confirm paths:

```bash
pie doctor
```

`pie doctor` now shows the resolved `PIE_HOME` value. If `PIE_HOME` is not set, the output reads "not set — paths resolve from current directory" and any relative paths trigger a warning. Resolve this by setting `PIE_HOME` (recommended) or by always running `pie` from the same working directory.

2. Create a backup before the first real entry of the day:

```bash
pie backup create
```

3. Add 3 to 10 entries during the day:

```bash
pie add "Projeto: PIE. Tipo: decisão. Texto: Usar relatórios semanais para revisar progresso do Core. Tags: pie,relatorios"

# Or using explicit metadata flags:
pie add "Usar relatórios semanais para revisar progresso do Core" --project PIE --type decision --tag pie --tag relatorios
```

4. Review uncertain entries:

```bash
pie review list
pie review show <structured_entry_id>
pie review approve <structured_entry_id>
pie review reject <structured_entry_id>
pie review history <structured_entry_id>
```

5. Search when checking whether something was already captured:

```bash
pie search "relatórios semanais"
pie entries list --status needs_review
pie entries show <structured_entry_id>
```

6. Generate a daily report at the end of the day:

```bash
pie report daily --date YYYY-MM-DD
```

## Weekly Routine

At the end of seven days:

```bash
pie backup create
pie report weekly --date YYYY-MM-DD
pie report project --project PIE
pie export json
pie export markdown
```

Read the weekly and project reports, then write down friction points before adding any new feature.

## Entry Examples

Use a consistent format when possible:

- `Projeto: PIE. Tipo: decisão. Texto: Manter FakeExtractor como padrão durante testes reais. Tags: pie,extracao`
- `Projeto: PIE. Tipo: tarefa. Texto: Revisar entradas needs_review toda noite antes do relatório diário. Tags: review,rotina`
- `Projeto: PIE. Tipo: problema. Texto: O relatório semanal não deixou claro quais entradas precisam de revisão. Tags: reports,ux`
- `Projeto: Casa. Tipo: ideia. Texto: Criar um checklist local para manutenção mensal. Tags: organizacao,checklist`
- `Projeto: PIE. Tipo: revisão. Texto: A extração classificou uma decisão como ideia em duas entradas. Tags: qualidade,extracao`

Recommended format:

```text
Projeto: <nome>. Tipo: <decisão/tarefa/problema/ideia/revisão>. Texto: <conteúdo>. Tags: <tags>.
```

### Explicit Metadata Flags

Since version 0.1.0, you can also pass explicit flags to set metadata directly. This is useful to override or complement automatic extraction, ensuring 100% precision:

```bash
pie add "Decidir manter SQLite como fonte de verdade" --project PIE --type decision --tag arquitetura --tag sqlite
```

Options:
- `--project <name>`: Associates the entry to a specific project.
- `--type <type>`: Overrides the extracted type (e.g. `decision`, `idea`, `problem`, `candidate_task`).
- `--tag <tag>`: Adds tags to the entry (can be specified multiple times; merged and deduplicated case-insensitively).

---

## What To Record

- decisions you want to revisit;
- candidate tasks;
- project problems;
- useful insights;
- references or notes that should be searchable later;
- review notes about extraction quality;
- friction using CLI commands.

## What Not To Record

Do not put these into PIE during the controlled test:

- passwords;
- tokens or API keys;
- full bank details;
- sensitive personal documents;
- anything you would not want stored in local SQLite plaintext.

## Main Commands

```bash
pie add "..."
pie entries list
pie entries show <structured_entry_id>
pie search "<query>"
pie review list
pie review show <structured_entry_id>
pie review approve <structured_entry_id>
pie review reject <structured_entry_id>
pie review history <structured_entry_id>
pie entries reprocess <structured_entry_id> --dry-run
pie entries reprocess <structured_entry_id>
pie report daily --date YYYY-MM-DD
pie report weekly --date YYYY-MM-DD
pie report project --project <name>
pie backup create
pie export json
pie export markdown
```

## Privacy Checklist

- Keep `.env`, `pie.db`, `notes/`, `reports/`, `backups/`, and `exports/` out of Git.
- Keep backups/exports in a private local location.
- Use OS-level disk encryption if testing with real data.
- Do not point optional Ollama settings at a remote or shared server unless you understand the privacy impact.
- Review reports before sharing any file generated by PIE.

## Backup Checklist

- Run `pie backup create` before the first real usage session.
- Run `pie backup create` before batch reprocessing.
- Run `pie backup create` before exporting data.
- Keep at least one backup from before the seven-day test.
- Delete old backups if they are no longer needed and contain sensitive data.
- After purging entries, review old backups, exports, notes, and reports because they may still contain data that no longer exists in the live database.

## Handling Poor Extraction Without Review Edit

`pie review edit` is not implemented yet. If extraction is poor:

1. Inspect the entry:

```bash
pie review show <structured_entry_id>
pie review history <structured_entry_id>
```

2. Reject the bad structured extraction:

```bash
pie review reject <structured_entry_id>
```

3. Add a corrected new entry with clearer wording:

```bash
pie add "Projeto: PIE. Tipo: decisão. Texto: Corrigindo entrada anterior: manter revisão humana antes da Assistant Layer. Tags: pie,review"
```

4. Use search/history to preserve traceability:

```bash
pie search "Corrigindo entrada anterior"
pie review history <structured_entry_id>
```

## Deciding The Next Features

After seven days, prioritize features using these questions:

- Which command caused repeated friction?
- Did reports help real decisions, or only summarize obvious data?
- How often did extraction need correction?
- Is `review edit` necessary before Core v1 feels usable?
- Did stale Markdown after reprocessing create confusion?
- Was search good enough without embeddings?
- Were backups and exports easy enough to trust?

Prefer improving Core reliability and review workflows before building the Assistant Layer.
