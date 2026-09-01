# Model Tournament Design

## Goal

Add a local, deterministic model-search gate that requires a baseline, genuinely different model routes, risk probes, complexity justification, and an auditable human-owned selection.

## Scope

This phase implements G2 (`MODEL_SEARCH_COMPLETE`) and G3 (`MODEL_JUSTIFIED_AND_SELECTED`). It does not run solvers, compare numerical metrics, freeze evidence, or invoke external model providers. Existing v1 projects and research-mode fixtures remain compatible.

## Artifacts

`artifacts/candidate-registry.json` contains `schema_version`, `problem_id`, and a non-empty `candidates` array. Each candidate has a unique `id`, `question_id`, `role` (`baseline` or `candidate`), `conceptual_family`, `assumption_family`, `optimization_or_inference_structure`, `method_card_id`, `simpler_alternative`, `why_simpler_is_insufficient`, `complexity_cost`, and `expected_gain`.

`artifacts/method-cards.json` contains `schema_version` and `cards`. Each card records `id`, `family`, `suitable_when`, `danger_when`, `required_validation`, `common_failure_modes`, `simpler_alternatives`, `complexity_cost`, and `interpretability`.

`artifacts/risk-probe.json` contains `schema_version`, `generated_by`, and `probes`. Every candidate has one probe with the fields `assumption_fit`, `data_sufficiency`, `data_quality`, `implementation_feasibility`, `solver_availability`, `runtime_feasibility`, `parameter_identifiability`, `output_degeneracy`, `leakage_risk`, `sensitivity_risk`, `validation_feasibility`, and `baseline_plausibility`. Values are explicit statuses or evidence notes, not a single agent-authored PASS.

`artifacts/decision-ledger.jsonl` is append-only evidence. Each entry has `id`, `candidate_id`, `decision` (`SELECTED` or `REJECTED`), `reason`, `timestamp`, and `reviewed_artifacts`. Rejected candidates require a non-empty reason. Exactly one current candidate may be selected.

## Profile-driven policy

The CUMCM profile supplies the minimum total candidates, minimum non-baseline conceptual routes, maximum route count, and risk fields. Python contains only safe defaults for legacy profiles; active profile values are authoritative.

## G2 rules

G2 passes only if the candidate registry and method-card registry are valid, one baseline exists, the configured candidate minimum is met, non-baseline conceptual route signatures are distinct, every candidate has a complete risk probe, and no probe contains a `CRITICAL` risk status. RF/XGBoost/LightGBM variants with the same route signature count as one route.

## G3 rules

G3 passes only if G2 passes, exactly one candidate is selected in the decision ledger, every other candidate has a rejection reason, every non-baseline candidate justifies why its simpler alternative is insufficient, all method-card links resolve, and H2 signoff explicitly reviews candidate registry, method cards, risk probes, and decision ledger. A supplied ledger status is never authoritative.

## Integration

Formal execution modes add G2 and G3 page gates to audit/build and expose both reports in `quality-report.json`. Package requires both statuses to be `PASS` for formal modes. Research mode records `NOT_APPLICABLE` and keeps v1 behavior.

## Testing

Tests cover missing baseline, insufficient candidates, conceptual deduplication, incomplete/critical risk probes, invalid method-card links, multiple/no selections, missing rejection reasons, missing H2 linkage, forged statuses, research compatibility, and formal package fail-closed behavior.
