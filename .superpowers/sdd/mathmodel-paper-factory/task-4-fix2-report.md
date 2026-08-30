# Task 4 fix2 report

## Files changed

- `mathmodel-skill/tests/test_quality.py`
- `mathmodel-skill/scripts/mmcore/quality.py`

## Round-2 fixes

- Added table-driven regression coverage for every missing required artifact file with exact `ARTIFACT-FILE-001` failure assertions.
- Added table-driven regression coverage for malformed JSON in every required artifact with exact `ARTIFACT-JSON-001` failure assertions.
- Added omitted required support field variants for question and claim records.
- Added non-string reference-list member coverage for question and claim support fields.
- Added independent broken-reference direction coverage for:
  - question to unknown model,
  - model to unknown question,
  - validation to unknown question,
  - figure to unknown claim.
- Added missing `source` / `file` path-field coverage for result and figure records.
- Added manual score input tests for list, string, and scalar values.
- Hardened `score_quality()` so non-dict manual input returns `manual_review: INVALID`, `release_status: FAIL`, and `manual_errors` instead of raising `AttributeError`.

## RED

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
test_each_malformed_required_artifact_is_a_hard_failure (test_quality.QualityTests.test_each_malformed_required_artifact_is_a_hard_failure) ... ok
test_each_missing_required_artifact_is_a_hard_failure (test_quality.QualityTests.test_each_missing_required_artifact_is_a_hard_failure) ... ok
test_failing_audit_cli_writes_report_and_returns_nonzero (test_quality.QualityTests.test_failing_audit_cli_writes_report_and_returns_nonzero) ... ok
test_independent_broken_cross_reference_directions_are_hard_failures (test_quality.QualityTests.test_independent_broken_cross_reference_directions_are_hard_failures) ... ok
test_invalid_registry_shapes_are_hard_failures (test_quality.QualityTests.test_invalid_registry_shapes_are_hard_failures) ... ok
test_manual_scores_reject_non_dict_inputs_without_crashing (test_quality.QualityTests.test_manual_scores_reject_non_dict_inputs_without_crashing) ... 
  test_manual_scores_reject_non_dict_inputs_without_crashing (test_quality.QualityTests.test_manual_scores_reject_non_dict_inputs_without_crashing) (manual=['bad']) ... ERROR
  test_manual_scores_reject_non_dict_inputs_without_crashing (test_quality.QualityTests.test_manual_scores_reject_non_dict_inputs_without_crashing) (manual='bad') ... ERROR
  test_manual_scores_reject_non_dict_inputs_without_crashing (test_quality.QualityTests.test_manual_scores_reject_non_dict_inputs_without_crashing) (manual=7) ... ERROR
test_manual_scores_require_complete_valid_input (test_quality.QualityTests.test_manual_scores_require_complete_valid_input) ... ok
test_missing_claim_support_is_hard_failure (test_quality.QualityTests.test_missing_claim_support_is_hard_failure) ... ok
test_missing_result_source_and_figure_file_fields_are_path_failures (test_quality.QualityTests.test_missing_result_source_and_figure_file_fields_are_path_failures) ... ok
test_missing_sources_figures_roles_and_validation_status_are_hard_failures (test_quality.QualityTests.test_missing_sources_figures_roles_and_validation_status_are_hard_failures) ... ok
test_non_string_reference_list_members_are_hard_failures (test_quality.QualityTests.test_non_string_reference_list_members_are_hard_failures) ... ok
test_omitted_required_support_fields_are_hard_failures (test_quality.QualityTests.test_omitted_required_support_fields_are_hard_failures) ... ok
test_required_claim_support_associations_are_non_empty (test_quality.QualityTests.test_required_claim_support_associations_are_non_empty) ... ok
test_required_question_associations_are_non_empty (test_quality.QualityTests.test_required_question_associations_are_non_empty) ... ok
test_result_and_figure_paths_must_stay_inside_project (test_quality.QualityTests.test_result_and_figure_paths_must_stay_inside_project) ... ok

