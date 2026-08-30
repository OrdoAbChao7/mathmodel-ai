# Task 3 implementation report

## Scope

Implemented only Task 3: project inventory, chunked SHA-256 hashing, append-only run manifests and stage updates, plus `inspect PROJECT --json` dispatch. Added `mathmodel-skill/tests/test_manifest.py`.

## RED

Command:

```powershell
python -m unittest discover -s mathmodel-skill/tests -p 'test_manifest.py' -v
```

Exact output:

```text
test_manifest (unittest.loader._FailedTest.test_manifest) ... ERROR

======================================================================
ERROR: test_manifest (unittest.loader._FailedTest.test_manifest)
----------------------------------------------------------------------
ImportError: Failed to import test module: test_manifest
Traceback (most recent call last):
  File "C:\Users\32583\AppData\Local\Programs\Python\Python313\Lib\unittest\loader.py", line 396, in _find_test_path
    module = self._get_module_from_name(name)
  File "C:\Users\32583\AppData\Local\Programs\Python\Python313\Lib\unittest\loader.py", line 339, in _find_test_path
    __import__(name)
  File "E:\Projects\school\mathmodel\mathmodel-skill\tests\test_manifest.py", line 13, in <module>
    from mmcore.manifest import (
    ...<4 lines>...
    )
ModuleNotFoundError: No module named 'mmcore.manifest'

----------------------------------------------------------------------
Ran 1 test in 0.000s

FAILED (errors=1)
```

## GREEN

Command:

```powershell
python -m unittest discover -s mathmodel-skill/tests -p 'test_manifest.py' -v
```

Exact output:

```text
test_inspect_writes_audit_and_manifest_and_prints_json (test_manifest.ManifestTests.test_inspect_writes_audit_and_manifest_and_prints_json) ... ok
test_inventory_uses_relative_posix_paths_and_warns_for_missing_inputs (test_manifest.ManifestTests.test_inventory_uses_relative_posix_paths_and_warns_for_missing_inputs) ... ok
test_new_run_creates_distinct_append_only_run_directories (test_manifest.ManifestTests.test_new_run_creates_distinct_append_only_run_directories) ... ok
test_run_manifest_records_input_hash_and_stages (test_manifest.ManifestTests.test_run_manifest_records_input_hash_and_stages) ... ok
test_sha256_is_stable (test_manifest.ManifestTests.test_sha256_is_stable) ... ok

----------------------------------------------------------------------
Ran 5 tests in 0.057s

OK
{"manifest": "C:\\Users\\32583\\AppData\\Local\\Temp\\tmpcs4_6fdz\\.mathmodel\\runs\\1788081004814628500-4f8ac3312c0a\\manifest.json", "audit": "C:\\Users\\32583\\AppData\\Local\\Temp\\tmpcs4_6fdz\\artifacts\\data-audit.json", "status": "WARN"}
```

## Complete suite

Command:

```powershell
python -m unittest discover -s mathmodel-skill/tests -v
```

Exact output:

