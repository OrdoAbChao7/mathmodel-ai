# Task 6 fix re-review

## Summary

The fix resolves the three main findings from the prior review: existing path-like command arguments are symlink-resolved, solver and analysis execution results carry run-directory inventories with hashes and provenance, and solver/analysis failures stop dependent build stages while retaining diagnostics. Malformed `commands.analyze` configuration is also reported by the CLI as a structured configuration failure.

The focused and complete test suites pass. The implementation is not yet fully acceptance-compliant because command validation still skips command element 0 wholesale, allowing a relative executable path outside the project to bypass containment, and manifest stage records retain only output paths rather than the detailed per-file inventory required by the review scope. The execution-level evidence is substantially improved, but those gaps remain material.

## Verification evidence

- Focused: `python -m unittest mathmodel-skill.tests.test_runner_analysis -v`
  - `Ran 13 tests ... OK`
- Complete: `python -m unittest discover -s mathmodel-skill/tests -v`
  - `Ran 79 tests ... OK (skipped=1)`
  - The sole skip is the existing Windows symlink-permission test, which received `WinError 1314`. The new command symlink test uses the deterministic resolver mock fallback and passes.
- Direct source/spec inspection covered the requested package files, the Task 6 implementation and tests, the design specification, the implementation plan, and `mathmodel-skill/SKILL.md`.
- No source or test files were edited.

## Spec-compliance verdict: NEEDS FIX

### Critical findings

🔴 **Security: relative executable paths can bypass project containment**

`mathmodel-skill/scripts/mmcore/runner.py:62-70` validates only `command[1:]`. As a result, a command whose executable is itself a relative path such as `../outside/tool.exe` or `../outside/interpreter` is never checked for `..` components or symlink-resolved escape. If that path is executable on the host, `subprocess.run` at lines 176-184 starts it with the project as cwd, defeating the stated project-scoped command containment.

The documented exception for command element 0 is reasonable for an absolute configured interpreter such as `sys.executable`, but it should not also exempt relative path-like executables. Bare executable names should continue to resolve through `PATH`; relative executable paths should be rejected when they contain traversal or resolve outside the project. Add a regression test that places an executable outside the project and invokes it through a relative command[0] path, asserting rejection before execution. Keep the existing absolute-interpreter behavior explicit in the contract.

### Important findings

🟡 **Manifest stages do not retain detailed output inventories**

`runner.py:104-113` attaches the complete inventory to each execution result, and `_record_execution` in `mathmodel.py:113-123` persists it under `manifest["executions"]`. However, `_update_execution_stage` at `mathmodel.py:126-144` converts the inventory into path strings only, and `manifest.py:33` defines stage fields without an inventory field. Consequently, `manifest["stages"]["solver"]` and `manifest["stages"]["analysis"]` do not themselves expose per-file sizes, SHA-256 hashes, kinds, or provenance.

The review package specifically asks for stage-level output inventories and hashes/provenance. An observer consuming the stage records cannot verify output content without finding and correlating a separate execution record. Consider adding an `output_inventory` (or equivalent complete file-record field) to the stage contract and preserving it when updating the stage. Add an integration assertion for both solver and analysis stage records, including at least one generated output hash and provenance record.

🟡 **The path-like argument policy remains broader than the implementation contract explains**

`_argument_path_text` treats every non-option argument as path-like and treats every `--key=value` value as path-like. This is conservative, but it can reject legitimate scalar option values containing `..` or an absolute-looking string even when the value is not a path. The current behavior is acceptable as a safe default, but the configuration contract should document it, or the runner should identify path-bearing options explicitly. This is less urgent than the command[0] bypass because it fails closed rather than escaping the project.

## Task-quality verdict: NEEDS IMPROVEMENT

The fix is generally well structured. Centralizing execution in `run_project_command`, using `shell=False`, retaining stdout/stderr for pre-execution and runtime failures, assigning stable rule IDs, separating framework logs from generated outputs, and recording deterministic SHA-256 inventories are good choices. The new tests directly exercise symlink-resolved option values, solver inventories, input/config hashes, compilation short-circuiting, and malformed CLI configuration.

The quality bar is held back by the missing adversarial test for relative command[0] escape and by the split evidence model between `executions` and `stages`. The suite proves the newly implemented happy and failure paths, but does not yet prove the complete public manifest contract at the stage-consumer boundary.

### Minor findings

💭 **Skipped execution records should document their reproducibility shape**

`_skipped_execution` in `mathmodel.py:147-171` returns an empty `reproducibility` object. `_record_execution` later adds `input_hashes` and `config_sha256`, so the persisted execution record has the required run-level hashes, but consumers may reasonably expect the same reproducibility keys for skipped solver/analysis records as for executed records. Consider documenting that skipped stages have no command/code hashes, or provide an explicit `reproducibility.status`/reason field.

💭 **Use one canonical run-directory path representation in provenance**

Output entries use absolute `run_directory` values while stage outputs use project-relative paths. This is useful for local diagnostics, but a portable report consumer may benefit from also storing a canonical project-relative run directory or run ID as the primary reference. The existing `run_id` makes this recoverable, so this is a consistency improvement rather than a correctness defect.

## What is now satisfied

- Argument-array execution with `shell=False`, project cwd, captured stdout/stderr, timeout, exit code, and structured diagnostics.
- Resolution of existing path-like arguments, including `--option=value`, against the project root.
- Deterministic output inventories with file size, SHA-256, generated/framework classification, and run provenance.
- Input hashes and configuration hash in persisted execution evidence and the machine-readable build report.
- Solver-before-analysis ordering and analysis short-circuit after solver failure.
- Compilation, page metrics, artifact validation, and quality stages marked `SKIPPED` after solver or analysis failure.
- Malformed CLI command configuration returned as `BUILD-CONFIG-001` without starting a run.
- Unique append-only run directories and preservation of prior manifest contents.

## Recommended disposition

Do not mark Task 6 fully complete yet. Close the command[0] relative-path containment bypass, then make the stage-level inventory contract explicit and test it. After those changes, rerun the focused and complete suites; the current test evidence shows the remaining work should stay localized.
