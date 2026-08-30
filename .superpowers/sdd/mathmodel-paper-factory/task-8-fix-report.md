# Task 8 fix report

## Scope

This repair is confined to `mathmodel-skill/tests/test_end_to_end.py` and the three non-production Task 8 fixtures. No files under `traning1/` or production CLI modules were changed.

## Review findings closed

- Each fixture now declares `paper.compiler_mode` as `controlled_fake`. The fixture runner returns that mode and fails closed unless the configured engine resolves to that fixture's own `fake-compiler.cmd`.
- The runner reads `paper/main.tex` before controlled compilation and emits source checks for all six required boundary labels, plus one strict body -> references -> appendix ordering check. Missing labels, invalid source without labels, and misordered labels skip compilation and return `FAIL`.
- The focused tests independently assert the hand-derived fixture semantics:
  - optimization: `x=2`, `y=2`, objective `18`, and `13` feasible points;
  - forecasting: slope `2.0`, predictions `[11.0, 13.0]`, holdout MAE `0.0`, persistence improvement `3.0`, and training ending before the holdout;
  - evaluation: normalized values, weights summing to `1.0`, scores `A=0.8`, `B=0.7`, `C=0.0`, ranking `A,B,C`, and unchanged documented sensitivity ranking.
- Fixture-local analysis now rejects non-chronological/leaking forecast inputs, evaluation weights that are negative, incomplete, or do not sum to one, and constant evaluation indicator ranges.
- The checked-in optimization result was corrected from `11` to `13` feasible points and is covered by a clean-state baseline assertion.

## Controlled compiler boundary

The fixture compiler remains intentionally deterministic and reports `compiler_mode: controlled_fake`. It proves that the configured fixture-local adapter produces the expected A4 PDF/AUX page evidence; it is not represented as a real XeLaTeX syntax check. The source-level label/order gate prevents the fake compiler from certifying a source that lacks the executable boundary declarations.

## Verification

Focused:

```text
python -m unittest mathmodel-skill.tests.test_end_to_end -v
Ran 12 tests in 8.063s
OK
```

Complete:

```text
python -m unittest discover -s mathmodel-skill/tests -v
Ran 103 tests in 12.132s
OK (skipped=1)
```

The single skip is the existing Windows symlink-permission case (`WinError 1314`). No Git commit was created or claimed.
