# Task 6 brief — Solver execution and reproducible analysis outputs

## Scope

Implement only Task 6 from `docs/superpowers/plans/2026-08-30-mathmodel-paper-factory.md`. Read the design/spec and project-local `mathmodel-skill/SKILL.md` before editing. Do not implement Task 7+ figure-asset registry work.

## Owned files

- Create `mathmodel-skill/scripts/mmcore/runner.py`
- Create `mathmodel-skill/scripts/mmcore/analysis.py`
- Modify `mathmodel-skill/scripts/mathmodel.py`
- Create `mathmodel-skill/tests/test_runner_analysis.py`

## Required interfaces

- `run_solver(project: Path, command: list[str], run_dir: Path) -> dict`: execute a configured solver with argument arrays, project-scoped cwd, timeout, captured stdout/stderr, exit code, and reproducibility metadata.
- `run_analysis(project: Path, command: list[str], run_dir: Path) -> dict`: execute analysis after solver success, preserve logs and generated files, and return structured status.
- `collect_outputs(run_dir: Path) -> dict`: inventory outputs with relative paths, hashes, sizes, and provenance.

## Acceptance requirements

1. Follow TDD: RED tests first, then implementation and refactor; write `task-6-report.md` with exact results.
2. Commands must use argument arrays and project-scoped working directories; reject path escapes and unsafe command forms where required by config.
3. Run records must be append-only and identify solver/analysis commands, timestamps, input/config hashes, exit codes, timeout status, stdout/stderr paths, and output inventories.
4. Nonzero exits, missing commands, timeouts, malformed command configs, and analysis-after-solver-failure must return structured failures and retain diagnostics.
5. Output collection must be deterministic, project-contained, hash-addressed, and must not follow outputs outside the run/project root.
6. CLI `build PROJECT --json` must invoke the configured solver then analysis in order, update the run manifest/stages, and write a machine-readable build report without touching later figure registries.
7. Add tests for success order, failure short-circuit, timeout, missing command, path escape, output hashing/provenance, append-only runs, and CLI integration.
8. Run focused and complete suites; preserve only the known Windows symlink-permission skip.
