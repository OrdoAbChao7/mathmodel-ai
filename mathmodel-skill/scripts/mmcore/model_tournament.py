"""Deterministic model-search, risk-probe, and selection gates (G2/G3)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

_CANDIDATE_REQUIRED = (
    "id", "question_id", "role", "conceptual_family", "assumption_family",
    "optimization_or_inference_structure", "method_card_id", "simpler_alternative",
    "why_simpler_is_insufficient", "complexity_cost", "expected_gain",
)
_CARD_REQUIRED = (
    "id", "family", "suitable_when", "danger_when", "required_validation",
    "common_failure_modes", "simpler_alternatives", "complexity_cost", "interpretability",
)
_DEFAULT_RISK_FIELDS = (
    "assumption_fit", "data_sufficiency", "data_quality", "implementation_feasibility",
    "solver_availability", "runtime_feasibility", "parameter_identifiability",
    "output_degeneracy", "leakage_risk", "sensitivity_risk", "validation_feasibility",
    "baseline_plausibility",
)
_H2_ARTIFACTS = {
    "artifacts/candidate-registry.json", "artifacts/method-cards.json",
    "artifacts/risk-probe.json", "artifacts/decision-ledger.jsonl",
}


def _profile() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[2] / "profiles" / "cumcm" / "profile.yaml"
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return {}
    return value if isinstance(value, dict) else {}


def _check(rule: str, status: str, message: str, **evidence: Any) -> dict[str, Any]:
    return {"rule": rule, "status": status, "message": message, "evidence": evidence}


def _read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.is_file():
        return None, "missing artifact"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, f"invalid JSON: {exc}"
    if not isinstance(value, dict):
        return None, "artifact root must be an object"
    return value, None


def _read_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    if not path.is_file():
        return [], ["ledger file is missing"]
    rows, errors = [], []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        return [], [str(exc)]
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {number}: {exc.msg}")
            continue
        if isinstance(value, dict):
            rows.append(value)
        else:
            errors.append(f"line {number}: record must be an object")
    return rows, errors


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _load_candidates(project: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    checks, candidates, errors = [], [], []
    data, error = _read_json(project / "artifacts" / "candidate-registry.json")
    if error:
        return [], [_check("G2-CANDIDATE-EVIDENCE-001", "UNASSESSED", "candidate registry is unavailable", error=error)], []
    if data.get("schema_version") != 1 or not _text(data.get("problem_id")):
        checks.append(_check("G2-ARTIFACT-METADATA-001", "FAIL", "candidate registry metadata is missing or invalid"))
    raw = data.get("candidates")
    if not isinstance(raw, list):
        return [], checks + [_check("G2-CANDIDATE-SHAPE-001", "UNASSESSED", "candidate registry must contain a candidates array")], []
    seen: set[str] = set()
    for item in raw:
        identifier = item.get("id") if isinstance(item, dict) else None
        missing = [field for field in _CANDIDATE_REQUIRED if not isinstance(item, dict) or field not in item]
        if not isinstance(identifier, str) or not identifier.strip() or identifier in seen or missing:
            checks.append(_check("G2-CANDIDATE-SHAPE-001", "FAIL", "candidate record is malformed or duplicated", id=identifier, missing=missing))
            continue
        text_fields = _CANDIDATE_REQUIRED[2:]
        if any(not _text(item.get(field)) for field in text_fields) or item.get("role") not in {"baseline", "candidate"}:
            checks.append(_check("G2-CANDIDATE-SHAPE-001", "FAIL", "candidate fields have invalid types or role", id=identifier))
            continue
        seen.add(identifier)
        candidates.append(item)
    return candidates, checks, errors


def _load_cards(project: Path, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    checks = []
    data, error = _read_json(project / "artifacts" / "method-cards.json")
    if error:
        return [_check("G2-METHOD-CARD-EVIDENCE-001", "UNASSESSED", "method-card registry is unavailable", error=error)]
    if data.get("schema_version") != 1:
        checks.append(_check("G2-ARTIFACT-METADATA-001", "FAIL", "method-card metadata is missing or invalid"))
    raw = data.get("cards")
    if not isinstance(raw, list):
        return checks + [_check("G2-METHOD-CARD-SHAPE-001", "UNASSESSED", "method-card registry must contain cards")]
    cards = {}
    for item in raw:
        identifier = item.get("id") if isinstance(item, dict) else None
        if not isinstance(item, dict) or not isinstance(identifier, str) or not identifier.strip() or identifier in cards:
            checks.append(_check("G2-METHOD-CARD-SHAPE-001", "FAIL", "method-card record is malformed or duplicated", id=identifier))
            continue
        missing = [field for field in _CARD_REQUIRED if field not in item]
        list_fields = _CARD_REQUIRED[2:6] + ("simpler_alternatives",)
        text_fields = ("family", "complexity_cost", "interpretability")
        if missing or any(not isinstance(item[field], list) for field in list_fields) or any(not _text(item.get(field)) for field in text_fields):
            checks.append(_check("G2-METHOD-CARD-SHAPE-001", "FAIL", "method-card record is incomplete", id=identifier, missing=missing))
            continue
        cards[identifier] = item
    missing_links = sorted({item["method_card_id"] for item in candidates if item["method_card_id"] not in cards})
    if missing_links:
        checks.append(_check("G2-METHOD-CARD-LINK-001", "FAIL", "candidate method-card links do not resolve", missing=missing_links))
    elif candidates:
        checks.append(_check("G2-METHOD-CARD-LINK-001", "PASS", "all candidate method-card links resolve", count=len(candidates)))
    return checks


def _risk_checks(project: Path, candidates: list[dict[str, Any]], fields: tuple[str, ...]) -> list[dict[str, Any]]:
    checks = []
    data, error = _read_json(project / "artifacts" / "risk-probe.json")
    if error:
        return [_check("G2-RISK-EVIDENCE-001", "UNASSESSED", "risk-probe evidence is unavailable", error=error)]
    if data.get("schema_version") != 1 or not _text(data.get("generated_by")):
        checks.append(_check("G2-ARTIFACT-METADATA-001", "FAIL", "risk-probe metadata is missing or invalid"))
    raw = data.get("probes")
    if not isinstance(raw, list):
        return checks + [_check("G2-RISK-SHAPE-001", "UNASSESSED", "risk-probe artifact must contain probes")]
    by_id: dict[str, dict[str, Any]] = {}
    for item in raw:
        identifier = item.get("candidate_id") if isinstance(item, dict) else None
        if not isinstance(identifier, str) or not identifier.strip() or identifier in by_id:
            checks.append(_check("G2-RISK-SHAPE-001", "FAIL", "risk probe has malformed or duplicate candidate ID", id=identifier))
            continue
        by_id[identifier] = item
    candidate_ids = {item["id"] for item in candidates}
    if set(by_id) != candidate_ids:
        checks.append(_check("G2-RISK-COVERAGE-001", "FAIL", "risk probes do not cover exactly the candidate set", expected=sorted(candidate_ids), actual=sorted(by_id)))
    critical = []
    for identifier in sorted(candidate_ids):
        probe = by_id.get(identifier)
        missing = [field for field in fields if not isinstance(probe, dict) or field not in probe]
        invalid = []
        if not missing:
            for field in fields:
                value = probe[field]
                if not isinstance(value, dict) or value.get("status") not in {"PASS", "WARN", "FAIL", "CRITICAL"} or not _text(value.get("evidence")):
                    invalid.append(field)
                if isinstance(value, dict) and value.get("status") == "CRITICAL":
                    critical.append(f"{identifier}:{field}")
        if missing or invalid:
            checks.append(_check("G2-RISK-SHAPE-001", "FAIL", "risk probe is incomplete or invalid", candidate_id=identifier, missing=missing, invalid=invalid))
    if critical:
        checks.append(_check("G2-RISK-001", "FAIL", "critical risks block model search", critical=critical))
    elif candidates and not any(check["rule"] == "G2-RISK-COVERAGE-001" for check in checks):
        checks.append(_check("G2-RISK-001", "PASS", "risk probes are complete with no critical findings", candidates=len(candidates)))
    return checks


def _g2_checks(project: Path, profile: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    candidates, checks, _ = _load_candidates(project)
    minimum = int(profile.get("model_tournament", {}).get("minimum_total_candidates", 4))
    minimum_routes = int(profile.get("model_tournament", {}).get("minimum_non_baseline_routes", 3))
    if len(candidates) < minimum:
        checks.append(_check("G2-CANDIDATE-COVERAGE-001", "FAIL", "minimum candidate count is not met", actual=len(candidates), minimum=minimum))
    elif candidates:
        checks.append(_check("G2-CANDIDATE-COVERAGE-001", "PASS", "minimum candidate count is met", actual=len(candidates), minimum=minimum))
    baselines = [item for item in candidates if item.get("role") == "baseline"]
    if len(baselines) != 1:
        checks.append(_check("G2-BASELINE-001", "FAIL", "exactly one baseline candidate is required", count=len(baselines)))
    else:
        checks.append(_check("G2-BASELINE-001", "PASS", "one baseline candidate exists", candidate_id=baselines[0]["id"]))
    routes = {(
        item.get("conceptual_family"), item.get("assumption_family"), item.get("optimization_or_inference_structure")
    ) for item in candidates if item.get("role") == "candidate"}
    if len(routes) < minimum_routes:
        checks.append(_check("G2-DIVERSITY-001", "FAIL", "minimum conceptual route diversity is not met", actual=len(routes), minimum=minimum_routes))
    else:
        checks.append(_check("G2-DIVERSITY-001", "PASS", "conceptual route diversity is met", actual=len(routes), minimum=minimum_routes))
    maximum_routes = int(profile.get("model_tournament", {}).get("maximum_non_baseline_routes", 5))
    if len(routes) > maximum_routes:
        checks.append(_check("G2-DIVERSITY-002", "WARN", "candidate routes exceed the profile review budget", actual=len(routes), maximum=maximum_routes))
    checks.extend(_load_cards(project, candidates))
    risk_fields = tuple(profile.get("model_tournament", {}).get("risk_fields", _DEFAULT_RISK_FIELDS))
    checks.extend(_risk_checks(project, candidates, risk_fields))
    return checks, candidates


def _decision_checks(project: Path, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    checks = []
    rows, errors = _read_jsonl(project / "artifacts" / "decision-ledger.jsonl")
    if errors:
        checks.append(_check("G3-DECISION-JSONL-001", "FAIL", "decision ledger is malformed or missing", errors=errors))
    latest: dict[str, dict[str, Any]] = {}
    seen_record_ids: set[str] = set()
    for row in rows:
        identifier = row.get("candidate_id")
        missing = [field for field in ("id", "candidate_id", "decision", "reason", "timestamp", "reviewed_artifacts") if field not in row]
        record_id = row.get("id")
        if _text(record_id) and record_id in seen_record_ids:
            checks.append(_check("G3-DECISION-JSONL-001", "FAIL", "decision ledger record IDs must be unique", id=record_id))
            continue
        if _text(record_id):
            seen_record_ids.add(record_id)
        artifacts = row.get("reviewed_artifacts")
        if missing or not isinstance(identifier, str) or row.get("decision") not in {"SELECTED", "REJECTED"} or not _text(record_id) or not _text(row.get("reason")) or not _text(row.get("timestamp")) or not isinstance(artifacts, list) or not artifacts or any(not isinstance(item, str) or not item.strip() for item in artifacts):
            checks.append(_check("G3-DECISION-001", "FAIL", "decision record is incomplete or invalid", id=row.get("id"), missing=missing))
            continue
        latest[identifier] = row
    candidate_ids = {item["id"] for item in candidates}
    selected = [identifier for identifier, row in latest.items() if identifier in candidate_ids and row["decision"] == "SELECTED"]
    if len(selected) != 1:
        checks.append(_check("G3-SELECTION-001", "FAIL", "exactly one current selected candidate is required", selected=selected))
    else:
        checks.append(_check("G3-SELECTION-001", "PASS", "exactly one current selected candidate exists", selected=selected[0]))
    unknown = sorted(set(latest) - candidate_ids)
    if unknown:
        checks.append(_check("G3-DECISION-001", "FAIL", "decision ledger references unknown candidates", unknown=unknown))
    missing_rejections = sorted(identifier for identifier in candidate_ids if identifier not in latest or latest[identifier]["decision"] != "SELECTED" and latest[identifier]["decision"] != "REJECTED")
    if missing_rejections:
        checks.append(_check("G3-DECISION-001", "FAIL", "every non-selected candidate needs a rejection reason", missing=missing_rejections))
    return checks


def _complexity_checks(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    missing = [item["id"] for item in candidates if item.get("role") != "baseline" and (not _text(item.get("simpler_alternative")) or not _text(item.get("why_simpler_is_insufficient")) or not _text(item.get("complexity_cost")) or not _text(item.get("expected_gain")))]
    if missing:
        return [_check("G3-COMPLEXITY-001", "FAIL", "complexity justification is incomplete", candidates=missing)]
    return [_check("G3-COMPLEXITY-001", "PASS", "all non-baseline candidates justify complexity")]


def _h2_check(project: Path) -> dict[str, Any]:
    rows, errors = _read_jsonl(project / "artifacts" / "human-review-ledger.jsonl")
    for row in rows:
        reviewed = row.get("reviewed_artifacts")
        if row.get("gate") == "H2_METHOD_SELECTION" and row.get("decision") == "APPROVED" and isinstance(reviewed, list) and _H2_ARTIFACTS <= {item.replace("\\", "/") for item in reviewed if isinstance(item, str)}:
            return _check("G3-H2-LINK-001", "PASS", "H2 signoff covers model-search evidence", review_id=row.get("id"))
    return _check("G3-H2-LINK-001", "FAIL", "H2 signoff does not cover model-search evidence", ledger_errors=errors)


def evaluate_model_tournament(project: Path, config: dict[str, Any]) -> dict[str, Any]:
    """Evaluate G2 and G3; formal modes fail closed, research mode is N/A."""
    profile = _profile()
    mode = config.get("execution_mode", "research_autonomous")
    if mode not in set(profile.get("formal_modes", ("competition_assisted", "competition_max"))):
        return {"status": "NOT_APPLICABLE", "mode": mode, "g2": {"status": "NOT_APPLICABLE", "checks": []}, "g3": {"status": "NOT_APPLICABLE", "checks": []}}
    g2_checks, candidates = _g2_checks(Path(project), profile)
    g2_status = "PASS" if g2_checks and all(check["status"] == "PASS" for check in g2_checks) else "FAIL"
    g3_checks = []
    if g2_status != "PASS":
        g3_checks.append(_check("G3-PREREQUISITE-001", "FAIL", "G3 requires G2 to pass"))
    g3_checks.extend(_decision_checks(Path(project), candidates))
    g3_checks.extend(_complexity_checks(candidates))
    g3_checks.append(_h2_check(Path(project)))
    g3_status = "PASS" if g2_status == "PASS" and g3_checks and all(check["status"] == "PASS" for check in g3_checks) else "FAIL"
    return {
        "status": "PASS" if g2_status == "PASS" and g3_status == "PASS" else "FAIL",
        "mode": mode,
        "profile": profile.get("profile_id"),
        "rule_version": profile.get("rule_version"),
        "g2": {"status": g2_status, "checks": g2_checks, "candidate_ids": [item["id"] for item in candidates]},
        "g3": {"status": g3_status, "checks": g3_checks},
    }
