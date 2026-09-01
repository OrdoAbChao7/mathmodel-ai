"""Evidence-constrained paper writing (G7) and adversarial review (G8)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_FORMAL_MODES = {"competition_assisted", "competition_max"}
_STRONG_TERMS = ("最优", "显著", "准确", "稳定", "鲁棒", "优于", "提升", "有效", "最佳", "可靠", "optimal", "significant", "robust")
_COMPARISON_TERMS = ("优于", "提升", "improve", "better", "superior")
_REVIEW_TYPES = ("mathematical", "statistical", "evidence_consistency", "red_team", "citation", "judge_view", "final_judge")
_JUDGE_ANSWERS = ("problem", "method", "innovation", "result", "trust", "risk")


def _check(rule: str, status: str, message: str, **evidence: Any) -> dict[str, Any]:
    return {"rule": rule, "status": status, "message": message, "evidence": evidence}


def _read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, str(exc)
    return (value, None) if isinstance(value, dict) else (None, "artifact root must be an object")


def _items(value: Any, field: str) -> tuple[list[dict[str, Any]], bool]:
    raw = value.get(field) if isinstance(value, dict) else None
    if not isinstance(raw, list) or not raw or any(not isinstance(item, dict) for item in raw):
        return [], False
    return raw, True


def _safe_path(root: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    candidate = Path(value)
    if candidate.is_absolute():
        return None
    resolved = (root / candidate).resolve()
    if resolved != root and root not in resolved.parents:
        return None
    return resolved if resolved.is_file() else None


def _formal(config: dict[str, Any]) -> tuple[str, str | None]:
    if not isinstance(config, dict):
        return "FAIL", None
    mode = config.get("execution_mode", "research_autonomous")
    if not isinstance(mode, str) or mode not in (_FORMAL_MODES | {"research_autonomous"}):
        return "FAIL", mode if isinstance(mode, str) else None
    return ("NOT_APPLICABLE", mode) if mode == "research_autonomous" else ("FORMAL", mode)


def evaluate_writer_package(project: Path, config: dict[str, Any]) -> dict[str, Any]:
    """Check that paper writing is a translation of current evidence only."""
    mode_status, mode = _formal(config)
    if mode_status == "NOT_APPLICABLE":
        return {"status": "NOT_APPLICABLE", "mode": mode, "checks": []}
    if mode_status != "FORMAL":
        return {"status": "FAIL", "mode": mode or "INVALID", "checks": [_check("G7-CONFIG-001", "FAIL", "execution_mode is not supported")]}
    root = Path(project).resolve()
    checks: list[dict[str, Any]] = []
    package, package_error = _read_json(root / "artifacts" / "writer-package.json")
    if package_error:
        return {"status": "FAIL", "mode": mode, "checks": [_check("G7-EVIDENCE-001", "FAIL", "writer-package.json is required", error=package_error)]}
    if package.get("schema_version") != 1:
        checks.append(_check("G7-SHAPE-001", "FAIL", "writer-package schema_version must be 1"))
    source_artifacts = package.get("source_artifacts")
    required_sources = {"artifacts/problem-map.json", "artifacts/model-architecture.json", "artifacts/frozen-results.json", "artifacts/claim-registry.json", "artifacts/figure-registry.json", "artifacts/decision-ledger.json"}
    source_set = {item for item in source_artifacts if isinstance(item, str)} if isinstance(source_artifacts, list) else set()
    source_ok = isinstance(source_artifacts, list) and all(isinstance(item, str) and _safe_path(root, item) is not None for item in source_artifacts)
    if not source_ok or not required_sources <= source_set:
        checks.append(_check("G7-SOURCE-001", "FAIL", "writer package must reference all locked evidence sources", missing=sorted(required_sources - source_set)))
    else:
        checks.append(_check("G7-SOURCE-001", "PASS", "writer package references locked evidence sources"))
    claims_data, _ = _read_json(root / "artifacts" / "claim-registry.json")
    claims, claims_ok = _items(claims_data, "claims")
    results_data, _ = _read_json(root / "artifacts" / "result-registry.json")
    results, results_ok = _items(results_data, "results")
    validations_data, _ = _read_json(root / "artifacts" / "validation.json")
    validations, validations_ok = _items(validations_data, "validations")
    claim_ids = {item.get("id") for item in claims if isinstance(item.get("id"), str)}
    result_ids = {item.get("id") for item in results if isinstance(item.get("id"), str)}
    validation_ids = {item.get("id") for item in validations if isinstance(item.get("id"), str)}
    bindings, bindings_ok = _items(package, "claim_bindings")
    bound_ids = {item.get("claim_id") for item in bindings if isinstance(item.get("claim_id"), str)}
    if not claims_ok or not bindings_ok or bound_ids != claim_ids:
        checks.append(_check("UNSUPPORTED_STRONG_CLAIM", "FAIL", "every manuscript claim must bind to current result and validation evidence", missing=sorted(claim_ids - bound_ids)))
    else:
        for claim in claims:
            binding = next(item for item in bindings if item.get("claim_id") == claim.get("id"))
            body = claim.get("body", "") if isinstance(claim.get("body"), str) else ""
            result_refs, validation_refs = binding.get("result_ids"), binding.get("validation_ids")
            valid_refs = isinstance(result_refs, list) and bool(result_refs) and all(item in result_ids for item in result_refs) and isinstance(validation_refs, list) and bool(validation_refs) and all(item in validation_ids for item in validation_refs)
            comparison_required = any(term in body.lower() for term in _COMPARISON_TERMS)
            comparison_ok = not comparison_required or (isinstance(binding.get("comparison_ids"), list) and bool(binding.get("comparison_ids")))
            if any(term in body.lower() for term in _STRONG_TERMS) and (not valid_refs or not comparison_ok):
                checks.append(_check("UNSUPPORTED_STRONG_CLAIM", "FAIL", "strong claim lacks required result/validation/comparison binding", claim_id=claim.get("id")))
        if not any(item["rule"] == "UNSUPPORTED_STRONG_CLAIM" and item["status"] == "FAIL" for item in checks):
            checks.append(_check("UNSUPPORTED_STRONG_CLAIM", "PASS", "all strong claims have evidence bindings"))
    figures_data, _ = _read_json(root / "artifacts" / "figure-registry.json")
    figures, figures_ok = _items(figures_data, "figures")
    figure_bindings, figure_bindings_ok = _items(package, "figure_bindings")
    figure_map = {item.get("figure_id"): item for item in figure_bindings if isinstance(item.get("figure_id"), str)}
    figure_ids = {item.get("id") for item in figures if isinstance(item.get("id"), str)}
    figure_pass = figures_ok and figure_bindings_ok and figure_ids == set(figure_map) and len(figure_ids) == len(figures) and all(_safe_path(root, item.get("source")) is not None for item in figure_bindings)
    checks.append(_check("G7-FIGURE-001", "PASS" if figure_pass else "FAIL", "all figures resolve to canonical sources" if figure_pass else "figure evidence binding is incomplete"))
    citations = package.get("verified_citations")
    citation_pass = isinstance(citations, list) and bool(citations) and all(isinstance(item, dict) and item.get("verified") is True and isinstance(item.get("source"), str) and item.get("source").strip() for item in citations)
    checks.append(_check("G7-CITATION-001", "PASS" if citation_pass else "FAIL", "citations are verified" if citation_pass else "verified citations are missing or invalid"))
    candidates, candidates_ok = _items(package, "abstract_candidates")
    candidate_ids = {item.get("id") for item in candidates if isinstance(item.get("id"), str)}
    final_id = package.get("final_abstract_id")
    judge = package.get("judge_view")
    judge_pass = isinstance(judge, dict) and judge.get("status") == "PASS" and isinstance(judge.get("answers"), dict) and all(isinstance(judge["answers"].get(key), str) and judge["answers"].get(key).strip() for key in _JUDGE_ANSWERS)
    abstract_pass = candidates_ok and len(candidates) >= 3 and len(candidate_ids) == len(candidates) and isinstance(final_id, str) and final_id in candidate_ids and judge_pass
    checks.append(_check("G7-ABSTRACT-001", "PASS" if abstract_pass else "FAIL", "abstract tournament and judge-view test passed" if abstract_pass else "abstract tournament or judge-view test is incomplete"))
    frozen, frozen_error = _read_json(root / "artifacts/frozen-results.json")
    frozen_items, frozen_ok = _items(frozen, "results")
    frozen_ids = {item.get("result_id") for item in frozen_items if isinstance(item.get("result_id"), str)}
    freeze_pass = frozen_error is None and frozen_ok and results_ok and result_ids <= frozen_ids
    checks.append(_check("G7-FREEZE-001", "PASS" if freeze_pass else "FAIL", "manuscript result references resolve to frozen results" if freeze_pass else "manuscript results are not fully frozen"))
    status = "PASS" if checks and all(item["status"] == "PASS" for item in checks) else "FAIL"
    return {"status": status, "mode": mode, "checks": checks}


def evaluate_review_registry(project: Path, config: dict[str, Any]) -> dict[str, Any]:
    """Require independent math/statistics/evidence/red-team reviews before G8."""
    mode_status, mode = _formal(config)
    if mode_status == "NOT_APPLICABLE":
        return {"status": "NOT_APPLICABLE", "mode": mode, "checks": []}
    if mode_status != "FORMAL":
        return {"status": "FAIL", "mode": mode or "INVALID", "checks": [_check("G8-CONFIG-001", "FAIL", "execution_mode is not supported")]}
    root = Path(project).resolve()
    registry, error = _read_json(root / "artifacts" / "review-registry.json")
    reviews, valid = _items(registry, "reviews")
    checks: list[dict[str, Any]] = []
    types = {item.get("reviewer_type") for item in reviews if isinstance(item.get("reviewer_type"), str)}
    if error or not valid or types != set(_REVIEW_TYPES) or any(item.get("status") != "COMPLETE" or item.get("independent") is not True for item in reviews):
        checks.append(_check("G8-COVERAGE-001", "FAIL", "all independent reviewer types must complete", missing=sorted(set(_REVIEW_TYPES) - types)))
    else:
        checks.append(_check("G8-COVERAGE-001", "PASS", "all independent reviewer types completed"))
    open_critical = []
    for review in reviews:
        findings = review.get("findings")
        if not isinstance(findings, list) or any(not isinstance(item, dict) for item in findings):
            checks.append(_check("G8-SHAPE-001", "FAIL", "review findings must be an array of objects", review_id=review.get("id")))
            continue
        open_critical.extend(item for item in findings if item.get("severity") == "CRITICAL" and item.get("status") == "OPEN")
    checks.append(_check("G8-OPEN-CRITICAL-001", "FAIL" if open_critical else "PASS", "no OPEN CRITICAL findings" if not open_critical else "open critical findings block release", findings=open_critical))
    status = "PASS" if checks and all(item["status"] == "PASS" for item in checks) else "FAIL"
    return {"status": status, "mode": mode, "checks": checks, "open_critical": open_critical}