======================================================================
ERROR: test_manual_scores_reject_non_dict_inputs_without_crashing (test_quality.QualityTests.test_manual_scores_reject_non_dict_inputs_without_crashing) (manual=['bad'])
----------------------------------------------------------------------
Traceback (most recent call last):
  File "E:\Projects\school\mathmodel\mathmodel-skill\tests\test_quality.py", line 393, in test_manual_scores_reject_non_dict_inputs_without_crashing
    scored = score_quality([], manual)
  File "E:\Projects\school\mathmodel\mathmodel-skill\scripts\mmcore\quality.py", line 73, in score_quality
    manual_scores, manual_errors, manual_review = _validate_manual(manual or {})
                                                  ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
  File "E:\Projects\school\mathmodel\mathmodel-skill\scripts\mmcore\quality.py", line 53, in _validate_manual
    for name, value in manual.items():
                       ^^^^^^^^^^^^
AttributeError: 'list' object has no attribute 'items'

======================================================================
ERROR: test_manual_scores_reject_non_dict_inputs_without_crashing (test_quality.QualityTests.test_manual_scores_reject_non_dict_inputs_without_crashing) (manual='bad')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "E:\Projects\school\mathmodel\mathmodel-skill\tests\test_quality.py", line 393, in test_manual_scores_reject_non_dict_inputs_without_crashing
    scored = score_quality([], manual)
  File "E:\Projects\school\mathmodel\mathmodel-skill\scripts\mmcore\quality.py", line 73, in score_quality
    manual_scores, manual_errors, manual_review = _validate_manual(manual or {})
                                                  ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
  File "E:\Projects\school\mathmodel\mathmodel-skill\scripts\mmcore\quality.py", line 53, in _validate_manual
    for name, value in manual.items():
                       ^^^^^^^^^^^^
AttributeError: 'str' object has no attribute 'items'

======================================================================
ERROR: test_manual_scores_reject_non_dict_inputs_without_crashing (test_quality.QualityTests.test_manual_scores_reject_non_dict_inputs_without_crashing) (manual=7)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "E:\Projects\school\mathmodel\mathmodel-skill\tests\test_quality.py", line 393, in test_manual_scores_reject_non_dict_inputs_without_crashing
    scored = score_quality([], manual)
  File "E:\Projects\school\mathmodel\mathmodel-skill\scripts\mmcore\quality.py", line 73, in score_quality
    manual_scores, manual_errors, manual_review = _validate_manual(manual or {})
                                                  ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
  File "E:\Projects\school\mathmodel\mathmodel-skill\scripts\mmcore\quality.py", line 53, in _validate_manual
    for name, value in manual.items():
                       ^^^^^^^^^^^^
AttributeError: 'int' object has no attribute 'items'

----------------------------------------------------------------------
Ran 20 tests in 0.694s

FAILED (errors=3)
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
test_each_malformed_required_artifact_is_a_hard_failure (test_quality.QualityTests.test_each_malformed_required_artifact_is_a_hard_failure) ... ok
test_each_missing_required_artifact_is_a_hard_failure (test_quality.QualityTests.test_each_missing_required_artifact_is_a_hard_failure) ... ok
test_failing_audit_cli_writes_report_and_returns_nonzero (test_quality.QualityTests.test_failing_audit_cli_writes_report_and_returns_nonzero) ... ok
test_independent_broken_cross_reference_directions_are_hard_failures (test_quality.QualityTests.test_independent_broken_cross_reference_directions_are_hard_failures) ... ok
test_invalid_registry_shapes_are_hard_failures (test_quality.QualityTests.test_invalid_registry_shapes_are_hard_failures) ... ok
test_manual_scores_reject_non_dict_inputs_without_crashing (test_quality.QualityTests.test_manual_scores_reject_non_dict_inputs_without_crashing) ... ok
test_manual_scores_require_complete_valid_input (test_quality.QualityTests.test_manual_scores_require_complete_valid_input) ... ok
test_missing_claim_support_is_hard_failure (test_quality.QualityTests.test_missing_claim_support_is_hard_failure) ... ok
test_missing_result_source_and_figure_file_fields_are_path_failures (test_quality.QualityTests.test_missing_result_source_and_figure_file_fields_are_path_failures) ... ok
test_missing_sources_figures_roles_and_validation_status_are_hard_failures (test_quality.QualityTests.test_missing_sources_figures_roles_and_validation_status_are_hard_failures) ... ok
test_non_string_reference_list_members_are_hard_failures (test_quality.QualityTests.test_non_string_reference_list_members_are_hard_failures) ... ok
test_omitted_required_support_fields_are_hard_failures (test_quality.QualityTests.test_omitted_required_support_fields_are_hard_failures) ... ok
test_required_claim_support_associations_are_non_empty (test_quality.QualityTests.test_required_claim_support_associations_are_non_empty) ... ok
test_required_question_associations_are_non_empty (test_quality.QualityTests.test_required_question_associations_are_non_empty) ... ok
test_result_and_figure_paths_must_stay_inside_project (test_quality.QualityTests.test_result_and_figure_paths_must_stay_inside_project) ... ok

