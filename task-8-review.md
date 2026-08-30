# Task 8 independent review

## Scope and verdicts

Reviewed the Task 8 package, brief, report, plan/spec requirements, all three fixture directories, `test_end_to_end.py`, the shared compile/contract paths used by the runner, and the generated behavior in temporary fixture copies. No source or test files were edited.

Spec verdict: **PARTIAL — not ready to certify without follow-up**.

The requested fixture structure, public `run_fixture` interface, execution order, registry validation, fail-closed link checks, deterministic fixture outputs, and the requested focused/complete test commands are present. However, two acceptance properties are not reliably enforced by the Task 8 tests/artifacts: executable LaTeX boundary labels are not actually coupled to the compiled source when the fake compiler is used, and the checked-in optimization result is stale relative to its raw input and algorithm.

Task-quality verdict: **NEEDS CHANGES**.

The implementation is small, readable, isolated from `traning1/`, and the normal temporary-copy flow passes. The review confidence is reduced because the end-to-end tests mostly assert that generated structure exists and that the runner returns PASS; they do not independently assert the exact optimization/forecasting/evaluation semantics. The fake compiler is clearly described in the report, but the test contract does not prove its use is controlled or that the LaTeX source is executable.

## Verification evidence

- Focused: `python -m unittest mathmodel-skill.tests.test_end_to_end -v` — **6/6 passed**.
- Complete: `python -m unittest discover -s mathmodel-skill/tests -v` — **97 passed, 1 skipped, 0 failed**. The only skip is the existing Windows symlink-permission case (`WinError 1314`).
- `xelatex --version` was found but exited 1 because MiKTeX reports an unfinished first-time setup/update check. The fixtures therefore exercised their local `.cmd` fake compiler.
- Independent arithmetic produced optimization optimum `(x, y) = (2, 2)`, objective `18`, and **13** feasible points; forecasting slope `2.0` with predictions `11.0, 13.0`; evaluation scores `A=0.8`, `B=0.7`, `C=0.0`.
- A temporary forecasting copy whose `paper/main.tex` was replaced with invalid text and no boundary labels still returned `run_fixture` status `PASS`, compile `SUCCESS`, and metrics with all six labels. This demonstrates that the fake compiler output is independent of the LaTeX source.

## What is good

- The three fixtures are compact and non-production, with the required seven registry files, raw input, analysis adapter, paper source, and four figure roles.
- `run_fixture` follows the stated inspect → analyze → validate → compile → audit sequence in `mathmodel-skill/tests/test_end_to_end.py:86-124`.
- Registry ID/link failures and generated result/figure hash tampering are tested fail-closed in `test_end_to_end.py:226-256`.
- The forecasting fixture uses a final chronological holdout, and the evaluation fixture records direction-aware normalization, weights, scores, ranking, and a sensitivity ranking.
- The report accurately records that CLI audit remains `NEEDS_MANUAL_REVIEW` without a manual scorecard and that the fixture runner supplies a fixed local scorecard for the combined result.
- No `traning1/` changes were made, and the workspace is not a Git repository, so there is no unreviewed production diff to assess.

## Findings

### Critical

None found. I found no demonstrated security bypass, data-loss path, or release-blocking failure in the normal tested fixture flow.

### Important

#### I-1 — The fake compiler allows invalid LaTeX and missing executable labels to pass

**Location:** `mathmodel-skill/tests/fixtures/*/analysis/run.py:22-54` and `mathmodel-skill/tests/test_end_to_end.py:103-107`.

Each fixture's fake compiler creates a fixed three-page PDF and fixed `.aux` labels without reading or parsing `paper/main.tex`. `run_fixture` then trusts those generated labels through `measure_pdf`. In a temporary negative test, replacing the entire forecasting `main.tex` with `this is not valid latex` and no boundary labels still produced `PASS`, `compile=SUCCESS`, and the expected six labels.

