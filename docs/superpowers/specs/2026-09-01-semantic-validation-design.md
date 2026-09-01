# Semantic Validation and Falsification Design

## Goal

Implement G4 (`EXPERIMENT_VERIFIED`) and G5 (`FALSIFICATION_PASSED`) so a model result cannot become authoritative merely because an artifact says `status: PASS`.

## Scope

This phase adds a deterministic validation evaluator and a falsification evidence evaluator. It does not run experiments, alter numerical result artifacts, freeze evidence, or add an orchestrator. Existing research-mode fixtures remain readable and executable.

## Machine-computed validation

Formal projects use `artifacts/validation.json` records containing `schema_version`, `id`, `question_id`, `metric`, `operator`, `threshold`, `observed`, and `evidence_source`. The evaluator computes `computed_status` from `observed`, `operator`, and `threshold`; any supplied `status` or `computed_status` is ignored. Numeric and operator types are validated, and evidence paths must remain inside the project.

Each validation also contains a `checks` object. The active CUMCM profile maps `problem_type` to required semantic checks. Each required check must have a non-empty evidence note and a machine-readable `status` of `PASS`; missing or failed checks make G4 fail. The mapping covers chronological split/leakage/baseline/metric recomputation for forecasting, solver/feasibility/constraint/objective/baseline checks for optimization, direction/normalization/weight/ranking checks for evaluation, seed/replication/convergence/interval checks for simulation, and units/boundary/parameter/calibration checks for mechanism.

## Falsification

`artifacts/falsification.json` contains `schema_version`, `generated_by`, and `attacks`. Every validation ID must have at least one attack with `id`, `validation_id`, `attack_type`, `evidence_source`, `outcome`, and `evidence_note`. The only surviving outcome is `SURVIVED`; `BROKEN` means the result was falsified and blocks G5. A supplied aggregate status is ignored. Evidence paths are project-relative and path-safe.

## Gate behavior

G4 passes only if every validation is numerically computed PASS, every required problem-type check passes, and all referenced evidence files exist. G5 passes only if G4 passes, every validation has a falsification attack, and no attack outcome is `BROKEN`. Missing or malformed evidence produces structured failure.

Formal audit/build add G4 and G5 gates; package requires both. Research mode returns `NOT_APPLICABLE` for both gates so legacy fixtures are unchanged.

## Security and provenance

No artifact content is executed. Agent-authored statuses are diagnostic only. Every failure includes a rule, evidence, and source path where available. Relative path validation rejects absolute paths and traversal outside the project.

## Tests

Tests cover forged PASS status, numeric threshold failures, invalid operators/types, missing semantic checks, path traversal, problem-type requirements, missing attacks, broken attacks, forged falsification status, malformed records, research compatibility, and audit/package integration.
