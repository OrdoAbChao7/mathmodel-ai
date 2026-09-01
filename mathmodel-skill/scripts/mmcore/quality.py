"""Quality scoring for mathmodel evidence-contract checks."""

from __future__ import annotations

from typing import Any


DIMENSION_WEIGHTS = {
    "problem_coverage": 10,
    "data_traceability": 10,
    "model_rigor": 20,
    "validation_robustness": 20,
    "result_claim_evidence": 15,
    "body_expression": 10,
    "figures": 10,
    "latex": 5,
}

RULE_DIMENSIONS = {
    "ARTIFACT-FILE-001": "data_traceability",
    "ARTIFACT-JSON-001": "data_traceability",
    "ARTIFACT-SHAPE-001": "data_traceability",
    "ARTIFACT-ID-001": "data_traceability",
    "EVIDENCE-QUESTION-SUPPORT-001": "problem_coverage",
    "EVIDENCE-QUESTION-001": "problem_coverage",
    "EVIDENCE-MODEL-001": "model_rigor",
    "EVIDENCE-CLAIM-SUPPORT-001": "result_claim_evidence",
    "EVIDENCE-CLAIM-001": "result_claim_evidence",
    "EVIDENCE-FIGURE-001": "result_claim_evidence",
    "EVIDENCE-VALIDATION-001": "validation_robustness",
    "EVIDENCE-RESULT-PATH-001": "result_claim_evidence",
    "EVIDENCE-RESULT-SOURCE-001": "result_claim_evidence",
    "FIGURE-PATH-001": "figures",
    "FIGURE-FILE-001": "figures",
    "FIGURE-ROLE-001": "figures",
    "VALIDATION-STATUS-001": "validation_robustness",
}

OFFICIAL_JUDGE_WEIGHTS = {
    "modeling_reasonableness": 30,
    "modeling_creativity": 20,
    "result_correctness_trust": 30,
    "communication_clarity": 20,
}

_OFFICIAL_COMPONENTS = {
    "modeling_reasonableness": ("problem_coverage", "model_rigor"),
    # Creativity is intentionally not inferred from algorithm names or prose.
    # It becomes assessed only when a future innovation-specific assessment is
    # supplied by the governed review layer.
    "modeling_creativity": (),
    "result_correctness_trust": ("validation_robustness", "result_claim_evidence"),
    "communication_clarity": ("body_expression", "figures", "latex"),
}


def _machine_score(checks: list[dict[str, Any]], dimension: str, weight: int) -> tuple[int, str]:
    relevant = [check for check in checks if RULE_DIMENSIONS.get(check.get("rule")) == dimension]
    if not relevant:
        return 0, "UNASSESSED"
    passed = sum(1 for check in relevant if check.get("status") == "PASS")
    return round(weight * passed / len(relevant)), "ASSESSED"


def _validate_manual(manual: Any) -> tuple[dict[str, int], list[str], str]:
    if manual is None:
        return {}, [], "PENDING"
    if not isinstance(manual, dict):
        return {}, [f"manual scores must be an object, got {type(manual).__name__}"], "INVALID"
    if not manual:
        return {}, [], "PENDING"
    scores: dict[str, int] = {}
    errors: list[str] = []
    for name, value in manual.items():
        if name not in DIMENSION_WEIGHTS:
            errors.append(f"unknown manual score dimension: {name}")
            continue
        if isinstance(value, bool) or not isinstance(value, int):
            errors.append(f"{name} must be an integer score")
            continue
        if not 0 <= value <= DIMENSION_WEIGHTS[name]:
            errors.append(f"{name} must be between 0 and {DIMENSION_WEIGHTS[name]}")
            continue
        scores[name] = value
    if errors:
        return scores, errors, "INVALID"
    if set(scores) == set(DIMENSION_WEIGHTS):
        return scores, [], "COMPLETE"
    return scores, [], "PENDING"


def _official_judge_view(dimensions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    official: dict[str, dict[str, Any]] = {}
    for name, weight in OFFICIAL_JUDGE_WEIGHTS.items():
        components = _OFFICIAL_COMPONENTS[name]
        component_details = [dimensions[item] for item in components]
        assessed = bool(component_details) and all(item.get("assessment_status") != "UNASSESSED" for item in component_details)
        if assessed:
            raw_score = sum(item["score"] for item in component_details)
            raw_weight = sum(item["weight"] for item in component_details)
            score = round(weight * raw_score / raw_weight) if raw_weight else 0
            status = "ASSESSED"
        else:
            score = 0
            status = "UNASSESSED"
        official[name] = {"score": score, "weight": weight, "assessment_status": status, "components": list(components)}
    return {
        "dimensions": official,
        "weights": OFFICIAL_JUDGE_WEIGHTS,
        "total": sum(item["score"] for item in official.values()),
        "assessment_status": "ASSESSED" if all(item["assessment_status"] == "ASSESSED" for item in official.values()) else "UNASSESSED",
    }


def score_quality(checks: list[dict[str, Any]], manual: dict | None = None) -> dict[str, Any]:
    """Return dimension scores, weighted total, hard failures, and release status."""
    manual_scores, manual_errors, manual_review = _validate_manual(manual)
    dimensions: dict[str, dict[str, Any]] = {}
    unassessed_dimensions: list[str] = []
    for dimension, weight in DIMENSION_WEIGHTS.items():
        if dimension in manual_scores:
            score = manual_scores[dimension]
            source = "manual"
            assessment_status = "HUMAN_ASSESSED"
        else:
            score, assessment_status = _machine_score(checks, dimension, weight)
            source = "machine"
            if assessment_status == "UNASSESSED":
                unassessed_dimensions.append(dimension)
        score = max(0, min(weight, score))
        dimensions[dimension] = {
            "score": score,
            "weight": weight,
            "source": source,
            "assessment_status": assessment_status,
        }

    hard_failures = [
        check
        for check in checks
        if check.get("severity") == "FAIL" and check.get("status") == "FAIL"
    ]
    total = sum(dimension["score"] for dimension in dimensions.values())
    official_judge_view = _official_judge_view(dimensions)
    if manual_errors:
        release_status = "FAIL"
    elif hard_failures:
        release_status = "FAIL"
    elif unassessed_dimensions:
        release_status = "PENDING_MANUAL_REVIEW"
    elif manual_review == "PENDING":
        release_status = "PENDING_MANUAL_REVIEW"
    elif total >= 85:
        release_status = "PASS"
    else:
        release_status = "FAIL"

    return {
        "dimensions": dimensions,
        "weights": DIMENSION_WEIGHTS,
        "total": total,
        "hard_failures": hard_failures,
        "manual_review": manual_review,
        "manual_errors": manual_errors,
        "unassessed_dimensions": unassessed_dimensions,
        "release_status": release_status,
        "official_judge_view": official_judge_view,
    }
