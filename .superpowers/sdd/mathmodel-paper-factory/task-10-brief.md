# Task 10 brief — Release audit and package blocking

## Scope

Implement Task 10 from the plan, independently of the pending Task 9 real-paper body expansion. Read the plan/spec, current CLI and all reports. Do not weaken page gates or manufacture a PASS for `traning1`.

## Owned files

- Create `mathmodel-skill/scripts/mmcore/package.py` (allowed implementation support for the planned package interface)
- Modify `mathmodel-skill/scripts/mathmodel.py` to expose `package PROJECT --json`
- Create `mathmodel-skill/tests/test_release_audit.py`
- Create `mathmodel-skill/references/release-checklist.md`
- Modify `mathmodel-skill/SKILL.md` only for release-audit corrections found by tests

## Acceptance requirements

1. Follow TDD and write `task-10-report.md` with exact RED/GREEN/verification results.
2. `package` refuses to run when any machine hard gate fails, page/body/appendix thresholds fail, quality score is below profile minimum, manual review/checklist is unresolved, source/output hashes are missing, or the selected PDF is absent/stale.
3. Clean fixture packaging copies rather than mutates build artifacts and emits a unique PDF name containing page count and an 8-character content hash, plus a package manifest, source snapshot manifest, quality report, validation report, and reproducibility summary.
4. Package paths are project-contained and deterministic; never package a PDF from another project or silently use stale artifacts.
5. Tests cover body shortfall, appendix ratio, unresolved manual review, quality fail, stale/missing PDF, unique naming, manifest contents, source/output hashes, and clean fixture package.
6. Run focused and complete suites. For `traning1`, preserve the truthful BLOCKED result until Task 9 body scope is explicitly authorized and repaired.
