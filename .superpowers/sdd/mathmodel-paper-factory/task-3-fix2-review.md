# Task 3 fix round 2 re-review

## Verdict

Q3 — **ADDRESSED**

## Review basis

Reviewed the round-2 package, prior review, implementation report, and current files:

- `mathmodel-skill/scripts/mmcore/manifest.py`
- `mathmodel-skill/tests/test_manifest.py`

No source files were edited and no subagents were dispatched.

Focused verification on 2026-08-30:

```text
python -m unittest discover -s mathmodel-skill/tests -p 'test_manifest.py' -v
----------------------------------------------------------------------
Ran 9 tests in 0.082s

OK (skipped=1)
```

The one skipped test is the symlink-specific test; Windows denied non-elevated symlink creation with `[WinError 1314]`, and the test records that permission reason. The deterministic fallback test ran and passed.

## Q3 — Deterministic regression coverage for out-of-root recognized entries

**Verdict: ADDRESSED.**

The repository now contains `test_out_of_root_recognized_candidate_is_warned_and_skipped_without_symlink`. It is deterministic because it uses an ordinary out-of-root candidate path and mocks `_recognized_paths`; it does not depend on symlink creation privileges.

The test covers all required behaviors:

- `recognized_path_decision` returns no relative path and an `out-of-root` warning, proving the containment decision does not raise.
- `inventory_project` completes successfully with the injected out-of-root candidate.
- The candidate is absent from `inventory["files"]`.
- The inventory contains exactly one out-of-root warning.

The production path is routed through the same `recognized_path_decision` seam, so the regression test exercises the inventory behavior rather than only testing an unused helper. The symlink-specific test remains useful where permissions allow it and is appropriately skipped on this Windows host.

## New Critical/Important issues in this fix scope

No new Critical or Important issue was found in the round-2 fix. The focused suite passes with only the documented, permission-driven symlink skip.

## Conclusion

Q3 is addressed: repository-level deterministic fallback coverage verifies no crash, omission of the out-of-root candidate, and warning emission, while the focused test suite completes successfully.
