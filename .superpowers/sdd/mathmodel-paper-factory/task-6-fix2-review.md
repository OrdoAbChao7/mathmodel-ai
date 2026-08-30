# Task 6 fix2 final scoped review

## Summary

The fix2 changes address the two material gaps identified by the prior review. Relative path-like executables in `command[0]` are now rejected for traversal and for symlink-resolved targets outside the project; bare executable names continue to use `PATH`, and absolute interpreters such as `sys.executable` remain usable. Solver and analysis results now carry complete output inventories, and the build integration persists those inventories in both the solver and analysis manifest stage records.

No Critical or Important findings remain in the reviewed scope. The implementation is ready to close Task 6 for this scope, subject to the Minor test-quality note below.

## Verification evidence

- Focused: `python -m unittest mathmodel-skill.tests.test_runner_analysis mathmodel-skill.tests.test_manifest -v`
  - `Ran 23 tests ... OK (skipped=1)`.
- Complete: `python -m unittest discover -s mathmodel-skill/tests -v`
  - `Ran 80 tests ... OK (skipped=1)`.
- The sole skip is the existing Windows symlink-permission test, skipped with `WinError 1314`; the command-path regression uses its deterministic fallback and passes.
- A direct smoke check also confirmed bare `python` in `command[0]` remains PATH-resolved and succeeds. Existing focused coverage confirms absolute `sys.executable` execution.
- Direct source inspection covered `runner.py`, `analysis.py`, `mathmodel.py`, `manifest.py`, the focused tests, the Task 6 brief/spec, and the prior review/fix reports. No source or test files were edited.

## Spec-compliance verdict: PASS

The reviewed acceptance points are satisfied:

- Relative executable paths are checked before launch. Traversal is rejected with `RUNNER-PATH-001`, and existing relative executable paths are resolved before containment checking.
- Bare PATH names remain allowed, while absolute configured interpreters remain usable.
- Argument-array execution remains shell-free, project-scoped, timeout-bounded, and diagnostic-preserving.
- Solver and analysis inventories include relative path, size, SHA-256, kind, and run provenance. The inventories are attached to execution results and retained directly under `manifest["stages"]["solver"]` and `manifest["stages"]["analysis"]`.
- The integration tests verify generated solver and analysis files, hashes, provenance, and stage-level inventory presence.
- Solver failure skips analysis and dependent build stages; analysis failure skips compilation and later dependent stages while retaining the failure report.
- Malformed command configuration, missing executables, nonzero exits, timeouts, path escapes, and append-only run directories remain covered and passing.

### Minor finding

💭 **Test coverage: add an explicit permanent bare-PATH regression test**

The implementation and direct smoke check demonstrate that a bare `python` command remains usable, and absolute-interpreter behavior is covered by the existing test suite. However, the focused test file does not currently contain a named assertion for the bare-PATH contract. A future change to executable classification could therefore regress that requirement without a focused test failure.

**Suggestion:** Add a small test using a stable PATH-resolved executable (or a controlled test PATH) and assert successful execution. This is not a release blocker because the current behavior is correct and was verified directly.

## Task-quality verdict: PASS with minor improvement

The fix is localized and coherent. The runner centralizes containment and subprocess policy, the conservative argument rule is documented, inventories distinguish generated files from framework logs/manifests, and stage consumers receive the detailed evidence they need. The added tests target the prior security and manifest-contract gaps and the complete suite shows no regression.

The only quality improvement is to encode the bare-PATH smoke check as a permanent regression test. The known Windows permission skip is environmental and unchanged from the accepted baseline.

## Disposition

Task 6 fix2 is accepted for the requested scope. The remaining Minor suggestion can be handled opportunistically; no further fix2 changes are required.
