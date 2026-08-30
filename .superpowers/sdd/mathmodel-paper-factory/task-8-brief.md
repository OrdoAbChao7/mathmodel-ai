# Task 8 brief — Deterministic end-to-end problem-type fixtures

## Scope

Implement only Task 8 from `docs/superpowers/plans/2026-08-30-mathmodel-paper-factory.md`. Read plan/spec, current Skill and references, and existing CLI APIs. Do not redesign the framework or modify `traning1/` unless strictly required for adapter integration.

## Owned files

- Create `mathmodel-skill/tests/fixtures/optimization/`
- Create `mathmodel-skill/tests/fixtures/forecasting/`
- Create `mathmodel-skill/tests/fixtures/evaluation/`
- Create `mathmodel-skill/tests/test_end_to_end.py`
- Modify `traning1/` only if a minimal adapter integration is required; document every such change.

## Required interface

- `run_fixture(path: Path) -> dict`: execute inspect → analyze → validate → compile → audit and return report paths/status.

## Acceptance requirements

1. Follow TDD: write failing end-to-end tests first, then fixtures/orchestration, and write `task-8-report.md` with exact results.
2. Each fixture contains `mathmodel.json`, raw input, deterministic `analysis/run.py`, all seven registries, minimal LaTeX with executable boundary labels, role-complete figure files, traceable claims, validation evidence, and a compileable PDF path or controlled mock compiler path.
3. Optimization fixture: small hand-checkable optimization with objective/constraints and result evidence.
4. Forecasting fixture: time-ordered linear forecast with holdout validation and explicit forecast claims.
5. Evaluation fixture: multi-criteria weighted evaluation with weights, scores, and traceable result/validation claims.
6. `run_fixture` performs the complete inspect → analyze → validate → compile → audit flow; all three fixtures PASS and have distinct result hashes.
7. Two-repeat reproducibility check compares result content, registry files, PDF text/content hash, and figure source hashes; only timestamps/run IDs may differ.
8. Tests must fail closed on unsupported claims, missing registry links, and tampered outputs. Keep all fixture data small, deterministic, hand-checkable, and non-production.
9. Run focused and complete suites; preserve only the known Windows symlink-permission skip. Record unavailable external compiler behavior explicitly and use a deterministic local fake compiler only if the existing CLI contract allows it.
