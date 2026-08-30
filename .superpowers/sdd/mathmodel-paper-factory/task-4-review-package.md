# Task 4 review package — Evidence-contract validation and quality scoring

## Review mode

This workspace is not a Git repository, so review the current files directly. The implementer report is in `task-4-report.md`; treat it as evidence, not as authority. Return separate verdicts for:

1. Spec compliance: does the implementation satisfy the design/spec and Task 4 brief?
2. Task quality: are the tests meaningful and is the implementation maintainable and safe?

Write the complete review to `task-4-review.md` in this directory. Classify findings as Critical, Important, or Minor. Do not edit production or test files.

## Required scope

- `mathmodel-skill/scripts/mmcore/contracts.py`
- `mathmodel-skill/scripts/mmcore/quality.py`
- `mathmodel-skill/scripts/mathmodel.py` (`audit PROJECT --json`)
- `mathmodel-skill/tests/test_quality.py`

## Task 4 acceptance requirements

- Implement `validate_artifacts(project: Path, required: tuple[str, ...]) -> dict`.
- Implement `audit_cross_references(artifacts: dict) -> list[dict]`.
- Implement `score_quality(checks: list[dict], manual: dict | None = None) -> dict`.
- Validate seven JSON artifact registries: problem-map, data-audit, model-registry, result-registry, claim-registry, figure-registry, validation.
- Hard-fail missing files, malformed JSON, invalid shapes, duplicate/missing IDs, broken references, missing result source files, missing figure files, missing required figure roles, and non-PASS validation statuses.
- Check records expose `rule`, `severity`, `status`, `message`, plus `path` and/or `evidence`.
- Required default figure roles are data/method/result/validation, configurable from project config.
- Quality weights are exactly 10/10/20/20/15/10/10/5 for the eight named dimensions.
- Without manual review, output must state `manual_review: PENDING`; hard failures force release failure; clean contract can reach at least 85.
- CLI `audit PROJECT --json` writes `build/quality-report.json` and `.md`, prints machine JSON, and leaves page metrics as PENDING for Task 5.
- Tests must include exact missing claim support rule `EVIDENCE-CLAIM-001` and clean score >=85.
- Do not implement PDF/page parsing in this task.

## Verification evidence to check

The implementer reports `python -m unittest discover -s mathmodel-skill/tests -v` as 25 passed, 1 skipped (Windows symlink permission). Independently run focused and complete tests; inspect edge cases and actual CLI output. Ensure no unrelated task work was introduced.
