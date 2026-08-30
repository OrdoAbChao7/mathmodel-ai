# Task 4 report — Evidence-contract validation and quality scoring

## Scope

Implemented only the Task 4 brief under `E:/Projects/school/mathmodel`:

- Created `mathmodel-skill/scripts/mmcore/contracts.py`.
- Created `mathmodel-skill/scripts/mmcore/quality.py`.
- Modified `mathmodel-skill/scripts/mathmodel.py` to add `audit PROJECT --json`.
- Created `mathmodel-skill/tests/test_quality.py`.

No subagents or reviewers were dispatched. No Git commit was created.

## Skill note

The TDD skill referenced `writing-good-tests.md`, but the file was not present at the advertised path. Exact output:

```text
Get-Content: 
Line |
   2 |  Get-Content -Raw 'D:\Dev\.codex\plugins\cache\openai-curated-remote\s …
     |  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
     | Cannot find path 'D:\Dev\.codex\plugins\cache\openai-curated-remote\superpowers\6.3.0\skills\writing-good-tests.md' because it does not exist.
```

Continued with the main RED-GREEN-REFACTOR instructions from `test-driven-development/SKILL.md`.

## RED

Command:

```powershell
python -m unittest discover -s mathmodel-skill/tests -p 'test_quality.py' -v
```

Output:

```text
test_quality (unittest.loader._FailedTest.test_quality) ... ERROR

======================================================================
ERROR: test_quality (unittest.loader._FailedTest.test_quality)
----------------------------------------------------------------------
ImportError: Failed to import test module: test_quality
Traceback (most recent call last):
  File "C:\Users\32583\AppData\Local\Programs\Python\Python313\Lib\unittest\loader.py", line 396, in _find_test_path
    module = self._get_module_from_name(name)
  File "C:\Users\32583\AppData\Local\Programs\Python\Python313\Lib\unittest\loader.py", line 339, in _get_module_from_name
    __import__(name)
    ~~~~~~~~~~^^^^^^
  File "E:\Projects\school\mathmodel\mathmodel-skill\tests\test_quality.py", line 15, in <module>
    from mmcore.contracts import validate_artifacts
ModuleNotFoundError: No module named 'mmcore.contracts'


----------------------------------------------------------------------
Ran 1 test in 0.000s

FAILED (errors=1)
```

Expected RED reason: Task 4 production modules did not exist yet.

## GREEN

Command:

```powershell
python -m unittest discover -s mathmodel-skill/tests -p 'test_quality.py' -v
```

Output:

```text
test_audit_cli_writes_machine_reports_and_prints_json (test_quality.QualityTests.test_audit_cli_writes_machine_reports_and_prints_json) ... ok
test_check_records_include_contract_fields_and_evidence (test_quality.QualityTests.test_check_records_include_contract_fields_and_evidence) ... ok
test_clean_contract_scores_at_least_eighty_five (test_quality.QualityTests.test_clean_contract_scores_at_least_eighty_five) ... ok
test_missing_claim_support_is_hard_failure (test_quality.QualityTests.test_missing_claim_support_is_hard_failure) ... ok

----------------------------------------------------------------------
Ran 4 tests in 0.073s

OK
```

## Complete-suite verification

Command:

```powershell
python -m unittest discover -s mathmodel-skill/tests -v
```

Output:

