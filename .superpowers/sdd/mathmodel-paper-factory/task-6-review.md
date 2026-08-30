# Task 6 independent review

## Summary

The implementation is clear and mostly well-factored: execution is centralized in a shell-free subprocess runner, logs are retained for success and failure, solver failure prevents analysis execution, output hashes are deterministic, and build runs receive distinct run directories. The focused and complete suites both pass.

The task is not fully acceptance-compliant. The main security issue is that command arguments are checked only lexically, so a project-local symlink can resolve to and execute a file outside the project. The run evidence also does not consistently attach output inventories to every execution stage, and `build` continues into LaTeX compilation after solver/analysis failure despite the design's dependent-stage stop rule. These are not exposed by the current tests.

## Verification evidence

- Focused: `python -m unittest mathmodel-skill.tests.test_runner_analysis -v`
  - `Ran 9 tests ... OK`
- Complete: `python -m unittest discover -s mathmodel-skill/tests -v`
  - `Ran 75 tests ... OK (skipped=1)`
  - The sole skip is the known Windows symlink-permission test, skipped because symlink creation returned `WinError 1314`.
- The package's root-level `task-6-report.md` was read; `.superpowers/sdd/mathmodel-paper-factory/task-6-report.md` does not exist.
- This workspace is not a Git repository, so the review is based on current files rather than a VCS diff.

## Spec-compliance verdict: NEEDS FIX

The implementation satisfies the tested argument-array execution, project cwd, timeout, missing/nonzero command diagnostics, solver-before-analysis ordering, failure short-circuit for analysis, append-only run-directory behavior, output hashing, and JSON build report requirements. It does not fully satisfy the stated path-containment and run-evidence requirements described in the review package and design/spec.

### Critical findings

🔴 **Security: symlink-resolved command paths can escape the project**

`mathmodel-skill/scripts/mmcore/runner.py:47-52` rejects absolute paths and literal `..` components, but it does not resolve an existing argument before accepting it. A command such as `sys.executable project-local-link/script.py`, where `script.py` is a symlink to an external file, passes validation and is then executed by `subprocess.run` at lines 137-145. This violates the requirement that command paths resolve inside the project and makes the path-escape protection bypassable on systems where symlinks are available.

**Suggestion:** Resolve path-like command arguments before execution and reject any existing path whose resolved target is outside `project`. Apply the same check to option values such as `--config=...`; retain a documented exception only for the executable itself if absolute interpreters are intentionally supported. Add a regression test that creates a local symlink to an outside script and verifies the command is rejected without execution.

### Important findings

🟡 **Run evidence: output inventory is not recorded for every execution stage**

`runner.py:163-179` returns no `output_inventory`, and `mathmodel.py:124-142` only adds inventory paths when the analysis result contains one. Consequently, solver-generated files are not inventoried as solver outputs, and a build with an empty analysis command has no output inventory at all. The acceptance requires run records to contain output inventories; the current implementation only inventories files when `run_analysis` is called, and that inventory also combines the analysis logs with all other files in the run directory.

**Suggestion:** Collect and attach an inventory after each stage that can produce files, including solver-only builds. Store the inventory (or its complete file records) in the corresponding manifest execution/stage record, not only as derived output paths. Distinguish framework logs/manifest from user outputs if the contract requires an output-only inventory.

🟡 **Dependent-stage failure is not short-circuited beyond analysis**

In `mathmodel.py:283-317`, a failed or timed-out solver skips analysis, but the code still calls `_source_gates`, `compile_latex`, PDF measurement, artifact validation, and quality reporting. The design specification states that when a stage fails, subsequent dependent stages stop while diagnostics and existing artifacts are retained. Compilation depends on successful analysis/artifacts in this workflow, so continuing it can produce a report from stale or incomplete outputs and obscures the actual failure boundary.

**Suggestion:** Mark dependent stages `SKIPPED` after solver or analysis failure, preserve the failure diagnostics, and write the machine-readable build report without attempting compilation. If compilation is intentionally independent, document that dependency decision in the manifest and add a test proving the intended behavior.

🟡 **Input hashes are not attached to solver/analysis execution records**

`manifest.py:154-163` stores `input_hashes` at the manifest root, while `mathmodel.py:113-121` records execution details without copying input/config hashes into each solver or analysis execution record. The root manifest is useful, but the review-package wording requires run records to identify input/config hashes and the build report exposes stage records without input hashes.

**Suggestion:** Either make the manifest contract explicitly define root-level hashes as the run-level evidence, or include `input_hashes` and `config_sha256` in each execution record/build-report stage. Add a test asserting the chosen contract.

## Task-quality verdict: NEEDS IMPROVEMENT

The code quality is good for the covered scope: the runner has a small API, structured errors include rule IDs and evidence, stdout/stderr are persisted even for pre-execution failures, `shell=False` is used, and output ordering is deterministic. The tests are readable and cover the requested ordinary success/failure matrix.

The quality bar is reduced by missing adversarial and integration coverage for the exact acceptance boundaries. In particular, there is no test for symlink command escape, no test that solver outputs are inventoried, no test for analysis failure's effect on compilation, and no test that malformed solver configuration is handled through the CLI. The current test suite therefore demonstrates the implemented paths but does not establish the full reproducibility/security contract.

### Minor findings

💭 **Test coverage: add boundary tests for path-like arguments and output inventory semantics**

The existing path test covers `../outside.py`, but not normalized paths, local symlinks, `--option=value` paths, or a generated output symlink. Those cases are where containment implementations commonly diverge from the contract. Adding them would make the security behavior explicit and prevent regressions.

💭 **Manifest mutability is acceptable but should be documented as append-only history semantics**

`update_stage` rewrites the current manifest several times during one run. The tests correctly verify that a completed prior run remains unchanged, which is the useful append-only property here. A short contract comment distinguishing immutable historical run directories from mutable in-progress manifests would avoid confusion for future maintainers.

## Recommended disposition

Do not mark Task 6 fully complete yet. Fix the symlink-resolved command containment issue first, then decide and encode the stage-inventory and dependent-compilation contract. Add the missing regression tests and rerun both suites; the existing implementation structure should make those changes localized.