----------------------------------------------------------------------
Ran 20 tests in 0.753s

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
test_out_of_root_recognized_symlink_is_warned_or_skipped (test_manifest.ManifestTests.test_out_of_root_recognized_symlink_is_warned_or_skipped) ... skipped "symlink creation unavailable: [WinError 1314] �ͻ���û���������Ȩ��: 'C:\\Users\\32583\\AppData\\Local\\Temp\\tmpu8eogyx8\\outside.py' -> 'C:\\Users\\32583\\AppData\\Local\\Temp\\tmpsppoq9il\\linked.py'"
test_run_id_is_utc_timestamp_plus_corresponding_config_hash (test_manifest.ManifestTests.test_run_id_is_utc_timestamp_plus_corresponding_config_hash) ... ok
test_run_manifest_records_input_hash_and_stages (test_manifest.ManifestTests.test_run_manifest_records_input_hash_and_stages) ... ok
test_sha256_is_stable (test_manifest.ManifestTests.test_sha256_is_stable) ... ok
test_audit_cli_writes_machine_reports_and_prints_json (test_quality.QualityTests.test_audit_cli_writes_machine_reports_and_prints_json) ... ok
test_check_records_include_contract_fields_and_evidence (test_quality.QualityTests.test_check_records_include_contract_fields_and_evidence) ... ok
test_clean_contract_scores_at_least_eighty_five (test_quality.QualityTests.test_clean_contract_scores_at_least_eighty_five) ... ok
test_configurable_figure_roles_are_enforced (test_quality.QualityTests.test_configurable_figure_roles_are_enforced) ... ok
test_duplicate_and_missing_ids_are_hard_failures (test_quality.QualityTests.test_duplicate_and_missing_ids_are_hard_failures) ... ok
test_each_malformed_required_artifact_is_a_hard_failure (test_quality.QualityTests.test_each_malformed_required_artifact_is_a_hard_failure) ... ok
test_each_missing_required_artifact_is_a_hard_failure (test_quality.QualityTests.test_each_missing_required_artifact_is_a_hard_failure) ... ok
test_failing_audit_cli_writes_report_and_returns_nonzero (test_quality.QualityTests.test_failing_audit_cli_writes_report_and_returns_nonzero) ... ok
test_independent_broken_cross_reference_directions_are_hard_failures (test_quality.QualityTests.test_independent_broken_cross_reference_directions_are_hard_failures) ... ok
test_invalid_registry_shapes_are_hard_failures (test_quality.QualityTests.test_invalid_registry_shapes_are_hard_failures) ... ok
test_manual_scores_reject_non_dict_inputs_without_crashing (test_quality.QualityTests.test_manual_scores_reject_non_dict_inputs_without_crashing) ... ok
test_manual_scores_require_complete_valid_input (test_quality.QualityTests.test_manual_scores_require_complete_valid_input) ... ok
test_missing_claim_support_is_hard_failure (test_quality.QualityTests.test_missing_claim_support_is_hard_failure) ... ok
test_missing_result_source_and_figure_file_fields_are_path_failures (test_quality.QualityTests.test_missing_result_source_and_figure_file_fields_are_path_failures) ... ok
test_missing_sources_figures_roles_and_validation_status_are_hard_failures (test_quality.QualityTests.test_missing_sources_figures_roles_and_validation_status_are_hard_failures) ... ok
test_non_string_reference_list_members_are_hard_failures (test_quality.QualityTests.test_non_string_reference_list_members_are_hard_failures) ... ok
test_omitted_required_support_fields_are_hard_failures (test_quality.QualityTests.test_omitted_required_support_fields_are_hard_failures) ... ok
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
Ran 41 tests in 0.977s

OK (skipped=1)
usage: mathmodel [-h] {init,adopt,inspect,audit} ...

positional arguments:
  {init,adopt,inspect,audit}

options:
  -h, --help            show this help message and exit
```
