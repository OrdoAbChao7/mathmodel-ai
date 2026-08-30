# Task 6 review-fix report

## Review findings fixed

- Existing path-like command arguments are resolved before execution. Any path that resolves outside the project, including an option value such as `--config=link.py`, is rejected. Absolute paths remain allowed only for `command[0]`, the configured executable/interpreter; this is documented in `run_solver`.
- Every solver and analysis execution now carries a complete run-directory inventory. Entries classify framework manifests/logs separately from generated outputs, and `generated_files` records files created or changed by that stage.
- Each execution record includes the manifest-level `input_hashes`, source-file `config_sha256`, and complete `output_inventory`. The machine-readable build report also exposes the run input/config hashes.
- Solver or analysis failure now short-circuits compilation, PDF metrics, artifact validation, and quality scoring. Those manifest stages are recorded as `SKIPPED`; the build report remains available with the retained diagnostics.
- A build without `commands.solver` is explicitly treated as the legacy existing-artifacts path: solver and analysis hooks are skipped, while the established LaTeX build behavior remains available.

## TDD evidence

RED command:

```text
python -m unittest mathmodel-skill.tests.test_runner_analysis -v
```

Observed failures before the fix included missing `_resolve_existing_path`, absent solver `output_inventory` and execution hashes, and `compile_latex` being called after solver failure.

Focused GREEN command:

```text
python -m unittest mathmodel-skill.tests.test_runner_analysis -v
```

Result: `Ran 13 tests ... OK`.

Complete verification command:

```text
python -m unittest discover -s mathmodel-skill/tests -v
```

Result: `Ran 79 tests ... OK (skipped=1)`.

The sole skip is the existing Windows symlink-permission test (`WinError 1314`). The new symlink containment test has a deterministic resolver-mock fallback and passes on hosts without symlink permission.