```text
test_load_config_accepts_minimal_valid_contract (test_config.ConfigTests.test_load_config_accepts_minimal_valid_contract) ... ok
test_main_help_returns_zero (test_config.ConfigTests.test_main_help_returns_zero) ... ok
test_rejects_appendix_ratio_above_one (test_config.ConfigTests.test_rejects_appendix_ratio_above_one) ... ok
test_rejects_path_escape (test_config.ConfigTests.test_rejects_path_escape) ... ok
test_inspect_writes_audit_and_manifest_and_prints_json (test_manifest.ManifestTests.test_inspect_writes_audit_and_manifest_and_prints_json) ... ok
test_inventory_uses_relative_posix_paths_and_warns_for_missing_inputs (test_manifest.ManifestTests.test_inventory_uses_relative_posix_paths_and_warns_for_missing_inputs) ... ok
test_new_run_creates_distinct_append_only_run_directories (test_manifest.ManifestTests.test_new_run_creates_distinct_append_only_run_directories) ... ok
test_run_manifest_records_input_hash_and_stages (test_manifest.ManifestTests.test_run_manifest_records_input_hash_and_stages) ... ok
test_sha256_is_stable (test_manifest.ManifestTests.test_sha256_is_stable) ... ok
test_adopt_does_not_replace_existing_configuration (test_scaffold.ScaffoldTests.test_adopt_does_not_replace_existing_configuration) ... ok
test_adopt_preserves_existing_paper_and_solver (test_scaffold.ScaffoldTests.test_adopt_preserves_existing_paper_and_solver) ... ok
test_adoption_report_categorizes_files_and_lists_framework_conflicts (test_scaffold.ScaffoldTests.test_adoption_report_categorizes_files_and_lists_framework_conflicts) ... ok
test_cli_dispatches_init_and_adopt (test_scaffold.ScaffoldTests.test_cli_dispatches_init_and_adopt) ... error: unsupported problem type: unknown
ok
test_cli_rejects_invalid_problem_type_cleanly (test_scaffold.ScaffoldTests.test_cli_rejects_invalid_problem_type_cleanly) ... ok
test_init_creates_contract_and_required_directories (test_scaffold.ScaffoldTests.test_init_creates_contract_and_required_directories) ... ok
test_init_never_overwrites_existing_file (test_scaffold.ScaffoldTests.test_init_never_overwrites_existing_file) ... ok
test_paper_template_has_executable_boundary_labels_and_clearpages (test_scaffold.ScaffoldTests.test_paper_template_has_executable_boundary_labels_and_clearpages) ... ok

----------------------------------------------------------------------
Ran 17 tests in 0.216s

OK
usage: mathmodel [-h] {init,adopt,inspect} ...

positional arguments:
  {init,adopt,inspect}

options:
  -h, --help            show this help message and exit
{"manifest": "C:\\Users\\32583\\AppData\\Local\\Temp\\tmpf8fl0uxl\\.mathmodel\\runs\\1788081009519979800-33dfe3f20d45\\manifest.json", "audit": "C:\\Users\\32583\\AppData\\Local\\Temp\\tmpf8fl0uxl\\artifacts\\data-audit.json", "status": "WARN"}
```

## Files changed

- `mathmodel-skill/scripts/mmcore/manifest.py`
- `mathmodel-skill/scripts/mathmodel.py`
- `mathmodel-skill/tests/test_manifest.py`
- `.superpowers/sdd/mathmodel-paper-factory/task-3-report.md`

## Commit status

No Git commit was created. The requested workspace root is not a Git repository, and the task explicitly disallows fabricating a commit.

## Concerns

- The complete-suite output includes the pre-existing expected `error: unsupported problem type: unknown` line from a test; the suite still passes.
- The test fixture intentionally includes a missing configured input, so its inspect status is `WARN`.

## Fix round 1 (S1, Q1, Q2, Q3)

### Root-cause investigation

S1 was caused by `new_run` constructing IDs from `time.time_ns()` before recording `created_at`, producing an opaque epoch integer unrelated in visible form to the UTC manifest timestamp. Q1/Q2 were coverage gaps: the tests did not exercise repeated stage evidence, complete provenance fields, or inspect JSON contents. Q3 was a real boundary bug: inventory sorted with `_relative()` before handling paths, so an out-of-root recognized symlink could raise `ValueError`.

### RED

Command:

```powershell
python -m unittest discover -s mathmodel-skill/tests -p 'test_manifest.py' -v
```

Exact output:

