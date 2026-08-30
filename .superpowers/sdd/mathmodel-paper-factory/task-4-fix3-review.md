# Task 4 final scoped review (fix3)

## Summary

The fix3 implementation closes the last finding from the fix2 review. `score_quality()` now distinguishes omitted manual input (`manual is None`) from every non-dictionary value, including falsy values such as `[]`, `""`, `0`, and `False`. Those invalid payloads produce controlled `manual_review: INVALID`, populated `manual_errors`, and `release_status: FAIL`; omitted input remains `PENDING` with `PENDING_MANUAL_REVIEW`.

The current Task 4 implementation and regression coverage satisfy the reviewed brief. The artifact validator has strict required-file/JSON/shape/ID/support/reference/path/role/validation gates, quality weights remain exact, hard failures force release failure, the CLI writes reports and returns non-zero for failed audits, and page metrics remain pending as required. No Critical, Important, or Minor issue remains in the scoped Task 4 work. The only complete-suite skip is the environment-only Windows symlink-permission case.

## Verification performed

- Focused suite: `python -m unittest discover -s mathmodel-skill/tests -p 'test_quality.py' -v` — **20 passed, 0 failed**.
- Complete suite: `python -m unittest discover -s mathmodel-skill/tests -v` — **41 passed, 0 failed, 1 skipped**. The sole skip is `test_out_of_root_recognized_symlink_is_warned_or_skipped`, skipped because this Windows environment denies symlink creation with `[WinError 1314]`; the non-symlink out-of-root coverage passes.
- Compile check: `python -m py_compile mathmodel-skill/scripts/mmcore/contracts.py mathmodel-skill/scripts/mmcore/quality.py mathmodel-skill/scripts/mathmodel.py` — **passed**.
- Direct manual-boundary probe: `None` returns `PENDING` / `PENDING_MANUAL_REVIEW`; `[]`, `""`, `0`, `False`, `['bad']`, `"bad"`, and `7` each return `INVALID` / `FAIL` with non-empty errors.
- Source and test inspection covered `contracts.py`, `quality.py`, `mathmodel.py`, `test_quality.py`, and the manifest symlink test. No source or test files were edited during this review; only this review file was written.

## Previous finding verification

| Previous finding | Result | Evidence |
|---|---|---|
| Invalid registry shapes were accepted | **Closed** | `contracts.py:73-160` enforces object containers, non-empty required collections, and dictionary records; the focused invalid-shape matrix passes. |
| Required evidence associations could be omitted or malformed | **Closed** | `contracts.py:222-268` rejects missing, empty, non-list, empty-string, and non-string question/claim support lists; focused omission and member-type tests pass. |
| Result/figure paths could escape the project | **Closed** | `contracts.py:425-435` rejects absolute paths and resolved paths outside the project root; focused path tests pass. |
| Hard gates lacked negative-case coverage | **Closed** | Focused tests cover all seven missing files, all seven malformed JSON files, invalid shapes, IDs, support associations, cross-reference directions, evidence paths, roles, validation status, CLI failure, and manual input boundaries. |
| Check evidence was discarded when `path` was supplied | **Closed** | `_check()` always exposes both `path` and `evidence`; the check-record regression passes. |
| Partial/malformed manual input was accepted or could crash | **Closed** | `_validate_manual()` type-checks before `.items()` and `score_quality()` passes the value unchanged; the expanded regression matrix covers truthy and falsy non-dictionaries. |
| Falsy non-dictionary manual values were misclassified as omitted | **Closed** | The current code checks `manual is None`; direct probes and `test_manual_scores_reject_non_dict_inputs_without_crashing` confirm `[]`, `""`, `0`, and `False` are `INVALID`/`FAIL`. |
| Failing audit returned success exit code | **Closed** | `mathmodel.py:101-118` returns `1` when contract or quality release status fails; the failing-CLI regression passes. |

## Findings

### Critical

None.

### Important

None.

### Minor

None.

No issue remains beyond the explicitly documented environment-only symlink test skip. That skip does not indicate a product or test-contract defect: the same behavior is covered through the non-symlink out-of-root test, which passes.

## Verdicts

### Spec-compliance verdict: PASS

Task 4’s required behavior is implemented and directly exercised: all seven artifacts are loaded; missing/malformed files and invalid shapes fail; IDs, evidence associations, cross-references, result/figure paths, figure roles, and validation statuses are enforced; exact dimension weights are retained; hard failures force release failure; reports are emitted; page metrics remain `PENDING`; and failed audits return a non-zero exit code. The manual API boundary now correctly distinguishes `None` from all non-dictionary values.

### Task-quality verdict: PASS

The implementation is readable and the regression suite now covers the previously missing release-safety cases and the complete manual-input boundary. Focused and complete tests pass with no unexplained failures, and the only skip is attributable to Windows symlink permissions.

## Final disposition

- **Critical:** none.
- **Important:** none.
- **Minor:** none.
- **Environment-only exception:** one Windows symlink-creation skip (`[WinError 1314]`), with the corresponding non-symlink containment behavior passing.

Task 4 fix3 is approved as complete within scope.
