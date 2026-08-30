# Task 4 fix report

## Files changed

- `mathmodel-skill/scripts/mmcore/contracts.py`
- `mathmodel-skill/scripts/mmcore/quality.py`
- `mathmodel-skill/scripts/mathmodel.py`
- `mathmodel-skill/tests/test_quality.py`

## Review findings fixed

- Added strict per-registry top-level shape validation:
  - `problem-map.json` must be an object with non-empty `questions` list.
  - `model-registry.json` must be an object with non-empty `models` list.
  - `result-registry.json` must be an object with non-empty `results` list.
  - `claim-registry.json` must be an object with non-empty `claims` list.
  - `figure-registry.json` must be an object with non-empty `figures` list.
  - `validation.json` must be an object with non-empty `validations` list.
  - `data-audit.json` must be an object with a non-empty string `status`.
- Added hard-fail checks for non-dict registry records.
- Added hard-fail checks for missing or empty required evidence associations:
  - question `model_ids`, `result_ids`, `validation_ids`, and `claim_ids`;
  - claim `result_ids` and `validation_ids`.
- Added project-root containment checks for result source paths and figure file paths:
  - absolute paths fail;
  - `..` escapes fail;
  - file existence is checked only after the path is accepted as project-scoped.
- Updated check records to preserve both `path` and `evidence`.
- Added controlled manual score validation:
  - invalid manual values return `manual_review: INVALID`, `release_status: FAIL`, and `manual_errors`;
  - partial valid manual scores keep `manual_review: PENDING`;
  - only a complete valid score set marks manual review `COMPLETE`.
- Updated `audit PROJECT --json` to return non-zero for release-gate failure while still writing reports.
- Expanded `test_quality.py` to cover hard gates, configurable roles, path escapes, manual scoring, and failing CLI behavior.

## RED

Command:

```powershell
python -m unittest discover -s mathmodel-skill/tests -p 'test_quality.py' -v
```

Output:

