# Details

Date : 2026-05-30 15:48:15

Directory e:\\projetos\\pie

Total : 88 files,  10852 codes, 1397 comments, 3072 blanks, all 15321 lines

[Summary](results.md) / Details / [Diff Summary](diff.md) / [Diff Details](diff-details.md)

## Files
| filename | language | code | comment | blank | total |
| :--- | :--- | ---: | ---: | ---: | ---: |
| [.github/workflows/ci.yml](/.github/workflows/ci.yml) | YAML | 32 | 0 | 11 | 43 |
| [README.md](/README.md) | Markdown | 227 | 0 | 83 | 310 |
| [README.pt-BR.md](/README.pt-BR.md) | Markdown | 227 | 0 | 83 | 310 |
| [docs/architecture.md](/docs/architecture.md) | Markdown | 93 | 0 | 18 | 111 |
| [docs/assistant\_architecture.md](/docs/assistant_architecture.md) | Markdown | 100 | 0 | 43 | 143 |
| [docs/core\_v1\_gap\_analysis.md](/docs/core_v1_gap_analysis.md) | Markdown | 100 | 0 | 36 | 136 |
| [docs/current\_state.md](/docs/current_state.md) | Markdown | 108 | 0 | 29 | 137 |
| [docs/data\_model.md](/docs/data_model.md) | Markdown | 112 | 0 | 28 | 140 |
| [docs/git\_publication\_checklist.md](/docs/git_publication_checklist.md) | Markdown | 44 | 0 | 17 | 61 |
| [docs/human\_review\_design.md](/docs/human_review_design.md) | Markdown | 182 | 0 | 84 | 266 |
| [docs/phase\_2c\_issues.md](/docs/phase_2c_issues.md) | Markdown | 198 | 0 | 97 | 295 |
| [docs/privacy.md](/docs/privacy.md) | Markdown | 72 | 0 | 33 | 105 |
| [docs/review\_edit\_design.md](/docs/review_edit_design.md) | Markdown | 173 | 0 | 70 | 243 |
| [docs/roadmap.md](/docs/roadmap.md) | Markdown | 86 | 0 | 33 | 119 |
| [docs/simulated\_usage\_report.md](/docs/simulated_usage_report.md) | Markdown | 202 | 0 | 51 | 253 |
| [docs/troubleshooting.md](/docs/troubleshooting.md) | Markdown | 60 | 0 | 28 | 88 |
| [docs/usage\_playbook.md](/docs/usage_playbook.md) | Markdown | 152 | 0 | 60 | 212 |
| [docs/vision.md](/docs/vision.md) | Markdown | 45 | 0 | 21 | 66 |
| [examples/sample\_entries.json](/examples/sample_entries.json) | JSON | 33 | 0 | 1 | 34 |
| [migrations/001\_initial\_schema.sql](/migrations/001_initial_schema.sql) | MS SQL | 85 | 3 | 7 | 95 |
| [migrations/002\_add\_review\_audit\_actions.sql](/migrations/002_add_review_audit_actions.sql) | MS SQL | 60 | 4 | 6 | 70 |
| [migrations/003\_create\_structured\_entry\_revisions.sql](/migrations/003_create_structured_entry_revisions.sql) | MS SQL | 13 | 2 | 2 | 17 |
| [migrations/004\_add\_soft\_delete.sql](/migrations/004_add_soft_delete.sql) | MS SQL | 2 | 2 | 2 | 6 |
| [migrations/005\_add\_delete\_audit\_actions.sql](/migrations/005_add_delete_audit_actions.sql) | MS SQL | 63 | 4 | 6 | 73 |
| [personal\_intelligence\_engine/\_\_init\_\_.py](/personal_intelligence_engine/__init__.py) | Python | 1 | 1 | 2 | 4 |
| [personal\_intelligence\_engine/app/\_\_init\_\_.py](/personal_intelligence_engine/app/__init__.py) | Python | 0 | 1 | 1 | 2 |
| [personal\_intelligence\_engine/app/adapters/\_\_init\_\_.py](/personal_intelligence_engine/app/adapters/__init__.py) | Python | 0 | 1 | 1 | 2 |
| [personal\_intelligence\_engine/app/adapters/fake\_extractor.py](/personal_intelligence_engine/app/adapters/fake_extractor.py) | Python | 61 | 39 | 12 | 112 |
| [personal\_intelligence\_engine/app/adapters/local\_llm\_extractor.py](/personal_intelligence_engine/app/adapters/local_llm_extractor.py) | Python | 304 | 17 | 58 | 379 |
| [personal\_intelligence\_engine/app/adapters/markdown\_writer.py](/personal_intelligence_engine/app/adapters/markdown_writer.py) | Python | 75 | 23 | 23 | 121 |
| [personal\_intelligence\_engine/app/cli/\_\_init\_\_.py](/personal_intelligence_engine/app/cli/__init__.py) | Python | 0 | 1 | 1 | 2 |
| [personal\_intelligence\_engine/app/cli/commands.py](/personal_intelligence_engine/app/cli/commands.py) | Python | 721 | 104 | 122 | 947 |
| [personal\_intelligence\_engine/app/config.py](/personal_intelligence_engine/app/config.py) | Python | 115 | 8 | 13 | 136 |
| [personal\_intelligence\_engine/app/domain/\_\_init\_\_.py](/personal_intelligence_engine/app/domain/__init__.py) | Python | 0 | 1 | 1 | 2 |
| [personal\_intelligence\_engine/app/domain/schemas.py](/personal_intelligence_engine/app/domain/schemas.py) | Python | 224 | 36 | 72 | 332 |
| [personal\_intelligence\_engine/app/domain/types.py](/personal_intelligence_engine/app/domain/types.py) | Python | 40 | 7 | 19 | 66 |
| [personal\_intelligence\_engine/app/evaluation/\_\_init\_\_.py](/personal_intelligence_engine/app/evaluation/__init__.py) | Python | 23 | 1 | 3 | 27 |
| [personal\_intelligence\_engine/app/evaluation/report.py](/personal_intelligence_engine/app/evaluation/report.py) | Python | 77 | 3 | 17 | 97 |
| [personal\_intelligence\_engine/app/evaluation/runner.py](/personal_intelligence_engine/app/evaluation/runner.py) | Python | 103 | 10 | 30 | 143 |
| [personal\_intelligence\_engine/app/evaluation/scoring.py](/personal_intelligence_engine/app/evaluation/scoring.py) | Python | 103 | 15 | 46 | 164 |
| [personal\_intelligence\_engine/app/main.py](/personal_intelligence_engine/app/main.py) | Python | 623 | 103 | 83 | 809 |
| [personal\_intelligence\_engine/app/prompts/extraction\_prompt.md](/personal_intelligence_engine/app/prompts/extraction_prompt.md) | Markdown | 31 | 0 | 7 | 38 |
| [personal\_intelligence\_engine/app/repositories/\_\_init\_\_.py](/personal_intelligence_engine/app/repositories/__init__.py) | Python | 0 | 1 | 1 | 2 |
| [personal\_intelligence\_engine/app/repositories/audit\_repository.py](/personal_intelligence_engine/app/repositories/audit_repository.py) | Python | 34 | 10 | 9 | 53 |
| [personal\_intelligence\_engine/app/repositories/database.py](/personal_intelligence_engine/app/repositories/database.py) | Python | 124 | 43 | 37 | 204 |
| [personal\_intelligence\_engine/app/repositories/entries\_repository.py](/personal_intelligence_engine/app/repositories/entries_repository.py) | Python | 278 | 241 | 27 | 546 |
| [personal\_intelligence\_engine/app/repositories/reports\_repository.py](/personal_intelligence_engine/app/repositories/reports_repository.py) | Python | 29 | 9 | 8 | 46 |
| [personal\_intelligence\_engine/app/repositories/revisions\_repository.py](/personal_intelligence_engine/app/repositories/revisions_repository.py) | Python | 31 | 14 | 8 | 53 |
| [personal\_intelligence\_engine/app/services/\_\_init\_\_.py](/personal_intelligence_engine/app/services/__init__.py) | Python | 0 | 1 | 1 | 2 |
| [personal\_intelligence\_engine/app/services/audit\_service.py](/personal_intelligence_engine/app/services/audit_service.py) | Python | 23 | 11 | 8 | 42 |
| [personal\_intelligence\_engine/app/services/backup\_export\_service.py](/personal_intelligence_engine/app/services/backup_export_service.py) | Python | 121 | 18 | 36 | 175 |
| [personal\_intelligence\_engine/app/services/extraction\_service.py](/personal_intelligence_engine/app/services/extraction_service.py) | Python | 12 | 16 | 11 | 39 |
| [personal\_intelligence\_engine/app/services/ingestion\_service.py](/personal_intelligence_engine/app/services/ingestion_service.py) | Python | 17 | 10 | 10 | 37 |
| [personal\_intelligence\_engine/app/services/markdown\_service.py](/personal_intelligence_engine/app/services/markdown_service.py) | Python | 20 | 11 | 7 | 38 |
| [personal\_intelligence\_engine/app/services/report\_service.py](/personal_intelligence_engine/app/services/report_service.py) | Python | 335 | 58 | 71 | 464 |
| [personal\_intelligence\_engine/app/services/reprocess\_service.py](/personal_intelligence_engine/app/services/reprocess_service.py) | Python | 180 | 20 | 31 | 231 |
| [personal\_intelligence\_engine/app/services/validation\_service.py](/personal_intelligence_engine/app/services/validation_service.py) | Python | 32 | 13 | 9 | 54 |
| [tests/conftest.py](/tests/conftest.py) | Python | 24 | 4 | 9 | 37 |
| [tests/fixtures/extraction\_quality\_cases.json](/tests/fixtures/extraction_quality_cases.json) | JSON | 137 | 0 | 1 | 138 |
| [tests/fixtures/prompt\_regression\_cases.json](/tests/fixtures/prompt_regression_cases.json) | JSON | 62 | 0 | 1 | 63 |
| [tests/test\_add\_overrides.py](/tests/test_add_overrides.py) | Python | 302 | 61 | 87 | 450 |
| [tests/test\_audit\_log.py](/tests/test_audit_log.py) | Python | 129 | 13 | 29 | 171 |
| [tests/test\_backup\_export\_cli.py](/tests/test_backup_export_cli.py) | Python | 149 | 25 | 59 | 233 |
| [tests/test\_cli.py](/tests/test_cli.py) | Python | 69 | 2 | 32 | 103 |
| [tests/test\_config.py](/tests/test_config.py) | Python | 16 | 1 | 6 | 23 |
| [tests/test\_daily\_report.py](/tests/test_daily_report.py) | Python | 138 | 18 | 40 | 196 |
| [tests/test\_database\_schema.py](/tests/test_database_schema.py) | Python | 200 | 36 | 36 | 272 |
| [tests/test\_entries\_cli.py](/tests/test_entries_cli.py) | Python | 199 | 80 | 121 | 400 |
| [tests/test\_extraction\_quality\_cli.py](/tests/test_extraction_quality_cli.py) | Python | 41 | 1 | 19 | 61 |
| [tests/test\_extraction\_quality\_fixtures.py](/tests/test_extraction_quality_fixtures.py) | Python | 70 | 1 | 29 | 100 |
| [tests/test\_extraction\_quality\_report.py](/tests/test_extraction_quality_report.py) | Python | 74 | 1 | 14 | 89 |
| [tests/test\_extraction\_quality\_runner.py](/tests/test_extraction_quality_runner.py) | Python | 86 | 2 | 22 | 110 |
| [tests/test\_extraction\_quality\_scoring.py](/tests/test_extraction_quality_scoring.py) | Python | 79 | 1 | 32 | 112 |
| [tests/test\_extraction\_service.py](/tests/test_extraction_service.py) | Python | 17 | 1 | 8 | 26 |
| [tests/test\_extractor\_selection.py](/tests/test_extractor_selection.py) | Python | 79 | 1 | 34 | 114 |
| [tests/test\_fake\_extractor.py](/tests/test_fake_extractor.py) | Python | 54 | 11 | 18 | 83 |
| [tests/test\_ingestion.py](/tests/test_ingestion.py) | Python | 81 | 12 | 29 | 122 |
| [tests/test\_local\_llm\_extractor.py](/tests/test_local_llm_extractor.py) | Python | 150 | 1 | 59 | 210 |
| [tests/test\_main\_static.py](/tests/test_main_static.py) | Python | 4 | 1 | 5 | 10 |
| [tests/test\_markdown\_generation.py](/tests/test_markdown_generation.py) | Python | 60 | 11 | 19 | 90 |
| [tests/test\_prompt\_contract.py](/tests/test_prompt_contract.py) | Python | 25 | 1 | 10 | 36 |
| [tests/test\_reprocess\_cli.py](/tests/test_reprocess_cli.py) | Python | 505 | 34 | 151 | 690 |
| [tests/test\_review\_cli.py](/tests/test_review_cli.py) | Python | 389 | 21 | 157 | 567 |
| [tests/test\_robustness\_features.py](/tests/test_robustness_features.py) | Python | 258 | 37 | 80 | 375 |
| [tests/test\_schema.py](/tests/test_schema.py) | Python | 113 | 7 | 26 | 146 |
| [tests/test\_smoke\_simulation.py](/tests/test_smoke_simulation.py) | Python | 603 | 102 | 198 | 903 |
| [tests/test\_structured\_entry\_revisions.py](/tests/test_structured_entry_revisions.py) | Python | 90 | 1 | 21 | 112 |
| [tests/test\_weekly\_project\_reports.py](/tests/test_weekly_project_reports.py) | Python | 443 | 48 | 86 | 577 |

[Summary](results.md) / Details / [Diff Summary](diff.md) / [Diff Details](diff-details.md)