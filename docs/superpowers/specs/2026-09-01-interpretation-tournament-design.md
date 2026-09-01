# Interpretation Tournament Design

## Goal

Add a deterministic, profile-driven interpretation tournament that turns independent problem readings into auditable evidence and prevents unresolved semantic conflicts from entering formal CUMCM modeling.

## Scope

This phase adds G1 only. It does not generate model candidates, call external models, lock experiment results, or add a unified orchestrator. Existing v1 artifacts and research-mode fixtures remain readable.

## Artifacts

`artifacts/interpretation-candidates.json` contains an object with `schema_version`, `problem_id`, and a non-empty `candidates` array. Every candidate has a unique `interpreter_id`, `independence_note`, and arrays for `questions`, `objectives`, `decision_variables`, `hard_constraints`, `implicit_constraints`, `outputs`, `dependencies`, and `ambiguities`.

`artifacts/interpretation-conflicts.json` is machine-produced evidence with `schema_version`, `generated_by`, `candidate_ids`, and `conflicts`. Each conflict has a stable `id`, `dimension`, `severity` (`MAJOR` or `MINOR`), `candidate_ids`, `description`, and `resolution_status` (`OPEN` or `RESOLVED`). A supplied `computed_status` is ignored when determining G1.

The existing `artifacts/problem-map.json` remains the canonical downstream map. It must contain a non-empty `questions` array, and each question must have an `id` and `dependencies` array. G1 does not rewrite it.

## Machine rules

The profile supplies `minimum_independent_interpretations` and `major_conflict_dimensions`. The local evaluator:

1. validates candidate shape and unique IDs;
2. compares normalized values for each configured conflict dimension;
3. treats disagreement in objectives, decision variables, hard constraints, outputs, or dependencies as a major conflict;
4. requires every major conflict to be explicitly resolved;
5. validates the conflict artifact against the recomputed conflicts and rejects stale or fabricated evidence;
6. requires a complete problem map;
7. requires an H1 signoff whose reviewed artifacts include all three interpretation artifacts.

G1 is `PASS` only when every required check passes. Missing or malformed evidence is `UNASSESSED` at the individual-check level and makes the gate fail. Open major conflicts produce `BLOCKED_INTERPRETATION_CONFLICT` and make the gate fail.

## Integration

Formal execution modes add `G1-PROBLEM-INTERPRETATION-001` to audit/build page gates and expose the G1 report in `quality-report.json`. Research mode records `NOT_APPLICABLE` and preserves existing behavior. Package blocks a formal report unless its G1 status is `PASS`.

## Security and provenance

All artifact paths are project-relative references. The evaluator never executes candidate content and never treats an agent-provided PASS field as authoritative. The evaluator records its rule version and source profile in the result.

## Test strategy

Tests cover insufficient candidates, malformed candidates, major conflict blocking, unresolved-vs-resolved conflict behavior, fabricated machine status, missing H1 linkage, valid formal G1, research compatibility, and package fail-closed behavior.