```text
test_audit_cli_writes_machine_reports_and_prints_json (test_quality.QualityTests.test_audit_cli_writes_machine_reports_and_prints_json) ... ok
test_check_records_include_contract_fields_and_evidence (test_quality.QualityTests.test_check_records_include_contract_fields_and_evidence) ... FAIL
test_clean_contract_scores_at_least_eighty_five (test_quality.QualityTests.test_clean_contract_scores_at_least_eighty_five) ... ok
test_configurable_figure_roles_are_enforced (test_quality.QualityTests.test_configurable_figure_roles_are_enforced) ... ERROR
test_duplicate_and_missing_ids_are_hard_failures (test_quality.QualityTests.test_duplicate_and_missing_ids_are_hard_failures) ... ok
test_failing_audit_cli_writes_report_and_returns_nonzero (test_quality.QualityTests.test_failing_audit_cli_writes_report_and_returns_nonzero) ... FAIL
test_invalid_registry_shapes_are_hard_failures (test_quality.QualityTests.test_invalid_registry_shapes_are_hard_failures) ... 
  test_invalid_registry_shapes_are_hard_failures (test_quality.QualityTests.test_invalid_registry_shapes_are_hard_failures) (stem='problem-map') ... FAIL
  test_invalid_registry_shapes_are_hard_failures (test_quality.QualityTests.test_invalid_registry_shapes_are_hard_failures) (stem='data-audit') ... FAIL
  test_invalid_registry_shapes_are_hard_failures (test_quality.QualityTests.test_invalid_registry_shapes_are_hard_failures) (stem='model-registry') ... FAIL
  test_invalid_registry_shapes_are_hard_failures (test_quality.QualityTests.test_invalid_registry_shapes_are_hard_failures) (stem='result-registry') ... FAIL
  test_invalid_registry_shapes_are_hard_failures (test_quality.QualityTests.test_invalid_registry_shapes_are_hard_failures) (stem='claim-registry') ... FAIL
  test_invalid_registry_shapes_are_hard_failures (test_quality.QualityTests.test_invalid_registry_shapes_are_hard_failures) (stem='figure-registry') ... ERROR
  test_invalid_registry_shapes_are_hard_failures (test_quality.QualityTests.test_invalid_registry_shapes_are_hard_failures) (stem='validation') ... FAIL
test_manual_scores_require_complete_valid_input (test_quality.QualityTests.test_manual_scores_require_complete_valid_input) ... FAIL
test_missing_claim_support_is_hard_failure (test_quality.QualityTests.test_missing_claim_support_is_hard_failure) ... ok
test_missing_sources_figures_roles_and_validation_status_are_hard_failures (test_quality.QualityTests.test_missing_sources_figures_roles_and_validation_status_are_hard_failures) ... ok
test_required_claim_support_associations_are_non_empty (test_quality.QualityTests.test_required_claim_support_associations_are_non_empty) ... 
  test_required_claim_support_associations_are_non_empty (test_quality.QualityTests.test_required_claim_support_associations_are_non_empty) (field='result_ids') ... FAIL
  test_required_claim_support_associations_are_non_empty (test_quality.QualityTests.test_required_claim_support_associations_are_non_empty) (field='validation_ids') ... FAIL
test_required_question_associations_are_non_empty (test_quality.QualityTests.test_required_question_associations_are_non_empty) ... 
  test_required_question_associations_are_non_empty (test_quality.QualityTests.test_required_question_associations_are_non_empty) (field='model_ids') ... FAIL
  test_required_question_associations_are_non_empty (test_quality.QualityTests.test_required_question_associations_are_non_empty) (field='result_ids') ... FAIL
  test_required_question_associations_are_non_empty (test_quality.QualityTests.test_required_question_associations_are_non_empty) (field='validation_ids') ... FAIL
  test_required_question_associations_are_non_empty (test_quality.QualityTests.test_required_question_associations_are_non_empty) (field='claim_ids') ... FAIL
test_result_and_figure_paths_must_stay_inside_project (test_quality.QualityTests.test_result_and_figure_paths_must_stay_inside_project) ... 
  test_result_and_figure_paths_must_stay_inside_project (test_quality.QualityTests.test_result_and_figure_paths_must_stay_inside_project) (artifact='result-registry') ... FAIL
  test_result_and_figure_paths_must_stay_inside_project (test_quality.QualityTests.test_result_and_figure_paths_must_stay_inside_project) (artifact='figure-registry') ... FAIL

======================================================================
ERROR: test_configurable_figure_roles_are_enforced (test_quality.QualityTests.test_configurable_figure_roles_are_enforced)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "E:\Projects\school\mathmodel\mathmodel-skill\tests\test_quality.py", line 233, in test_configurable_figure_roles_are_enforced
    self.assertIn("diagnostic", role_check["evidence"]["missing_roles"])
                                ~~~~~~~~~~^^^^^^^^^^^^
KeyError: 'evidence'

======================================================================
ERROR: test_invalid_registry_shapes_are_hard_failures (test_quality.QualityTests.test_invalid_registry_shapes_are_hard_failures) (stem='figure-registry')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "E:\Projects\school\mathmodel\mathmodel-skill\tests\test_quality.py", line 173, in test_invalid_registry_shapes_are_hard_failures
    report = validate_artifacts(self.root, REQUIRED)
  File "E:\Projects\school\mathmodel\mathmodel-skill\scripts\mmcore\contracts.py", line 314, in validate_artifacts
    checks.extend(_duplicate_checks(artifacts))
                  ~~~~~~~~~~~~~~~~~^^^^^^^^^^^
  File "E:\Projects\school\mathmodel\mathmodel-skill\scripts\mmcore\contracts.py", line 98, in _duplicate_checks
    for item in _items(artifacts.get(artifact), field):
                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "E:\Projects\school\mathmodel\mathmodel-skill\scripts\mmcore\contracts.py", line 77, in _items
    return [item for item in value if isinstance(item, dict)]
                             ^^^^^
TypeError: 'NoneType' object is not iterable

======================================================================
FAIL: test_check_records_include_contract_fields_and_evidence (test_quality.QualityTests.test_check_records_include_contract_fields_and_evidence)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "E:\Projects\school\mathmodel\mathmodel-skill\tests\test_quality.py", line 157, in test_check_records_include_contract_fields_and_evidence
    self.assertIn("evidence", check)
    ~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^
AssertionError: 'evidence' not found in {'rule': 'ARTIFACT-FILE-001', 'severity': 'FAIL', 'status': 'PASS', 'message': 'loaded required artifact problem-map.json', 'path': 'artifacts/problem-map.json'}

======================================================================
FAIL: test_failing_audit_cli_writes_report_and_returns_nonzero (test_quality.QualityTests.test_failing_audit_cli_writes_report_and_returns_nonzero)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "E:\Projects\school\mathmodel\mathmodel-skill\tests\test_quality.py", line 316, in test_failing_audit_cli_writes_report_and_returns_nonzero
    self.assertEqual(exit_code, 1)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
AssertionError: 0 != 1

======================================================================
FAIL: test_invalid_registry_shapes_are_hard_failures (test_quality.QualityTests.test_invalid_registry_shapes_are_hard_failures) (stem='problem-map')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "E:\Projects\school\mathmodel\mathmodel-skill\tests\test_quality.py", line 175, in test_invalid_registry_shapes_are_hard_failures
    self.assertTrue(any(c["rule"].startswith("ARTIFACT-SHAPE") for c in report["checks"]))
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true

======================================================================
FAIL: test_invalid_registry_shapes_are_hard_failures (test_quality.QualityTests.test_invalid_registry_shapes_are_hard_failures) (stem='data-audit')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "E:\Projects\school\mathmodel\mathmodel-skill\tests\test_quality.py", line 174, in test_invalid_registry_shapes_are_hard_failures
    self.assertEqual(report["status"], "FAIL")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'PASS' != 'FAIL'
- PASS
+ FAIL

======================================================================
FAIL: test_invalid_registry_shapes_are_hard_failures (test_quality.QualityTests.test_invalid_registry_shapes_are_hard_failures) (stem='model-registry')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "E:\Projects\school\mathmodel\mathmodel-skill\tests\test_quality.py", line 175, in test_invalid_registry_shapes_are_hard_failures
    self.assertTrue(any(c["rule"].startswith("ARTIFACT-SHAPE") for c in report["checks"]))
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true

======================================================================
FAIL: test_invalid_registry_shapes_are_hard_failures (test_quality.QualityTests.test_invalid_registry_shapes_are_hard_failures) (stem='result-registry')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "E:\Projects\school\mathmodel\mathmodel-skill\tests\test_quality.py", line 175, in test_invalid_registry_shapes_are_hard_failures
    self.assertTrue(any(c["rule"].startswith("ARTIFACT-SHAPE") for c in report["checks"]))
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true

======================================================================
FAIL: test_invalid_registry_shapes_are_hard_failures (test_quality.QualityTests.test_invalid_registry_shapes_are_hard_failures) (stem='claim-registry')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "E:\Projects\school\mathmodel\mathmodel-skill\tests\test_quality.py", line 175, in test_invalid_registry_shapes_are_hard_failures
    self.assertTrue(any(c["rule"].startswith("ARTIFACT-SHAPE") for c in report["checks"]))
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true

======================================================================
FAIL: test_invalid_registry_shapes_are_hard_failures (test_quality.QualityTests.test_invalid_registry_shapes_are_hard_failures) (stem='validation')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "E:\Projects\school\mathmodel\mathmodel-skill\tests\test_quality.py", line 175, in test_invalid_registry_shapes_are_hard_failures
    self.assertTrue(any(c["rule"].startswith("ARTIFACT-SHAPE") for c in report["checks"]))
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true

======================================================================
FAIL: test_manual_scores_require_complete_valid_input (test_quality.QualityTests.test_manual_scores_require_complete_valid_input)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "E:\Projects\school\mathmodel\mathmodel-skill\tests\test_quality.py", line 254, in test_manual_scores_require_complete_valid_input
    self.assertEqual(partial["manual_review"], "PENDING")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'COMPLETE' != 'PENDING'
- COMPLETE
+ PENDING

======================================================================
FAIL: test_required_claim_support_associations_are_non_empty (test_quality.QualityTests.test_required_claim_support_associations_are_non_empty) (field='result_ids')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "E:\Projects\school\mathmodel\mathmodel-skill\tests\test_quality.py", line 206, in test_required_claim_support_associations_are_non_empty
    self.assertEqual(report["status"], "FAIL")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'PASS' != 'FAIL'
- PASS
+ FAIL

======================================================================
FAIL: test_required_claim_support_associations_are_non_empty (test_quality.QualityTests.test_required_claim_support_associations_are_non_empty) (field='validation_ids')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "E:\Projects\school\mathmodel\mathmodel-skill\tests\test_quality.py", line 206, in test_required_claim_support_associations_are_non_empty
    self.assertEqual(report["status"], "FAIL")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'PASS' != 'FAIL'
- PASS
+ FAIL

======================================================================
FAIL: test_required_question_associations_are_non_empty (test_quality.QualityTests.test_required_question_associations_are_non_empty) (field='model_ids')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "E:\Projects\school\mathmodel\mathmodel-skill\tests\test_quality.py", line 196, in test_required_question_associations_are_non_empty
    self.assertEqual(report["status"], "FAIL")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'PASS' != 'FAIL'
- PASS
+ FAIL

======================================================================
FAIL: test_required_question_associations_are_non_empty (test_quality.QualityTests.test_required_question_associations_are_non_empty) (field='result_ids')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "E:\Projects\school\mathmodel\mathmodel-skill\tests\test_quality.py", line 196, in test_required_question_associations_are_non_empty
    self.assertEqual(report["status"], "FAIL")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'PASS' != 'FAIL'
- PASS
+ FAIL

======================================================================
FAIL: test_required_question_associations_are_non_empty (test_quality.QualityTests.test_required_question_associations_are_non_empty) (field='validation_ids')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "E:\Projects\school\mathmodel\mathmodel-skill\tests\test_quality.py", line 196, in test_required_question_associations_are_non_empty
    self.assertEqual(report["status"], "FAIL")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'PASS' != 'FAIL'
- PASS
+ FAIL

======================================================================
FAIL: test_required_question_associations_are_non_empty (test_quality.QualityTests.test_required_question_associations_are_non_empty) (field='claim_ids')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "E:\Projects\school\mathmodel\mathmodel-skill\tests\test_quality.py", line 196, in test_required_question_associations_are_non_empty
    self.assertEqual(report["status"], "FAIL")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'PASS' != 'FAIL'
- PASS
+ FAIL

======================================================================
FAIL: test_result_and_figure_paths_must_stay_inside_project (test_quality.QualityTests.test_result_and_figure_paths_must_stay_inside_project) (artifact='result-registry')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "E:\Projects\school\mathmodel\mathmodel-skill\tests\test_quality.py", line 248, in test_result_and_figure_paths_must_stay_inside_project
    self.assertTrue(any(c["rule"] == rule and c["status"] == "FAIL" for c in report["checks"]))
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true

======================================================================
FAIL: test_result_and_figure_paths_must_stay_inside_project (test_quality.QualityTests.test_result_and_figure_paths_must_stay_inside_project) (artifact='figure-registry')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "E:\Projects\school\mathmodel\mathmodel-skill\tests\test_quality.py", line 248, in test_result_and_figure_paths_must_stay_inside_project
    self.assertTrue(any(c["rule"] == rule and c["status"] == "FAIL" for c in report["checks"]))
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true

----------------------------------------------------------------------
Ran 13 tests in 0.308s

FAILED (failures=17, errors=2)
```