```text
test_load_config_accepts_minimal_valid_contract (test_config.ConfigTests.test_load_config_accepts_minimal_valid_contract) ... ok
test_main_help_returns_zero (test_config.ConfigTests.test_main_help_returns_zero) ... ok
test_rejects_appendix_ratio_above_one (test_config.ConfigTests.test_rejects_appendix_ratio_above_one) ... ok
test_rejects_path_escape (test_config.ConfigTests.test_rejects_path_escape) ... ok
test_inspect_writes_audit_and_manifest_and_prints_json (test_manifest.ManifestTests.test_inspect_writes_audit_and_manifest_and_prints_json) ... ok
test_inventory_uses_relative_posix_paths_and_warns_for_missing_inputs (test_manifest.ManifestTests.test_inventory_uses_relative_posix_paths_and_warns_for_missing_inputs) ... ok
test_manifest_records_complete_provenance_and_inventory_fields (test_manifest.ManifestTests.test_manifest_records_complete_provenance_and_inventory_fields) ... ok
test_new_run_creates_distinct_append_only_run_directories (test_manifest.ManifestTests.test_new_run_creates_distinct_append_only_run_directories) ... ok
test_out_of_root_recognized_candidate_is_warned_and_skipped_without_symlink (test_manifest.ManifestTests.test_out_of_root_recognized_candidate_is_warned_and_skipped_without_symlink) ... ok
test_out_of_root_recognized_symlink_is_warned_or_skipped (test_manifest.ManifestTests.test_out_of_root_recognized_symlink_is_warned_or_skipped) ... skipped "symlink creation unavailable: [WinError 1314] �ͻ���û���������Ȩ��: 'C:\\Users\\32583\\AppData\\Local\\Temp\\tmpks3d1_tx\\outside.py' -> 'C:\\Users\\32583\\AppData\\Local\\Temp\\tmpw7864d5x\\linked.py'"
test_run_id_is_utc_timestamp_plus_corresponding_config_hash (test_manifest.ManifestTests.test_run_id_is_utc_timestamp_plus_corresponding_config_hash) ... ok
test_run_manifest_records_input_hash_and_stages (test_manifest.ManifestTests.test_run_manifest_records_input_hash_and_stages) ... ok
test_sha256_is_stable (test_manifest.ManifestTests.test_sha256_is_stable) ... ok
test_audit_cli_writes_machine_reports_and_prints_json (test_quality.QualityTests.test_audit_cli_writes_machine_reports_and_prints_json) ... ok
test_check_records_include_contract_fields_and_evidence (test_quality.QualityTests.test_check_records_include_contract_fields_and_evidence) ... ok
test_clean_contract_scores_at_least_eighty_five (test_quality.QualityTests.test_clean_contract_scores_at_least_eighty_five) ... ok
test_missing_claim_support_is_hard_failure (test_quality.QualityTests.test_missing_claim_support_is_hard_failure) ... ok
test_adopt_does_not_replace_existing_configuration (test_scaffold.ScaffoldTests.test_adopt_does_not_replace_existing_configuration) ... ok
test_adopt_preserves_existing_paper_and_solver (test_scaffold.ScaffoldTests.test_adopt_preserves_existing_paper_and_solver) ... ok
test_adoption_report_categorizes_files_and_lists_framework_conflicts (test_scaffold.ScaffoldTests.test_adoption_report_categorizes_files_and_lists_framework_conflicts) ... ok
test_cli_dispatches_init_and_adopt (test_scaffold.ScaffoldTests.test_cli_dispatches_init_and_adopt) ... ok
test_cli_rejects_invalid_problem_type_cleanly (test_scaffold.ScaffoldTests.test_cli_rejects_invalid_problem_type_cleanly) ... error: unsupported problem type: unknown
ok
test_init_creates_contract_and_required_directories (test_scaffold.ScaffoldTests.test_init_creates_contract_and_required_directories) ... ok
test_init_never_overwrites_existing_file (test_scaffold.ScaffoldTests.test_init_never_overwrites_existing_file) ... ok
test_paper_template_has_executable_boundary_labels_and_clearpages (test_scaffold.ScaffoldTests.test_paper_template_has_executable_boundary_labels_and_clearpages) ... ok

----------------------------------------------------------------------
Ran 25 tests in 0.304s

OK (skipped=1)
usage: mathmodel [-h] {init,adopt,inspect,audit} ...

positional arguments:
  {init,adopt,inspect,audit}

options:
  -h, --help            show this help message and exit
```

## Git status

Command:

```powershell
git status --short
```

Output:

```text
fatal: not a git repository (or any of the parent directories): .git
```

## Implementation notes

- `validate_artifacts(project, required)` loads the seven required artifact files under `artifacts/` and reports hard failures for missing files, malformed JSON, invalid top-level JSON shapes, duplicate/missing stable IDs, broken cross-references, missing result source files, missing figure files, missing required figure roles, and non-`PASS` validation statuses.
- `audit_cross_references(artifacts)` checks question/model/result/claim/figure/validation ID references.
- `score_quality(checks, manual=None)` returns dimension scores using the exact required weights, weighted total, hard failures, manual review state, and release status. Hard failures force release failure regardless of score. With no manual input, `manual_review` is `PENDING`.
- `python mathmodel-skill/scripts/mathmodel.py audit PROJECT --json` loads config, validates artifacts, writes `build/quality-report.json` and `build/quality-report.md`, prints JSON with `--json`, and leaves page metrics as `PENDING` for Task 5.
