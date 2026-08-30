# Task 4 independent review

## Summary and verdicts

The implementation has a clear small API, uses structured check records, implements the requested seven-file loading path, and produces both JSON and Markdown reports. The focused and complete suites pass independently, and the reviewed Python files compile.

Overall verdict:

- **Spec compliance: FAIL.** The implementation does not hard-fail several invalid artifact shapes or missing required evidence associations, despite those being explicit contract requirements. It also accepts result/figure paths outside the project root.
- **Task quality: FAIL.** The happy-path tests are useful but too narrow for a validator/quality gate: most explicit hard gates and the failure behavior of the CLI are untested. The scoring API also has weak input validation.

## Verification performed

- Focused suite: `python -m unittest discover -s mathmodel-skill/tests -p 'test_quality.py' -v` — **4 passed**.
- Complete suite: `python -m unittest discover -s mathmodel-skill/tests -v` — **25 passed, 1 skipped** (the reported Windows symlink-permission case).
- `python -m py_compile` passed for `contracts.py`, `quality.py`, and `mathmodel.py`.
- Direct probes showed that `data-audit.json` containing `[]` is accepted as `PASS`, while an empty `model-registry` or empty validation list only fails indirectly when another record happens to reference it.
- Direct CLI probe with a broken claim printed a JSON `FAIL` report and wrote a failing report, but returned exit code **0**.

## Findings

### Important — invalid registry shapes are not actually hard failures

`contracts.py:62-77` accepts any top-level object or array, and `_items()` silently turns absent, wrong-type, or empty collection fields into `[]`. The validator then treats those collections as valid: for example, `data-audit.json: []` produced `PASS`, and `{}` for a model registry can pass its ID check if no other artifact requires that model. Non-dictionary records inside a list are also discarded rather than reported.

**Why:** The acceptance requirements explicitly require hard failure for invalid shapes. A structurally unusable registry can therefore release with no data audit, models, claims, figures, or validations represented.

**Suggestion:** Define and enforce the expected top-level shape and required collection field for each of the seven files. Require the collection to have the expected type, validate every record rather than filtering invalid entries, and emit a dedicated `ARTIFACT-SHAPE-*` failure with a JSON path/evidence location.

### Important — required evidence associations can be omitted without failure

`audit_cross_references()` only checks values when fields are present as lists (`contracts.py:131-134`, `152-169`, `186-201`). A question with no `model_ids`, `result_ids`, `validation_ids`, or `claim_ids` gets a passing question-reference check; claims with no `result_ids` or `validation_ids` likewise pass. This violates the design contract that every question must have at least one model, result, validation, and conclusion/claim, and it weakens the requested broken-reference gate.

**Why:** Missing evidence is different from an empty set of references. Treating both as equivalent permits an apparently complete registry to contain no traceability chain.

**Suggestion:** Validate required fields and non-empty lists before resolving IDs. Use separate rules for missing required support versus an unknown referenced ID, and test both cases.

### Important — source and figure paths are not constrained to the project

`contracts.py:237` and `250` test `(project / source).is_file()` and `(project / file_path).is_file()` without resolving and checking containment. Absolute paths are accepted by `Path` joining, and `..` paths can point outside the project if the target exists.

**Why:** The project contract is supposed to be reproducible and project-scoped. External files can make an audit pass while depending on undeclared local data; they also create an avoidable path-validation/security boundary failure.

**Suggestion:** Resolve each declared path and require it to be under the resolved project root (and reject absolute paths). Report path escape as a hard failure before checking existence.

### Important — the test suite does not cover the stated hard gates

`test_quality.py` tests one broken claim reference, one clean fixture, check-field presence, and a clean CLI report. It has no tests for missing/malformed files, invalid shapes, duplicate IDs, missing IDs, missing result sources, missing figure files, missing roles, non-PASS validation statuses, configurable roles, path escapes, or manual scoring behavior (`test_quality.py:123-171`).

**Why:** The passing suite gives little protection against regressions in the majority of the acceptance surface. The shape and omission bugs above are exactly the kind of defects a negative contract matrix should catch.

**Suggestion:** Add table-driven tests for every hard gate, including malformed collection types and missing required fields, plus a CLI test asserting the intended exit behavior for a failing audit.

### Minor — check evidence is discarded whenever `path` is supplied

`_check()` stores `path` or `evidence`, never both (`contracts.py:37-40`). Callers frequently pass both, so useful failure details such as missing IDs are absent from the returned check when a path is present.