## Focused suite after fixes

Command:

```powershell
python -m unittest discover -s mathmodel-skill/tests -p 'test_quality.py' -v
```

Output:

```text
test_audit_cli_writes_machine_reports_and_prints_json (test_quality.QualityTests.test_audit_cli_writes_machine_reports_and_prints_json) ... ok
test_check_records_include_contract_fields_and_evidence (test_quality.QualityTests.test_check_records_include_contract_fields_and_evidence) ... ok
test_clean_contract_scores_at_least_eighty_five (test_quality.QualityTests.test_clean_contract_scores_at_least_eighty_five) ... ok
test_configurable_figure_roles_are_enforced (test_quality.QualityTests.test_configurable_figure_roles_are_enforced) ... ok
test_duplicate_and_missing_ids_are_hard_failures (test_quality.QualityTests.test_duplicate_and_missing_ids_are_hard_failures) ... ok
test_failing_audit_cli_writes_report_and_returns_nonzero (test_quality.QualityTests.test_failing_audit_cli_writes_report_and_returns_nonzero) ... ok
test_invalid_registry_shapes_are_hard_failures (test_quality.QualityTests.test_invalid_registry_shapes_are_hard_failures) ... ok
test_manual_scores_require_complete_valid_input (test_quality.QualityTests.test_manual_scores_require_complete_valid_input) ... ok
test_missing_claim_support_is_hard_failure (test_quality.QualityTests.test_missing_claim_support_is_hard_failure) ... ok
test_missing_sources_figures_roles_and_validation_status_are_hard_failures (test_quality.QualityTests.test_missing_sources_figures_roles_and_validation_status_are_hard_failures) ... ok
test_required_claim_support_associations_are_non_empty (test_quality.QualityTests.test_required_claim_support_associations_are_non_empty) ... ok
test_required_question_associations_are_non_empty (test_quality.QualityTests.test_required_question_associations_are_non_empty) ... ok
test_result_and_figure_paths_must_stay_inside_project (test_quality.QualityTests.test_result_and_figure_paths_must_stay_inside_project) ... ok

----------------------------------------------------------------------
Ran 13 tests in 0.385s

OK
```

