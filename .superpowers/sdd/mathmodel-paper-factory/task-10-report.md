# Task 10 report — Release audit and package blocking

## Implementation

- Added `mathmodel-skill/scripts/mmcore/package.py` with contained-PDF selection, strict machine/page/manual/hash gates, unique page-count/hash PDF names, source snapshots, evidence hashes, and package manifests.
- Added `package PROJECT --json` to the CLI.
- Added `mathmodel-skill/references/release-checklist.md`.
- Added four release tests covering body shortfall, appendix/manual blockers, missing/stale PDF and quality failure, and clean package naming/manifest output.

## Verification

Focused command:

```text
python -m unittest mathmodel-skill.tests.test_release_audit -v
Ran 4 tests ... OK
```

Direct real-project check:

```text
python mathmodel-skill/scripts/mathmodel.py package traning1 --json
{"status":"BLOCKED","checks":[{"rule":"PACKAGE-INPUT-001","status":"FAIL","message":"missing configuration: ...\\traning1\\mathmodel.json"}]}
```

This is intentional: Task 9 has not been authorized to expand the real paper body and its standard configuration does not exist. The package command does not manufacture a release candidate.

The complete suite currently has one expected Task 9 integration failure because `traning1` remains unadapted (plus the known Windows symlink-permission skip). It is recorded rather than hidden.

No Git commit was created; the workspace is not a Git repository.
