# Task 4 final scoped re-review (fix2)

## Summary

The fix2 changes close the previously reported missing-file, malformed-JSON, omitted-support, non-string-support-member, cross-reference-direction, and non-empty malformed-manual-input gaps. The current focused and complete test suites pass, and the reviewed Task 4 Python files compile.

One residual edge case remains in `score_quality()`: falsy non-dictionary manual values are converted to `{}` before `_validate_manual()` can reject them. Thus `[]`, `""`, `0`, and `False` produce `manual_review: PENDING` instead of the controlled `INVALID` result promised for non-dictionary input. This is a minor API-boundary robustness issue, but it also means the new regression test does not cover the full non-dictionary input domain.

No Critical finding was found.

## Verification performed

- Focused suite: `python -m unittest discover -s mathmodel-skill/tests -p 'test_quality.py' -v` — **20 passed**.
- Complete suite: `python -m unittest discover -s mathmodel-skill/tests -v` — **41 passed, 1 skipped**. The skipped test is the existing Windows symlink-permission case.
- Compile check: `python -m py_compile mathmodel-skill/scripts/mmcore/contracts.py mathmodel-skill/scripts/mmcore/quality.py mathmodel-skill/scripts/mathmodel.py` — **passed**.
- Direct input probe confirmed that `['bad']`, `'bad'`, and `7` return `INVALID`, while `[]`, `''`, `0`, and `False` return `PENDING` / `PENDING_MANUAL_REVIEW` with no errors.
- No source or test files were edited during this review.

## Previous finding verification

| Previous finding | Result | Evidence |
|---|---|---|
| Missing required artifact files lacked regression coverage | **Closed** | `test_each_missing_required_artifact_is_a_hard_failure` covers all seven files and asserts `ARTIFACT-FILE-001` with the expected path. |
| Malformed JSON lacked regression coverage | **Closed** | `test_each_malformed_required_artifact_is_a_hard_failure` covers all seven files and asserts `ARTIFACT-JSON-001` with the expected path. |
| Required support fields could be omitted or empty | **Closed** | `test_omitted_required_support_fields_are_hard_failures` and the non-empty association tests cover all question fields plus claim result/validation fields. `_required_id_list()` also rejects non-list, empty, empty-string, and non-string members. |
| Cross-reference variants were not independently covered | **Closed for the stated variants** | `test_independent_broken_cross_reference_directions_are_hard_failures` covers question→model, model→question, validation→question, and figure→claim; claim→result remains covered by the required claim-support test. |
| Non-dictionary manual input could crash | **Partially closed** | Truthy list/string/scalar inputs now return controlled `INVALID` results and are tested. Falsy non-dictionary inputs are still erased by `manual or {}` at `quality.py:75`. See M-1. |

## Remaining findings

### 💭 Minor — falsy non-dictionary manual values are misclassified

`mathmodel-skill/scripts/mmcore/quality.py:75` calls `_validate_manual(manual or {})`. Because empty lists, empty strings, numeric zero, and `False` are falsy, they bypass the type guard at `quality.py:51-52` and are treated exactly like omitted manual input.

**Why:** A caller supplying an invalid manual payload can receive `manual_review: PENDING` and `release_status: PENDING_MANUAL_REVIEW` rather than `manual_review: INVALID`, `manual_errors`, and `release_status: FAIL`. This is inconsistent with the fix2 contract and with the behavior for truthy non-dictionary values.

**Suggestion:** Pass `manual` through unchanged and let `_validate_manual()` distinguish `None` from a non-dictionary value, for example by checking `if manual is None` before the type check. Extend the regression test with `[]`, `""`, `0`, and `False`.

## Verdicts

### Spec-compliance verdict: PASS with a minor edge-case caveat

The required Task 4 behavior is implemented for the documented `dict | None` interface and the required fix2 cases: all seven artifacts are loaded; missing and malformed artifacts fail; registry shapes, IDs, support associations, cross-references, result/figure paths, figure roles, and validation statuses are checked; exact weights are retained; hard failures force release failure; reports are written; page metrics remain `PENDING`; and failing CLI audits return exit code 1. The remaining issue concerns invalid values outside the declared type boundary, but it is still a small gap in the requested controlled non-dictionary-input handling.

### Task-quality verdict: PASS with a minor test-coverage caveat

The implementation is readable, the fix2 regression coverage is materially stronger, and both suites pass. The only remaining quality issue is that the new non-dictionary manual-input test covers truthy invalid values but not falsy ones, allowing the `manual or {}` regression to persist. Add that boundary matrix and the task quality is clean.

## Final disposition

- **Critical:** none.
- **Important:** none remaining in the scoped fix2 findings.
- **Minor:** one production/test edge case: falsy non-dictionary manual input is treated as omitted input (M-1).

The fix2 pass is suitable for the scoped Task 4 requirements, subject to the small manual-input hardening noted above.