**Why:** The acceptance requires check records to expose a path and/or evidence, so this technically satisfies the minimum contract, but it makes repair-oriented reports less informative.

**Suggestion:** Preserve both fields when supplied. At minimum, include the detailed evidence in the JSON report for failed checks.

### Minor — partial or malformed manual input is treated as complete or can crash

`score_quality()` marks any non-empty manual dictionary as `COMPLETE` (`quality.py:46`, `65`) and converts values with `int()` without validating type/range (`quality.py:49-56`). A dictionary containing only one dimension therefore clears the manual-review state, while a malformed value raises instead of returning a checkable result.

**Suggestion:** Validate the manual schema, require all named manual-review dimensions/checklist fields before marking it complete, and return a controlled failure for invalid input.

### Minor — failing audit returns success exit code

`mathmodel.py:101-118` reports `status: FAIL` and `quality: FAIL` but always returns `0`. The acceptance explicitly says hard failures force release failure; if CLI status is used by automation, a zero exit code contradicts that outcome.

**Suggestion:** Confirm the CLI contract and, if audit is intended for automation, return a non-zero code for contract/release failure while still writing the reports. Add a regression test.

## Acceptance requirements

| Requirement | Direct assessment |
|---|---|
| Implement `validate_artifacts(project, required)` | **Addressed.** Function exists with the requested return shape. Its validation coverage is incomplete; see Important findings. |
| Implement `audit_cross_references(artifacts)` | **Partially addressed.** It checks several list-based references, but does not reject omitted required associations. |
| Implement `score_quality(checks, manual=None)` | **Addressed with quality caveat.** It returns dimensions, weights, total, hard failures, manual state, and release status; manual input validation is weak. |
| Validate all seven JSON artifact registries | **Partially addressed.** All seven are loaded, but only six have record/ID logic and `data-audit` content is effectively unchecked. |
| Hard-fail missing files | **Addressed.** `ARTIFACT-FILE-001` is emitted. |
| Hard-fail malformed JSON | **Addressed.** `ARTIFACT-JSON-001` is emitted. |
| Hard-fail invalid shapes | **Not addressed.** Broad object/array acceptance and silent filtering allow invalid registries. |
| Hard-fail duplicate/missing IDs | **Partially addressed.** Works for recognized dictionary records in six collections; missing/invalid collection shapes can evade it. |
| Hard-fail broken references | **Partially addressed.** Known missing IDs are caught, but missing reference fields are not. |
| Hard-fail missing result source files | **Addressed for in-project relative existing files.** Path containment is missing. |
| Hard-fail missing figure files | **Addressed for in-project relative existing files.** Path containment is missing. |
| Hard-fail missing required figure roles, configurable from config | **Addressed for a valid role list.** Invalid config values are silently ignored and defaults used. |
| Hard-fail non-PASS validation statuses | **Addressed for enumerated validation records.** Empty/malformed validation collections can evade the check. |
| Check records expose rule/severity/status/message and path and/or evidence | **Addressed.** `_check()` supplies these fields, though it drops evidence when path is present. |
| Exact weights 10/10/20/20/15/10/10/5 | **Addressed.** `DIMENSION_WEIGHTS` matches exactly and sums to 100. |
| No manual review states `manual_review: PENDING` | **Addressed.** `score_quality()` returns `PENDING` with no manual data. |
| Hard failures force release failure | **Addressed in the returned quality object.** `release_status` becomes `FAIL`; CLI exit-code behavior remains ambiguous/weak. |
| Clean contract can reach at least 85 | **Addressed.** Independent clean test passed; observed score is at least 85. |
| CLI audit writes JSON and Markdown reports, prints machine JSON, leaves page metrics PENDING | **Addressed.** Independent CLI test passed and report contains `page_metrics.status: PENDING`. |
| Tests include `EVIDENCE-CLAIM-001` and clean score >=85 | **Addressed.** Both explicit tests pass. |
| Do not implement PDF/page parsing in Task 4 | **Addressed.** The CLI explicitly leaves page metrics pending and no PDF parsing was found in the reviewed scope. |

## Recommended next steps

First add strict per-registry shape/required-field validation and project-root path checks; these are release-safety issues. Then expand `test_quality.py` into a complete negative-case matrix and clarify whether a failing `audit` must return non-zero. The existing API structure is a reasonable base once those gates are made strict and directly tested.