```text
test_inspect_writes_audit_and_manifest_and_prints_json (test_manifest.ManifestTests.test_inspect_writes_audit_and_manifest_and_prints_json) ... ok
test_inventory_uses_relative_posix_paths_and_warns_for_missing_inputs (test_manifest.ManifestTests.test_inventory_uses_relative_posix_paths_and_warns_for_missing_inputs) ... ok
test_manifest_records_complete_provenance_and_inventory_fields (test_manifest.ManifestTests.test_manifest_records_complete_provenance_and_inventory_fields) ... FAIL
test_new_run_creates_distinct_append_only_run_directories (test_manifest.ManifestTests.test_new_run_creates_distinct_append_only_run_directories) ... ok
test_out_of_root_recognized_symlink_is_warned_or_skipped (test_manifest.ManifestTests.test_out_of_root_recognized_symlink_is_warned_or_skipped) ... skipped "symlink creation unavailable: [WinError 1314] ..."
test_run_id_is_utc_timestamp_plus_corresponding_config_hash (test_manifest.ManifestTests.test_run_id_is_utc_timestamp_plus_corresponding_config_hash) ... FAIL
test_run_manifest_records_input_hash_and_stages (test_manifest.ManifestTests.test_run_manifest_records_input_hash_and_stages) ... ok
test_sha256_is_stable (test_manifest.ManifestTests.test_sha256_is_stable) ... ok

======================================================================
FAIL: test_manifest_records_complete_provenance_and_inventory_fields (test_manifest.ManifestTests.test_manifest_records_complete_provenance_and_inventory_fields)
----------------------------------------------------------------------
AssertionError: Items in the first set but not the second: 'paper/main.tex'

======================================================================
FAIL: test_run_id_is_utc_timestamp_plus_corresponding_config_hash (test_manifest.ManifestTests.test_run_id_is_utc_timestamp_plus_corresponding_config_hash)
----------------------------------------------------------------------
AssertionError: Regex didn't match: '^\\d{8}T\\d{6}Z-[0-9a-f]{12}$' not found in '1788081305941520800-f83858588f2e'

----------------------------------------------------------------------
Ran 8 tests in 0.086s

FAILED (failures=2, skipped=1)
```

### GREEN

Implemented a UTC `YYYYMMDDTHHMMSSZ` run-ID prefix, a 12-character SHA-256 short hash over the config and input hashes, collision suffix fallback, complete metadata assertions, repeated stage evidence assertions, first-manifest immutability assertions, inspect JSON assertions, and safe skip/warning handling for out-of-root recognized paths.

Command:

```powershell
python -m unittest discover -s mathmodel-skill/tests -p 'test_manifest.py' -v
```

Exact output:

```text
test_inspect_writes_audit_and_manifest_and_prints_json (test_manifest.ManifestTests.test_inspect_writes_audit_and_manifest_and_prints_json) ... ok
test_inventory_uses_relative_posix_paths_and_warns_for_missing_inputs (test_manifest.ManifestTests.test_inventory_uses_relative_posix_paths_and_warns_for_missing_inputs) ... ok
test_manifest_records_complete_provenance_and_inventory_fields (test_manifest.ManifestTests.test_manifest_records_complete_provenance_and_inventory_fields) ... ok
test_new_run_creates_distinct_append_only_run_directories (test_manifest.ManifestTests.test_new_run_creates_distinct_append_only_run_directories) ... ok
test_out_of_root_recognized_symlink_is_warned_or_skipped (test_manifest.ManifestTests.test_out_of_root_recognized_symlink_is_warned_or_skipped) ... skipped "symlink creation unavailable: [WinError 1314] ..."
test_run_id_is_utc_timestamp_plus_corresponding_config_hash (test_manifest.ManifestTests.test_run_id_is_utc_timestamp_plus_corresponding_config_hash) ... ok
test_run_manifest_records_input_hash_and_stages (test_manifest.ManifestTests.test_run_manifest_records_input_hash_and_stages) ... ok
test_sha256_is_stable (test_manifest.ManifestTests.test_sha256_is_stable) ... ok

----------------------------------------------------------------------
Ran 8 tests in 0.084s

OK (skipped=1)
```

### Complete suite

Command:

```powershell
python -m unittest discover -s mathmodel-skill/tests -v
```

Exact output:

