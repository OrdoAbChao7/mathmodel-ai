# Task 1 fix review package

## Scope

Review only the fix for finding S1 from `task-1-review.md`: `main(["--help"])` must return integer `0` rather than raising `SystemExit`; a focused regression test must cover it.

## Artifacts

- Requirements: `.superpowers/sdd/mathmodel-paper-factory/task-1-brief.md`
- Original report: `.superpowers/sdd/mathmodel-paper-factory/task-1-report.md`
- Original review: `.superpowers/sdd/mathmodel-paper-factory/task-1-review.md`
- Current files: `mathmodel-skill/scripts/mathmodel.py`, `mathmodel-skill/tests/test_config.py`

## Review contract

Independently inspect the fix, verify the focused test is present and meaningful, and check for new breakage in the changed lines. Verdict each S1 item as ADDRESSED or NOT ADDRESSED; report any new Critical/Important issue in the fix scope. Write the full review to `.superpowers/sdd/mathmodel-paper-factory/task-1-fix-review.md`.
