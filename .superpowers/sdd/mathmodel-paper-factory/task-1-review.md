# Task 1 Review

## Verdicts

- Spec compliance: **FAIL — one minor interface violation**.
- Task quality: **PASS — narrowly scoped, readable, dependency-free implementation with credible RED→GREEN evidence**.

## Review basis

Reviewed the task brief, implementer report, review package, and all four listed changed files directly. No Git state was used. Targeted verification was run on 2026-08-30:

```text
python -m unittest discover -s mathmodel-skill/tests -p 'test_config.py' -v
Ran 3 tests in 0.011s
OK

python -m unittest discover -s mathmodel-skill/tests -v
Ran 3 tests in 0.011s
OK
```

The three tests are the exact required behaviors and use `unittest`. The reported RED output is a genuine import failure (`ModuleNotFoundError: No module named 'mmcore'`) occurring before implementation was present, and the reported GREEN output matches the current tests. The historical RED run cannot be independently replayed without reverting the implementation, so this conclusion is evidence-based rather than a fresh RED execution.

## Spec compliance

The configuration implementation covers the requested object-root check, required top-level keys, schema version, allowed problem types, nested command/paper/input validation, two-element integer page ranges, ratio bounds, and project-root containment through `Path.resolve()`. It reads UTF-8 JSON and does not write during loading. The CLI remains limited to help and an unimplemented-command error, as required.

### Finding S1 — `main(argv)` does not always return an exit code

- Severity: **P2 (minor)**
- File/function: `mathmodel-skill/scripts/mathmodel.py`, `main`, parser construction around lines 10–13
- Evidence: `argparse.ArgumentParser` installs its built-in `--help` action. A direct call to `main(["--help"])` raises `SystemExit(0)` before reaching the function's `return 0`; targeted execution printed help but did not print the sentinel after the call. This conflicts with the declared `main(argv: list[str] | None = None) -> int` contract that dispatches and returns a process exit code.
- Repair: disable the automatic help action (`add_help=False`), add an explicit `--help`/`-h` argument, print `parser.format_help()`, and return `0`; alternatively catch only the help action's `SystemExit` inside `main` and convert it to `0`. Add a focused test asserting `main(["--help"]) == 0`.

## Task quality

The code is small and coherent. `ConfigError` is consistently used for malformed files and invalid values; booleans are correctly excluded from integer/range validation; path escape checks handle absolute paths and resolved symlink/`..` traversal; and no third-party package or later-task behavior was introduced. The complete discovered suite currently contains only the three Task 1 tests, exactly as noted in the implementer report, so broader regression confidence is necessarily limited by the repository state rather than by scope creep.

No additional task-quality findings.

