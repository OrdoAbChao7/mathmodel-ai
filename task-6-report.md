# Task 6 report — solver execution and reproducible analysis

## Scope delivered

- Added safe argument-array execution for configured solver and analysis stages.
- Added project-scoped working directories, a 300-second default timeout, captured logs, structured failures, reproducibility metadata, and code/config hashes.
- Added deterministic, hash-addressed inventories of files contained in each run directory.
- Updated `build --json` to create an append-only run manifest, execute solver before analysis, skip analysis after solver failure, retain diagnostics, and write `build/build-report.json`.
- Did not add or modify figure registry/asset behavior from Task 7 or later.

## TDD evidence

RED command:

```text
python -m unittest mathmodel-skill.tests.test_runner_analysis -v
```

Observed expected failure before implementation:

```text
ModuleNotFoundError: No module named 'mmcore.analysis'
```

Focused GREEN command:

```text
python -m unittest mathmodel-skill.tests.test_runner_analysis -v
```

Result: `Ran 9 tests ... OK`.

Complete verification command:

```text
python -m unittest discover -s mathmodel-skill/tests -v
```

Result: `Ran 75 tests ... OK (skipped=1)`.

The sole skip is the pre-existing Windows symlink-permission test:
`test_out_of_root_recognized_symlink_is_warned_or_skipped` (`WinError 1314`).

## Files changed

- `mathmodel-skill/scripts/mmcore/runner.py`
- `mathmodel-skill/scripts/mmcore/analysis.py`
- `mathmodel-skill/scripts/mathmodel.py`
- `mathmodel-skill/tests/test_runner_analysis.py`
- `task-6-report.md`