## Complete suite after fixes

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
test_out_of_root_recognized_symlink_is_warned_or_skipped (test_manifest.ManifestTests.test_out_of_root_recognized_symlink_is_warned_or_skipped) ... skipped "symlink creation unavailable: [WinError 1314] �ͻ���û���������Ȩ��: 'C:\\Users\\32583\\AppData\\Local\\Temp\\tmp2te8kzmi\\outside.py' -> 'C:\\Users\\32583\\AppData\\Local\\Temp\\tmpd1a5rs2h\\linked.py'"
test_run_id_is_utc_timestamp_plus_corresponding_config_hash (test_manifest.ManifestTests.test_run_id_is_utc_timestamp_plus_corresponding_config_hash) ... ok
test_run_manifest_records_input_hash_and_stages (test_manifest.ManifestTests.test_run_manifest_records_input_hash_and_stages) ... ok
test_sha256_is_stable (test_manifest.ManifestTests.test_sha256_is_stable) ... ok
test_audit_cli_writes_machine_reports_and_prints_json (test_quality.QualityTests.test_audit_cli_writes_machine_reports_and_prints_json) ... ok
test_check_records_include_contract_fields_and_evidence (test_quality.QualityTests.test_check_records_include_contract_fields_and_evidence) ... ok
test_clean_contract_scores_at_least_eighty_five (test_quality.QualityTests.test_clean_contract_scores_at_least_eighty_five) ... ok
test_configurable_figure_roles_are_enforced (test_quality.QualityTests.test_configurable_figure_roles_are_enforced) ... ok
test_duplicate_and_missing_ids_are_hard_failures (test_quality.QualityTests.test_duplicate_and_missing_ids_are_hard_failures) ... ok
test_failing_audit_cli_writes_report_and_returns_nonzero (test_quality.QualityTests.test_failing_audit_cli_writes_report_and_returns_nonzero) ... ok
test_invalid_registry_shapes_are_hard_failures (test_quality.QualityTests.test_invalid_registry_shapes_are_hard_failures) ... ok
test_manual_scores_require_complete_valid_input (test_quality.QualityTests.test_manual_scores_require_complete_valid_input) ... ok
test_missing_claim_support_is_hard_failure (test_quality.QualityTests.test_missing_claim_support_is_hard_failure) ... ok
test_missing_sources_figures_roles_and_validation_status_are_hard_failures (test_quality.QualityTests.test_missing_sources_figures_roles_and_validation_status_are_hard_failures) ... ok
test_required_claim_support_associations_are_non_empty (test_quality.QualityTests.test_required_claim_support_associations_are_non_empty) ... ok
test_required_question_associations_are_non_empty (test_quality.QualityTests.test_required_question_associations_are_non_empty) ... ok
test_result_and_figure_paths_must_stay_inside_project (test_quality.QualityTests.test_result_and_figure_paths_must_stay_inside_project) ... ok
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
Ran 34 tests in 0.581s

OK (skipped=1)
usage: mathmodel [-h] {init,adopt,inspect,audit} ...

positional arguments:
  {init,adopt,inspect,audit}

options:
  -h, --help            show this help message and exit
```
