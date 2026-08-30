# Task 4 scoped fix re-review

## Summary

The fix pass correctly addresses the main contract defects from the original review: registry collections are now checked for the expected object/list shape, required question and claim support lists must be non-empty and string-valued, result and figure paths are project-contained, check records retain both `path` and `evidence`, manual scores are validated for the documented dictionary cases, and a failing audit returns exit code 1.

No Critical issue was found. The implementation is functionally stronger, but the review is not fully clean: the negative-case suite still omits missing-file and malformed-JSON regression tests, and non-dictionary manual input still crashes rather than returning a controlled invalid result.

## Verification performed

- Focused suite: `python -m unittest discover -s mathmodel-skill/tests -p 'test_quality.py' -v` — **13 passed**.
- Complete suite: `python -m unittest discover -s mathmodel-skill/tests -v` — **34 passed, 1 skipped**. The skipped case is the existing Windows symlink-permission case.
- Compile check: `python -m py_compile mathmodel-skill/scripts/mmcore/contracts.py mathmodel-skill/scripts/mmcore/quality.py mathmodel-skill/scripts/mathmodel.py` — **passed**.
- Direct malformed manual-input probe: `score_quality([], ['bad'])` raises `AttributeError: 'list' object has no attribute 'items'`.
- No source or test files were edited during this review.

## Original finding verification

| Original finding | Re-review result | Evidence |
|---|---|---|
| Invalid registry shapes were accepted | **Addressed** | `contracts.py:73-160` enforces object containers, required non-empty collections, and dictionary records. The focused shape matrix passes, including `figure-registry: {"figures": null}` without crashing. |
| Required evidence associations could be omitted | **Addressed** | `contracts.py:222-268` rejects missing, empty, non-list, and invalid-string question/claim support fields. The focused required-association tests pass. |
| Result/figure paths could escape the project | **Addressed** | `contracts.py:425-435` rejects absolute paths and resolved paths outside the project root before checking existence. Focused absolute and `..` escape tests pass. |
| Hard gates lacked negative-case coverage | **Partially addressed; remains Important** | `test_quality.py` now covers shapes, IDs, support omissions, missing evidence files, roles, validation status, path escapes, manual values, and CLI failure. It still has no regression tests for missing required artifacts or malformed JSON, and does not exercise several independent broken-reference/missing-field variants. See Finding I-1. |
| Check evidence was discarded when `path` was also supplied | **Addressed** | `contracts.py:39-47` always emits both keys and preserves the supplied evidence. The check-record test passes. |
| Partial/malformed manual input was accepted or could crash | **Partially addressed; remains Minor** | `quality.py:48-68` correctly handles partial dictionaries, unknown dimensions, non-integer values, booleans, and out-of-range integers. However, `manual` is not type-checked before `.items()`, so a non-dict value still raises. See Finding M-1. |
| Failing audit returned exit code 0 | **Addressed** | `mathmodel.py:101-118` returns 1 when contract or release quality fails; the focused failing-CLI test passes. |

## Findings

### 🟡 Important — negative tests still do not protect all required artifact gates

`mathmodel-skill/tests/test_quality.py:159-175` covers invalid shapes, but the current suite never deletes a required artifact or writes malformed JSON. Those are explicit contract gates and were part of the original review finding. The suite also does not independently cover missing result/figure fields, unknown model/validation question IDs, broken figure claim IDs, or non-string reference-list members.

**Why:** The implementation currently handles missing files and malformed JSON in `_load_artifacts`, but without regression tests those paths can silently regress. The omitted cross-reference variants are especially relevant because `_missing_references()` only reports unknown string values; support validation catches some malformed lists, but the intended behavior is not directly locked down for every relationship.

**Suggestion:** Add table-driven tests for each required file missing and malformed, then add one test per cross-reference direction and per required path field. Assert both `status == "FAIL"` and the specific rule/check evidence.

### 💭 Minor — non-dictionary manual input still raises instead of returning controlled validation

`mathmodel-skill/scripts/mmcore/quality.py:48-68` assumes `manual` has `.items()`. Although the public annotation is `dict | None`, the fix report explicitly describes malformed manual input as controlled invalid input, and callers can pass JSON-decoded or CLI-provided values of another type.

**Why:** A malformed manual payload can terminate the audit/scoring call with an exception instead of producing `manual_review: INVALID`, `manual_errors`, and `release_status: FAIL`.

**Suggestion:** Check `isinstance(manual, dict)` before iterating and return the same controlled invalid state used for malformed dictionary contents. Add a regression test for a list, string, and scalar input if those values can cross the API boundary.

## New issue assessment

- **Critical:** none found.
- **Important:** one remaining test-quality gap, described above; no newly discovered production contract failure beyond the previously reported coverage gap.
- **Minor:** one remaining malformed-input robustness issue, described above; it is a residual form of the original manual-input finding.

## Verdicts

### Spec-compliance verdict: PASS with a test-coverage caveat

The required Task 4 behavior is implemented: all seven artifacts are loaded, malformed/missing artifacts and invalid registry shapes fail, required evidence associations and references are checked, paths are contained, validation statuses and figure roles are enforced, quality weights remain exact, hard failures force release failure, reports are written, page metrics remain `PENDING`, and the failing CLI returns non-zero. The remaining manual crash is outside the declared `dict | None` type boundary, though it should still be hardened.

### Task-quality verdict: FAIL

The implementation is readable and the focused/complete suites pass, but the test suite does not yet provide the complete negative contract matrix claimed by the fix report, and malformed non-dictionary manual input is not safely handled. Add those tests and the small input guard before treating the fix pass as fully complete.

## Recommended next steps

1. Add missing-file and malformed-JSON tests plus the omitted cross-reference/path-field cases.
2. Guard the `manual` argument type and test controlled failure for non-dictionary input.
3. Re-run the focused and complete suites and update this review if both findings are closed.