**Why:** The brief explicitly requires minimal LaTeX with executable boundary labels. A controlled mock compiler is allowed when the external compiler is unavailable, but the current test can certify a source that is not executable and has no labels. This makes the page/label evidence a property of the mock, not of the fixture paper.

**Suggestion:** Add a source-level assertion that each fixture `main.tex` contains all six required `\\label{...}` commands in valid ordering, and mark the report/result as mock-compiled (for example, an explicit `compiler_mode: controlled_fake` field). Add a negative test proving that removing a boundary label or using invalid source is reported as a mock-mode limitation or fails the fixture contract. If actual LaTeX cannot be run, do not represent the resulting PDF as proof of source compilation.

#### I-2 — End-to-end tests do not independently verify the three required model semantics

**Location:** `mathmodel-skill/tests/test_end_to_end.py:171-186` and fixture adapters, especially `optimization/analysis/run.py:70-94`.

The main success test only checks the overall PASS, PDF/report existence, figure roles, and presence of one result key. It does not assert the documented expected values (`x=2`, `y=2`, objective `18`; holdout MAE `0.0` and persistence improvement `3.0`; evaluation scores/ranking and sensitivity result), nor does it assert that the forecast training data precedes the holdout or that the evaluation weights sum to one. A substantially wrong fixture algorithm could still satisfy these tests if it emitted structurally valid registries and a PASS status.

**Why:** Task 8 is specifically a deterministic problem-type fixture task, not only a registry plumbing test. The acceptance language calls out hand-checkable optimization, time-ordered linear holdout, and weighted multi-criteria evaluation. Those properties need executable assertions independent of the adapter's own expected output.

**Suggestion:** Assert the exact hand-checkable values for all three fixtures and inspect the model/validation metadata. Add a negative forecasting case for train/holdout ordering or leakage, and a negative evaluation case for invalid weight totals or constant-range normalization. Keep these checks in temporary copies so the canonical fixtures remain untouched.

### Minor

#### M-1 — The checked-in optimization result is stale

**Location:** `mathmodel-skill/tests/fixtures/optimization/analysis/results.json` versus `mathmodel-skill/tests/fixtures/optimization/data/raw/input.json` and `analysis/run.py:73`.

The checked-in result contains `"feasible_points": 11`, while independently enumerating the stated constraints over the adapter's `range(5)` domain gives 13 feasible points. Running the adapter regenerates 13, so the normal `run_fixture` flow passes, but the fixture is internally inconsistent before that run. The report does not call out this generated-artifact mismatch.

**Why:** Reviewers and tools inspecting a fixture without first running analysis can read incorrect evidence. This also weakens the claim that the fixture package itself is a deterministic, hand-checkable baseline.

**Suggestion:** Regenerate and verify committed generated artifacts, or intentionally omit generated outputs from the fixture package and make the test assert that analysis creates them. Add a clean-state consistency check that recomputes the expected optimization result before running the full orchestration.

#### M-2 — Fake compiler control is documented but not asserted

**Location:** `mathmodel-skill/tests/fixtures/*/mathmodel.json` and `task-8-report.md:51-59`.

The report explains the fake compiler, and the configs point to fixture-local `.\\fake-compiler.cmd` files. However, `run_fixture` accepts any configured engine and only records its path in the compile result; there is no Task 8 assertion that the selected engine is fixture-local, that it is the expected fake compiler, or that mock mode is visible in the returned report.

**Suggestion:** Assert the engine resolves inside the fixture and is the expected controlled adapter for these tests, or expose an explicit compiler mode and test it. This would make the limitation auditable rather than relying on prose.

## Final recommendation

The normal suites and fixture flow are green, and the implementation is a useful foundation. Before marking Task 8 fully certified, close I-1 and I-2, then resolve M-1 so the checked-in package is self-consistent. After those changes, rerun both commands and update the Task 8 report with fresh output and the explicit mock-compiler limitation.
