"""Additional evidence gates for the CUMCM competition_max execution mode."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .schema import supported_artifact_schema


_FORMAL_MAX = "competition_max"
_DEFAULT_REQUIREMENTS = {
    "minimum_model_scouts": 2,
    "minimum_candidate_routes_reviewed": 4,
    "minimum_red_team_rounds": 2,
}
_DEFAULT_ATTACKS = {"alternative_split", "extreme_scenario", "bootstrap"}


def _check(rule: str, status: str, message: str, **evidence: Any) -> dict[str, Any]:
    return {"rule": rule, "status": status, "message": message, "evidence": evidence}


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _requirements() -> tuple[dict[str, int], set[str], str]:
    path = Path(__file__).resolve().parents[2] / "profiles" / "cumcm" / "profile.yaml"
    try:
        profile = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        profile = {}
    section = profile.get("competition_max", {}) if isinstance(profile, dict) else {}
    requirements = {
        key: int(section.get(key, default))
        for key, default in _DEFAULT_REQUIREMENTS.items()
    }
    attacks = section.get("required_robustness_attacks", sorted(_DEFAULT_ATTACKS))
    required_attacks = {item for item in attacks if isinstance(item, str)} if isinstance(attacks, list) else set(_DEFAULT_ATTACKS)
    provider = section.get("required_external_review_provider", "ars")
    return requirements, required_attacks or set(_DEFAULT_ATTACKS), provider if isinstance(provider, str) else "ars"


def evaluate_max_rigor(project: Path, config: dict[str, Any]) -> dict[str, Any]:
    """Require the extra robustness/red-team/ARS evidence promised by max mode."""
    mode = config.get("execution_mode", "research_autonomous") if isinstance(config, dict) else None
    if mode != _FORMAL_MAX:
        return {"status": "NOT_APPLICABLE", "mode": mode, "checks": []}
    root = Path(project).resolve()
    requirements, required_attacks, required_provider = _requirements()
    path = root / "artifacts" / "competition-max-review.json"
    checks: list[dict[str, Any]] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {"status": "FAIL", "mode": mode, "checks": [_check("G8-MAX-EVIDENCE-001", "FAIL", "competition-max-review.json is required", error=str(exc))]}
    if not supported_artifact_schema(data) or not _text(data.get("generated_by")):
        checks.append(_check("G8-MAX-SHAPE-001", "FAIL", "max-rigor artifact metadata is invalid"))
    numeric_requirements = {
        "model_scouts": requirements["minimum_model_scouts"],
        "candidate_routes_reviewed": requirements["minimum_candidate_routes_reviewed"],
        "red_team_rounds": requirements["minimum_red_team_rounds"],
    }
    for field, minimum in numeric_requirements.items():
        value = data.get(field)
        ok = isinstance(value, int) and not isinstance(value, bool) and value >= minimum
        checks.append(_check("G8-MAX-DEPTH-001", "PASS" if ok else "FAIL", f"{field} meets max-mode minimum" if ok else f"{field} is below max-mode minimum", field=field, actual=value, minimum=minimum))
    attacks = data.get("robustness_attacks")
    attack_ok = isinstance(attacks, list) and required_attacks <= {item for item in attacks if isinstance(item, str)}
    checks.append(_check("G8-MAX-ROBUSTNESS-001", "PASS" if attack_ok else "FAIL", "extended robustness attacks are recorded" if attack_ok else "max mode lacks required robustness attacks", required=sorted(required_attacks), actual=attacks))
    reviews = data.get("external_reviews")
    ars = [item for item in reviews if isinstance(item, dict) and item.get("provider") == required_provider] if isinstance(reviews, list) else []
    ars_ok = bool(ars) and all(item.get("status") == "COMPLETE" and _text(item.get("evidence")) for item in ars)
    checks.append(_check("G8-MAX-ARS-001", "PASS" if ars_ok else "FAIL", "ARS external review is complete and referenced" if ars_ok else "max mode requires a completed ARS review reference"))
    status = "PASS" if checks and all(item["status"] == "PASS" for item in checks) else "FAIL"
    return {"status": status, "mode": mode, "requirements": numeric_requirements, "checks": checks}
