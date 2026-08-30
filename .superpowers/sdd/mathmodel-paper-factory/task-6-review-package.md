# Task 6 review package

This workspace is not a Git repository; inspect the current files directly. Read `task-6-brief.md`, the plan/spec, and the implementer report at `task-6-report.md`. Do not edit source or tests. Run focused and complete suites.

Review scope: `mathmodel-skill/scripts/mmcore/runner.py`, `analysis.py`, `mathmodel.py`, and `tests/test_runner_analysis.py`.

Acceptance: safe argument-array and project-scoped execution; timeouts and missing/nonzero commands are structured; analysis runs only after solver success; append-only run manifests contain command/timestamp/input/config hashes/exit and timeout status/log paths/output inventory; deterministic project-contained hash-addressed output collection without following outside paths; build CLI invokes solver then analysis and writes machine report; tests cover success order, short circuit, timeout, missing command, path escape, hashing/provenance, append-only runs, and CLI integration. Return separate spec-compliance and task-quality verdicts with Critical/Important/Minor findings and write full review to `task-6-review.md`.
