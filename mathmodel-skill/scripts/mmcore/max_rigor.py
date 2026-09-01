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
_DEFAULT_DEPTH_RECORD_FIELDS = {
    "model_scouts": "model_scout_records",
    "candidate_routes_reviewed": "candidate_route_records",
    "red_team_rounds": "red_team_round_records",
    "robustness_attacks": "robustness_attack_records",
}


def _check(rule: str, status: str, message: str, **evidence: Any) -> dict[str, Any]:
    return {"rule": rule, "status": status, "message": message, "evidence": evidence}


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _safe_existing_file(root: Path, value: Any) -> Path | None:
    """Resolve only project-relative evidence that exists as a regular file."""
    if not _text(value):
        return None
    candidate = Path(value)
    if candidate.is_absolute():
        return None
    resolved = (root / candidate).resolve()
    if resolved == root or root not in resolved.parents or not resolved.is_file():
        return None
    return resolved


def _record_count(data: dict[str, Any], field: str) -> int | None:
    records = data.get(field)
    if not isinstance(records, list) or not records or any(not isinstance(item, dict) or not _text(item.get("id")) for item in records):
        return None
    identifiers = [item["id"] for item in records]
    return len(records) if len(identifiers) == len(set(identifiers)) else None


def _record_types(data: dict[str, Any], field: str) -> set[str] | None:
    records = data.get(field)
    if not isinstance(records, list) or not records:
        return None
    identifiers: list[str] = []
    types: list[str] = []
    for item in records:
        if not isinstance(item, dict) or not _text(item.get("id")) or not _text(item.get("attack_type")):
            return None
        identifiers.append(item["id"])
        types.append(item["attack_type"])
    if len(identifiers) != len(set(identifiers)):
        return None
    return set(types)


def _requirements() -> tuple[dict[str, int], set[str], str, dict[str, str]]:
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
    configured_fields = section.get("depth_record_fields", {})
    depth_record_fields = dict(_DEFAULT_DEPTH_RECORD_FIELDS)
    if isinstance(configured_fields, dict):
        for logical_name, record_field in configured_fields.items():
            if logical_name in depth_record_fields and _text(record_field):
                depth_record_fields[logical_name] = record_field
    return requirements, required_attacks or set(_DEFAULT_ATTACKS), provider if isinstance(provider, str) else "ars", depth_record_fields


def evaluate_max_rigor(project: Path, config: dict[str, Any]) -> dict[str, Any]:
    """Require the extra robustness/red-team/ARS evidence promised by max mode."""
    mode = config.get("execution_mode", "research_autonomous") if isinstance(config, dict) else None
    if mode != _FORMAL_MAX:
        return {"status": "NOT_APPLICABLE", "mode": mode, "checks": []}
    root = Path(project).resolve()
    requirements, required_attacks, required_provider, depth_record_fields = _requirements()
    path = root / "artifacts" / "competition-max-review.json"
    checks: list[dict[str, Any]] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {"status": "FAIL", "mode": mode, "checks": [_check("G8-MAX-EVIDENCE-001", "FAIL", "competition-max-review.json is required", error=str(exc))]}
    if not supported_artifact_schema(data) or not _text(data.get("generated_by")):
        checks.append(_check("G8-MAX-SHAPE-001", "FAIL", "max-rigor artifact metadata is invalid"))
    numeric_requirements = {
        depth_record_fields["model_scouts"]: requirements["minimum_model_scouts"],
        depth_record_fields["candidate_routes_reviewed"]: requirements["minimum_candidate_routes_reviewed"],
        depth_record_fields["red_team_rounds"]: requirements["minimum_red_team_rounds"],
    }
    for field, minimum in numeric_requirements.items():
        value = _record_count(data, field)
        ok = value is not None and value >= minimum
        checks.append(_check("G8-MAX-DEPTH-001", "PASS" if ok else "FAIL", f"{field} meets max-mode minimum" if ok else f"{field} is missing, malformed, or below max-mode minimum", field=field, actual=value, minimum=minimum))
    attack_field = depth_record_fields["robustness_attacks"]
    attack_types = _record_types(data, attack_field)
    attack_ok = attack_types is not None and required_attacks <= attack_types
    checks.append(_check("G8-MAX-ROBUSTNESS-001", "PASS" if attack_ok else "FAIL", "extended robustness attacks are recorded" if attack_ok else "max mode lacks required structured robustness attacks", field=attack_field, required=sorted(required_attacks), actual=sorted(attack_types) if attack_types is not None else None))
    reviews = data.get("external_reviews")
    ars = [item for item in reviews if isinstance(item, dict) and item.get("provider") == required_provider] if isinstance(reviews, list) else []
    invalid_evidence = [item.get("evidence") for item in ars if _safe_existing_file(root, item.get("evidence")) is None]
    ars_ok = bool(ars) and not invalid_evidence and all(item.get("status") == "COMPLETE" for item in ars)
    checks.append(_check("G8-MAX-ARS-001", "PASS" if ars_ok else "FAIL", "ARS external review is complete and referenced" if ars_ok else "max mode requires a completed ARS review with existing project-local evidence", invalid_evidence=invalid_evidence))
    status = "PASS" if checks and all(item["status"] == "PASS" for item in checks) else "FAIL"
    return {"status": status, "mode": mode, "requirements": numeric_requirements, "checks": checks}
