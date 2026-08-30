# Task 6 round-2 fix report

## Fixes delivered

- Relative path-like executables in `command[0]` are now containment-checked before launch. Traversal and symlink-resolved targets outside the project return `RUNNER-PATH-001`.
- Bare executable names (for example `python`) remain PATH-resolved. Absolute `command[0]` remains permitted for a configured interpreter such as `sys.executable`; this exception is documented in `run_solver`.
- The conservative argument rule is documented: all positional arguments and every `--key=value` value are treated as potential project paths and fail closed when path containment is violated.
- Manifest stage records now include `output_inventory`. Solver and analysis inventories retain per-file path, size, SHA-256, kind, and provenance, including generated files distinct from framework logs/manifests.

## TDD evidence

RED command:

```text
python -m unittest mathmodel-skill.tests.test_runner_analysis mathmodel-skill.tests.test_manifest -v
```

Observed expected failures before implementation:

- A relative `command[0]` traversal produced no `RUNNER-PATH-001`.
- Solver/analysis manifest stages had no `output_inventory` field.

Focused GREEN command:

```text
python -m unittest mathmodel-skill.tests.test_runner_analysis mathmodel-skill.tests.test_manifest -v
```

Result: `Ran 23 tests ... OK (skipped=1)`.

Complete verification command:

```text
python -m unittest discover -s mathmodel-skill/tests -v
```

Result: `Ran 80 tests ... OK (skipped=1)`.

The only skip is the existing Windows symlink-permission test (`WinError 1314`).
