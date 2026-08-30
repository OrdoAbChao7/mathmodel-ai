# Task 8 report — deterministic end-to-end fixtures

## Scope delivered

- Added deterministic optimization, forecasting, and evaluation fixtures under `mathmodel-skill/tests/fixtures/`.
- Added `tests/test_end_to_end.py` with the required public `run_fixture(path: Path) -> dict` interface.
- Each fixture includes `mathmodel.json`, a raw input, deterministic `analysis/run.py`, seven JSON registries, minimal LaTeX with body/reference/appendix boundary labels, and four registered SVG sources covering data, method, result, and validation roles.
- No `traning1/` files were changed.

## End-to-end contract

`run_fixture` executes the required order:

1. CLI `inspect`;
2. the configured analysis adapter;
3. registry/cross-reference validation plus generated-output hash validation;
4. two-pass controlled compilation and A4 PDF page measurement;
5. CLI `audit` and quality-report creation.

The fixtures are deliberately small and hand-checkable:

- Optimization exhaustively enumerates a two-variable integer allocation and records `x=2`, `y=2`, objective `18`.
- Forecasting trains on times 1--4 and evaluates times 5--6, producing holdout MAE `0.0` versus persistence MAE `3.0`.
- Evaluation applies direction-aware min-max normalization and weights `(0.3, 0.4, 0.3)`, producing ranking `A, B, C`, unchanged by the documented cost-weight perturbation.

## TDD and test evidence

Initial RED command:

```text
python -m unittest mathmodel-skill.tests.test_end_to_end -v
Ran 6 tests; 8 errors because optimization/forecasting/evaluation fixture directories did not yet exist.
```

Focused GREEN verification:

```text
python -m unittest mathmodel-skill.tests.test_end_to_end -v
Ran 6 tests in 4.762s
OK
```

The focused tests prove all three fixture flows return `PASS` with distinct result hashes; repeat runs preserve result bytes, normalized registry JSON, PDF SHA-256, and figure SHA-256 values; unsupported claims and missing registry links block audit; and a deliberately tampered generated result fails closed before compilation.

Complete fresh verification:

```text
python -m unittest discover -s mathmodel-skill/tests -v
Ran 97 tests in 8.756s
OK (skipped=1)
```

The sole skip is the pre-existing Windows symlink-permission test (`WinError 1314`), not a Task 8 skip.

## Compiler and audit limitations

`xelatex --version` was unavailable for fixture compilation because MiKTeX reports that its first-time setup/updates have not been completed and exits with code 1. `pdfinfo` is available.

The existing compiler contract is therefore exercised through each fixture's controlled Windows `.cmd` fake compiler, as already covered by the LaTeX integration tests. It deterministically emits a valid three-page A4 PDF, a matching AUX file with all six boundary labels, and a clean compiler log; `pdfinfo` and the normal page-metrics code validate those files.

The current CLI `audit` intentionally reports `NEEDS_MANUAL_REVIEW` when no complete manual scorecard is supplied. `run_fixture` records that audit output and evaluates the fixture's fixed, fully specified local manual scorecard to determine its combined `PASS` status. This preserves the CLI's manual-review release gate rather than bypassing it.

## Repository note

The shared workspace is not a Git repository, so no commit was created or claimed.
