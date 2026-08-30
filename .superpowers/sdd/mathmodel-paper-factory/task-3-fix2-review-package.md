# Task 3 fix round 2 review package

Review only Q3 from `task-3-fix-review.md`: deterministic regression coverage for recognized out-of-root entries when Windows cannot create symlinks.

Requirements: `.superpowers/sdd/mathmodel-paper-factory/task-3-brief.md`
Prior review: `.superpowers/sdd/mathmodel-paper-factory/task-3-fix-review.md`
Implementer report: `.superpowers/sdd/mathmodel-paper-factory/task-3-report.md`
Current source: `mathmodel-skill/scripts/mmcore/manifest.py`, `mathmodel-skill/tests/test_manifest.py`

Verify Q3 as ADDRESSED or NOT ADDRESSED and check new breakage in this fix only. Confirm the fallback test is repository-level, deterministic, and covers no crash, omitted out-of-root candidate, and warning. Write full review to `task-3-fix2-review.md`.