```text
test_load_config_accepts_minimal_valid_contract (test_config.ConfigTests.test_load_config_accepts_minimal_valid_contract) ... ok
test_main_help_returns_zero (test_config.ConfigTests.test_main_help_returns_zero) ... ok
test_rejects_appendix_ratio_above_one (test_config.ConfigTests.test_rejects_appendix_ratio_above_one) ... ok
test_rejects_path_escape (test_config.ConfigTests.test_rejects_path_escape) ... ok
test_inspect_writes_audit_and_manifest_and_prints_json (test_manifest.ManifestTests.test_inspect_writes_audit_and_manifest_and_prints_json) ... ok
test_inventory_uses_relative_posix_paths_and_warns_for_missing_inputs (test_manifest.ManifestTests.test_inventory_uses_relative_posix_paths_and_warns_for_missing_inputs) ... ok
test_manifest_records_complete_provenance_and_inventory_fields (test_manifest.ManifestTests.test_manifest_records_complete_provenance_and_inventory_fields) ... ok
test_new_run_creates_distinct_append_only_run_directories (test_manifest.ManifestTests.test_new_run_creates_distinct_append_only_run_directories) ... ok
test_out_of_root_recognized_symlink_is_warned_or_skipped (test_manifest.ManifestTests.test_out_of_root_recognized_symlink_is_warned_or_skipped) ... skipped "symlink creation unavailable: [WinError 1314] ..."
test_run_id_is_utc_timestamp_plus_corresponding_config_hash (test_manifest.ManifestTests.test_run_id_is_utc_timestamp_plus_corresponding_config_hash) ... ok
test_run_manifest_records_input_hash_and_stages (test_manifest.ManifestTests.test_run_manifest_records_input_hash_and_stages) ... ok
test_sha256_is_stable (test_manifest.ManifestTests.test_sha256_is_stable) ... ok
test_adopt_does_not_replace_existing_configuration (test_scaffold.ScaffoldTests.test_adopt_does_not_replace_existing_configuration) ... ok
test_adopt_preserves_existing_paper_and_solver (test_scaffold.ScaffoldTests.test_adopt_preserves_existing_paper_and_solver) ... ok
test_adoption_report_categorizes_files_and_lists_framework_conflicts (test_scaffold.ScaffoldTests.test_adoption_report_categorizes_files_and_lists_framework_conflicts) ... ok
test_cli_dispatches_init_and_adopt (test_scaffold.ScaffoldTests.test_cli_dispatches_init_and_adopt) ... error: unsupported problem type: unknown
ok
test_cli_rejects_invalid_problem_type_cleanly (test_scaffold.ScaffoldTests.test_cli_rejects_invalid_problem_type_cleanly) ... ok
test_init_creates_contract_and_required_directories (test_scaffold.ScaffoldTests.test_init_creates_contract_and_required_directories) ... ok
test_init_never_overwrites_existing_file (test_scaffold.ScaffoldTests.test_init_never_overwrites_existing_file) ... ok
test_paper_template_has_executable_boundary_labels_and_clearpages (test_scaffold.ScaffoldTests.test_paper_template_has_executable_boundary_labels_and_clearpages) ... ok

----------------------------------------------------------------------
Ran 20 tests in 0.264s

OK (skipped=1)
```

### Fix-round status

No Git commit was created; the workspace has no `.git` directory. The only remaining test concern is environmental: Windows denies non-elevated symlink creation (`WinError 1314`), so the symlink regression test skips deterministically on this host; production inventory now warns/skips such out-of-root entries rather than raising.

## Fix round 2 (Q3 deterministic fallback)

### RED

Added `test_out_of_root_recognized_candidate_is_warned_and_skipped_without_symlink`, which imports the requested containment seam before that seam existed.

Command:

```powershell
python -m unittest discover -s mathmodel-skill/tests -p 'test_manifest.py' -v
```

Exact output:

```text
test_manifest (unittest.loader._FailedTest.test_manifest) ... ERROR

======================================================================
ERROR: test_manifest (unittest.loader._FailedTest.test_manifest)
----------------------------------------------------------------------
ImportError: Failed to import test module: test_manifest
Traceback (most recent call last):
  File "C:\Users\32583\AppData\Local\Programs\Python\Python313\Lib\unittest\loader.py", line 396, in _find_test_path
    module = self._get_module_from_name(name)
  File "C:\Users\32583\AppData\Local\Programs\Python\Python313\Lib\unittest\loader.py", line 339, in _get_module_from_name
    __import__(name)
  File "E:\Projects\school\mathmodel\mathmodel-skill\tests\test_manifest.py", line 17, in <module>
    from mmcore.manifest import (
    ...<5 lines>...
    )
ImportError: cannot import name 'recognized_path_decision' from 'mmcore.manifest' (E:\Projects\school\mathmodel\mathmodel-skill\scripts\mmcore\manifest.py)

----------------------------------------------------------------------
Ran 1 test in 0.000s

FAILED (errors=1)
```

### GREEN

Added pure `recognized_path_decision(root, candidate)` containment handling and routed `inventory_project` through it. Out-of-root resolved candidates now return a warning, are omitted from `files`, and cannot raise `ValueError`. The deterministic test injects an out-of-root `.py` candidate without creating a symlink and verifies all three behaviors.

### Focused verification

Command:

