# Task 3 review

## Verdicts

- Spec compliance: **FAIL — run-ID format is weaker than the stated contract**.
- Task quality: **FAIL — focused tests are too narrow to protect the append-only and metadata requirements**.

## Review basis

Reviewed the Task 3 review package, `task-3-brief.md`, `task-3-report.md`, the current implementations of `manifest.py` and `mathmodel.py`, `test_manifest.py`, and the Task 1–2 configuration/scaffold code used by the CLI. The design specification and SDD progress ledger were also checked for downstream compatibility. No Git review was possible because the workspace has no `.git` directory, and no subagents were dispatched.

Fresh read-only verification on 2026-08-30:

```text
python -m unittest discover -s mathmodel-skill/tests -p 'test_manifest.py' -v
Ran 5 tests ...
OK

python -m unittest discover -s mathmodel-skill/tests -v
Ran 17 tests ...
OK

python mathmodel-skill/scripts/mathmodel.py --help
exit 0

python mathmodel-skill/scripts/mathmodel.py inspect --help
exit 0
```

The exact test output included the expected pre-existing stderr line from the invalid-problem-type scaffold test; it did not cause a test failure.

## Spec compliance findings

### S1 — Run IDs do not follow the documented UTC timestamp-plus-hash contract

- Severity: **P2 (minor but contractual)**
- File/function: `mathmodel-skill/scripts/mmcore/manifest.py:new_run`, lines 122–133.
- Evidence: the run ID is built as `f"{time.time_ns()}-{hashlib.sha256(snapshot).hexdigest()[:12]}"`. This is a local epoch nanosecond integer plus a hash, not a UTC timestamp plus hash as required by the Task 3 package and the design specification’s “UTC time加输入哈希短码” format. The report itself shows IDs such as `1788081150964486600-86b23d14e360`.
- Impact: IDs remain unique and sortable by time, but they are not human-readable UTC run timestamps and the timestamp component is not visibly tied to the recorded UTC `created_at`. Downstream operators cannot identify a run’s time from the ID without conversion.
- Repair: generate the ID from a UTC timestamp in the project’s documented format, followed by the short input/config hash; retain the collision suffix fallback if necessary. Add an assertion for the ID shape and its correspondence to the manifest timestamp.

The remaining core behaviors are implemented correctly: SHA-256 is chunked and lowercase; inventory paths are project-relative POSIX paths; configured files and recognized PDF/document/spreadsheet/code/LaTeX files are included; missing configured files become `exists: false` with `WARN`; manifests snapshot config and inventory hashes; each invocation creates a new run directory; stage updates preserve prior list evidence; stage objects contain the seven required keys; and `inspect PROJECT --json` writes both the audit and manifest while preserving `init`, `adopt`, and help dispatch.

No implementation of Tasks 4–10 was found in the reviewed Task 3 files. There is no raw-data overwrite or shell interpolation in this scope, and no third-party dependency was introduced.

## Task quality findings

### Q1 — Append-only evidence accumulation is not tested

- File: `mathmodel-skill/tests/test_manifest.py`, `test_run_manifest_records_input_hash_and_stages`, lines 79–89.
- Evidence: the test calls `update_stage` once and checks one output. It does not call the same stage twice with separate outputs, warnings, and errors, so it would not detect accidental replacement of prior evidence. The implementation currently concatenates list fields, but this important contract is unprotected.
- Impact: a future change could silently lose evidence from earlier stage updates while all current tests still pass. Historical run append-only behavior is checked only by creating two directories, not by verifying that the first manifest remains unchanged after the second run.
- Repair: update a stage at least twice and assert that all prior outputs/warnings/errors remain in order; snapshot the first manifest and assert that creating a second run does not modify it.

### Q2 — Tests do not validate the complete manifest metadata and inventory contract

- File: `mathmodel-skill/tests/test_manifest.py`.
- Evidence: `test_run_manifest_records_input_hash_and_stages` only asserts that `input_hashes` exists and that one stage has the required keys. It does not assert the recorded command, exact config snapshot, Python version/executable fields, hashes for every existing inventory entry, modified time/size fields, or POSIX normalization of a configured path containing `..`. The inspect test only checks artifact/manifest existence and command.
- Impact: the suite could pass while required provenance fields disappear or while only the hand-built fixture hash is recorded. The report’s complete-suite success therefore demonstrates the implemented examples, not the whole Task 3 evidence contract.
- Repair: add focused assertions for command/config/environment metadata, all existing-file inventory fields and hash values, normalized paths, missing-file warnings, and JSON output contents. Add a CLI regression test that exercises `init`/`adopt` followed by `inspect` on a real temporary project.

### Q3 — No test covers boundary/error behavior for recognized files outside the root

- File/function: `manifest.py:_relative` and `inventory_project`, lines 41–43 and 79–106.
- Evidence: inventory resolves every path before converting it to a relative path. A symlinked recognized file whose target resolves outside the project can cause `relative_to` to raise `ValueError`, turning inspection into an uncaught exception. The existing path validator protects configured paths, but the automatically recognized tree is not tested against this filesystem edge case.
- Impact: inspection is less robust on projects containing linked datasets or scripts. This is not demonstrated by the current fixture, which contains only ordinary regular files.
- Repair: either explicitly skip or warn on recognized paths whose resolved target escapes the project root, and add a platform-appropriate symlink test (or a deterministic unit test around `_relative`) so inspection never crashes on an out-of-root recognized entry.

## CLI compatibility and scope

The parser additions are additive: `init`, `adopt`, no-command help, and `inspect --help` all remain usable. `inspect` normalizes its project argument at the boundary and calls the existing Task 1 `load_config`, so path containment remains enforced for configured inputs. The implementation is limited to inventory, hashing, run manifests, stage updates, and inspect dispatch; it does not pre-implement later build/audit/package behavior.

One non-blocking quality note: a configuration error during `inspect` is not converted into a concise CLI error in `main`; `load_config` exceptions propagate with a traceback. Task 3 does not specify an error UX for this path, so this is not a separate compliance failure.

## Conclusion

The main Task 3 functionality works for the supplied scenarios and the full current suite is green. Acceptance should nevertheless remain blocked until the documented UTC run-ID format is implemented or explicitly revised, and the focused tests cover repeated stage updates, historical manifest preservation, and complete provenance metadata.
