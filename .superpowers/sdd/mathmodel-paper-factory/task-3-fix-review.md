# Task 3 fix re-review

## Verdicts

- S1 — **ADDRESSED**
- Q1 — **ADDRESSED**
- Q2 — **ADDRESSED**
- Q3 — **NOT ADDRESSED**

## Review basis

Reviewed the Task 3 requirements, original review, implementation report, and current files:

- `mathmodel-skill/scripts/mmcore/manifest.py`
- `mathmodel-skill/scripts/mathmodel.py`
- `mathmodel-skill/tests/test_manifest.py`

No source files were modified and no subagents were dispatched.

Targeted checks run on 2026-08-30:

```text
python -m unittest discover -s mathmodel-skill/tests -p 'test_manifest.py' -v
Ran 8 tests in 0.084s
OK (skipped=1)
```

The skipped test was `test_out_of_root_recognized_symlink_is_warned_or_skipped`; Windows denied non-elevated symlink creation with `[WinError 1314]`, and the test reported that reason.

```text
python -m unittest discover -s mathmodel-skill/tests -v
Ran 20 tests in 0.250s
OK (skipped=1)
```

A deterministic read-only fallback probe patched the recognized-path provider with an out-of-root `.py` path and verified that inventory omitted it and returned an `out-of-root` warning. That confirms the production guard, but it is not currently represented as a repository test.

## Finding review

### S1 — UTC timestamp-plus-hash run IDs

**Verdict: ADDRESSED.**

`new_run` now derives the run ID from the recorded UTC `created_at` using `YYYYMMDDTHHMMSSZ`, followed by the first 12 lowercase SHA-256 characters of the canonical config/input-hash payload. The focused test verifies the ID shape, correspondence to `created_at`, expected hash, and run-directory name. The collision suffix fallback preserves uniqueness without affecting the normal contract.

### Q1 — Append-only stage and historical manifest evidence

**Verdict: ADDRESSED.**

The stage test updates the same stage twice and verifies ordered retention of outputs, warnings, and errors, while preserving the seven required stage fields. The run-directory test snapshots the first manifest, creates a second run, and verifies the first manifest remains byte-for-byte unchanged. `update_stage` appends list evidence rather than replacing it.

### Q2 — Complete provenance and inventory coverage

**Verdict: ADDRESSED.**

The new focused coverage checks normalized project-relative POSIX paths, configured and recognized files, missing-file `WARN` behavior, type/size/modified-time/existence fields, hashes for every existing inventory item, command/config snapshots, Python version and executable metadata, input hashes, and inspect JSON/audit contents. The complete suite also remains green, so the added assertions do not regress Tasks 1–2 CLI behavior.

### Q3 — Safe handling of recognized files outside the project root

**Verdict: NOT ADDRESSED.**

The implementation now catches `ValueError` from resolving an out-of-root recognized path and records a warning while skipping the entry. The Windows symlink test is present and its permission-based skip is documented. However, because that test is skipped on this host, the current repository contains no deterministic fallback test for the same boundary behavior (for example, a controlled `_relative`/recognized-path unit test). The package explicitly permits the symlink test to be skipped only with such a fallback test. The manual probe performed during this review passes, but it does not satisfy repository-level regression coverage.

## New Critical/Important issues in fix scope

No new Critical or Important implementation issue was found. The only remaining issue is the Q3 test-coverage gap described above.

## Conclusion

S1, Q1, and Q2 are addressed and verified. Q3 remains not addressed for acceptance because the required deterministic fallback regression test is absent, despite the production guard behaving safely under the manual fallback probe.