```powershell
python -m unittest discover -s mathmodel-skill/tests -p 'test_manifest.py' -v
```

Exact output:

```text
test_inspect_writes_audit_and_manifest_and_prints_json (test_manifest.ManifestTests.test_inspect_writes_audit_and_manifest_and_prints_json) ... ok
test_inventory_uses_relative_posix_paths_and_warns_for_missing_inputs (test_manifest.ManifestTests.test_inventory_uses_relative_posix_paths_and_warns_for_missing_inputs) ... ok
test_manifest_records_complete_provenance_and_inventory_fields (test_manifest.ManifestTests.test_manifest_records_complete_provenance_and_inventory_fields) ... ok
test_new_run_creates_distinct_append_only_run_directories (test_manifest.ManifestTests.test_new_run_creates_distinct_append_only_run_directories) ... ok
test_out_of_root_recognized_candidate_is_warned_and_skipped_without_symlink (test_manifest.ManifestTests.test_out_of_root_recognized_candidate_is_warned_and_skipped_without_symlink) ... ok
test_out_of_root_recognized_symlink_is_warned_or_skipped (test_manifest.ManifestTests.test_out_of_root_recognized_symlink_is_warned_or_skipped) ... skipped "symlink creation unavailable: [WinError 1314] ..."
test_run_id_is_utc_timestamp_plus_corresponding_config_hash (test_manifest.ManifestTests.test_run_id_is_utc_timestamp_plus_corresponding_config_hash) ... ok
test_run_manifest_records_input_hash_and_stages (test_manifest.ManifestTests.test_run_manifest_records_input_hash_and_stages) ... ok
test_sha256_is_stable (test_manifest.ManifestTests.test_sha256_is_stable) ... ok

----------------------------------------------------------------------
Ran 9 tests in 0.078s

OK (skipped=1)
```

### Complete-suite verification

Command:

```powershell
python -m unittest discover -s mathmodel-skill/tests -v
```

Exact output:

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
test_out_of_root_recognized_symlink_is_warned_or_skipped (test_manifest.ManifestTests.test_out_of_root_recognized_symlink_is_warned_or_skipped) ... skipped "symlink creation unavailable: [WinError 1314] ..."
test_run_id_is_utc_timestamp_plus_corresponding_config_hash (test_manifest.ManifestTests.test_run_id_is_utc_timestamp_plus_corresponding_config_hash) ... ok
test_run_manifest_records_input_hash_and_stages (test_manifest.ManifestTests.test_run_manifest_records_input_hash_and_stages) ... ok
test_sha256_is_stable (test_manifest.ManifestTests.test_sha256_is_stable) ... ok
test_adopt_does_not_replace_existing_configuration (test_scaffold.ScaffoldTests.test_adopt_does_not_replace_existing_configuration) ... ok
test_adopt_preserves_existing_paper_and_solver (test_scaffold.ScaffoldTests.test_adopt_preserves_existing_paper_and_solver) ... ok
test_adoption_report_categorizes_files_and_lists_framework_conflicts (test_scaffold.ScaffoldTests.test_adoption_report_categorizes_files_and_lists_framework_conflicts) ... ok
test_cli_dispatches_init_and_adopt (test_scaffold.ScaffoldTests.test_cli_dispatches_init_and_adopt) ... error: unsupported problem type: unknown
ok
test_cli_rejects_invalid_problem_type_cleanly (test_scaffold.ScaffoldTests.test_cli_rejects_invalid_problem_type_cleanly) ... ok
test_init_creates_contract_and_required_directories (test_scaffold.ScaffoldTests.test_init_creates_contract_and_required_directories) ... ok
test_init_never_overwrites_existing_file (test_scaffold.ScaffoldTests.test_init_never_overwrites_existing_file) ... ok
test_paper_template_has_executable_boundary_labels_and_clearpages (test_scaffold.ScaffoldTests.test_paper_template_has_executable_boundary_labels_and_clearpages) ... ok

----------------------------------------------------------------------
Ran 21 tests in 0.232s

OK (skipped=1)
```

### Fix-round 2 status

Q3 deterministic repository coverage is addressed. No Git commit was created because the workspace has no `.git` directory. The symlink-specific test remains permission-skipped on this Windows host, while the non-symlink fallback regression executes and passes.
