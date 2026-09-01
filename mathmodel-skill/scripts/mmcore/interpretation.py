"""Deterministic interpretation tournament and G1 problem-understanding gate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

_CANDIDATE_FIELDS = (
    "questions", "objectives", "decision_variables", "hard_constraints",
    "implicit_constraints", "outputs", "dependencies", "ambiguities",
)
_CONFLICT_FIELDS = ("objectives", "decision_variables", "hard_constraints", "outputs", "dependencies")
_H1_REQUIRED_ARTIFACTS = {
    "artifacts/interpretation-candidates.json",
    "artifacts/interpretation-conflicts.json",
    "artifacts/problem-map.json",
}


def _profile() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[2] / "profiles" / "cumcm" / "profile.yaml"
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _check(rule: str, status: str, message: str, **evidence: Any) -> dict[str, Any]:
    return {"rule": rule, "status": status, "message": message, "evidence": evidence}


def _read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.is_file():
        return None, "missing artifact"
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, f"invalid JSON: {exc}"
    if not isinstance(loaded, dict):
        return None, "artifact root must be an object"
    return loaded, None


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


def _token(value: Any) -> str:
    if isinstance(value, str):
        return value.strip().casefold()
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _signature(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(sorted(_token(item) for item in value))


def _conflict_id(dimension: str, first: str, second: str) -> str:
    return f"CONFLICT-{dimension.upper()}-{first}-{second}"


def _computed_conflicts(candidates: list[dict[str, Any]], dimensions: tuple[str, ...]) -> list[dict[str, Any]]:
    conflicts = []
    for left_index, left in enumerate(candidates):
        for right in candidates[left_index + 1:]:
            left_id, right_id = left["interpreter_id"], right["interpreter_id"]
            for dimension in dimensions:
                if _signature(left.get(dimension)) == _signature(right.get(dimension)):
                    continue
                conflicts.append({
                    "id": _conflict_id(dimension, left_id, right_id),
                    "dimension": dimension,
                    "severity": "MAJOR",
                    "candidate_ids": [left_id, right_id],
                    "description": f"independent interpretations disagree on {dimension}",
                })
    return conflicts


def _candidate_checks(data: dict[str, Any], minimum: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    checks = []
    candidates = data.get("candidates")
    if not isinstance(candidates, list):
        return [_check("G1-CANDIDATE-SHAPE-001", "UNASSESSED", "candidate artifact must contain a candidates array")], []
    if len(candidates) < minimum:
        checks.append(_check("G1-CANDIDATE-COVERAGE-001", "FAIL", "minimum independent interpretation count is not met", actual=len(candidates), minimum=minimum))
    valid, ids = [], set()
    for candidate in candidates:
        if not isinstance(candidate, dict):
            checks.append(_check("G1-CANDIDATE-SHAPE-001", "UNASSESSED", "interpretation candidate must be an object"))
            continue
        missing = [field for field in ("interpreter_id", "independence_note", *_CANDIDATE_FIELDS) if field not in candidate]
        identifier = candidate.get("interpreter_id")
        if missing or not isinstance(identifier, str) or not identifier.strip() or identifier in ids:
            checks.append(_check("G1-CANDIDATE-SHAPE-001", "UNASSESSED", "interpretation candidate is malformed or duplicated", id=identifier, missing=missing))
            continue
        if not isinstance(candidate["independence_note"], str) or not candidate["independence_note"].strip() or any(not isinstance(candidate[field], list) for field in _CANDIDATE_FIELDS):
            checks.append(_check("G1-CANDIDATE-SHAPE-001", "UNASSESSED", "candidate fields must contain a non-empty independence note and arrays", id=identifier))
            continue
        ids.add(identifier)
        valid.append(candidate)
    if valid and not any(check["rule"] == "G1-CANDIDATE-COVERAGE-001" for check in checks):
        checks.append(_check("G1-CANDIDATE-COVERAGE-001", "PASS", "independent interpretation count meets profile", actual=len(valid), minimum=minimum))
    return checks, valid


def _conflict_checks(project: Path, computed: list[dict[str, Any]], candidate_ids: list[str]) -> tuple[list[dict[str, Any]], str | None]:
    checks = []
    data, error = _read_json(project / "artifacts" / "interpretation-conflicts.json")
    if error:
        return [_check("G1-CONFLICT-EVIDENCE-001", "UNASSESSED", "conflict evidence is unavailable", error=error)], None
    supplied = data.get("conflicts")
    if not isinstance(supplied, list):
        return [_check("G1-CONFLICT-EVIDENCE-001", "UNASSESSED", "conflict artifact must contain a conflicts array")], None
    metadata_valid = (
        data.get("schema_version") == 1
        and isinstance(data.get("generated_by"), str) and bool(data["generated_by"].strip())
        and isinstance(data.get("candidate_ids"), list)
        and all(isinstance(item, str) and bool(item.strip()) for item in data.get("candidate_ids", []))
        and sorted(data["candidate_ids"]) == sorted(candidate_ids)
    )
    if not metadata_valid:
        checks.append(_check("G1-ARTIFACT-METADATA-001", "FAIL", "conflict artifact metadata is missing or inconsistent"))
    by_id: dict[str, dict[str, Any]] = {}
    malformed_records = False
    for item in supplied:
        identifier = item.get("id") if isinstance(item, dict) else None
        if not isinstance(identifier, str) or not identifier.strip() or identifier in by_id:
            malformed_records = True
            continue
        by_id[identifier] = item
    if malformed_records:
        checks.append(_check("G1-CONFLICT-INTEGRITY-001", "FAIL", "conflict artifact contains duplicate or malformed IDs"))
    computed_ids = {item["id"] for item in computed}
    if set(by_id) != computed_ids:
        checks.append(_check("G1-CONFLICT-INTEGRITY-001", "FAIL", "conflict artifact does not match locally recomputed conflicts", expected=sorted(computed_ids), actual=sorted(by_id)))
    for conflict in computed:
        supplied_item = by_id.get(conflict["id"])
        if not isinstance(supplied_item, dict) or supplied_item.get("dimension") != conflict["dimension"] or supplied_item.get("candidate_ids") != conflict["candidate_ids"] or supplied_item.get("severity") != conflict["severity"]:
            checks.append(_check("G1-CONFLICT-INTEGRITY-001", "FAIL", "conflict evidence does not match locally recomputed metadata", conflict_id=conflict["id"]))
            continue
        if not isinstance(supplied_item.get("description"), str) or not supplied_item["description"].strip():
            checks.append(_check("G1-CONFLICT-INTEGRITY-001", "FAIL", "conflict evidence is missing a description", conflict_id=conflict["id"]))
            continue
        if supplied_item.get("resolution_status") == "OPEN":
            checks.append(_check("G1-CONFLICT-OPEN-001", "BLOCKED_INTERPRETATION_CONFLICT", "major interpretation conflict remains open", conflict_id=conflict["id"]))
        elif supplied_item.get("resolution_status") != "RESOLVED":
            checks.append(_check("G1-CONFLICT-RESOLUTION-001", "FAIL", "major conflict lacks an explicit resolution", conflict_id=conflict["id"]))
    if not computed and not checks:
        checks.append(_check("G1-CONFLICT-CHECK-001", "PASS", "no major interpretation conflicts were recomputed"))
    elif computed and not any(check["status"] in {"FAIL", "BLOCKED_INTERPRETATION_CONFLICT"} for check in checks):
        checks.append(_check("G1-CONFLICT-CHECK-001", "PASS", "all recomputed conflicts have explicit resolutions", conflicts=len(computed)))
    return checks, "BLOCKED_INTERPRETATION_CONFLICT" if any(check["status"] == "BLOCKED_INTERPRETATION_CONFLICT" for check in checks) else None


def _h1_check(project: Path) -> dict[str, Any]:
    rows, errors = _read_jsonl(project / "artifacts" / "human-review-ledger.jsonl")
    for row in rows:
        reviewed_items = row.get("reviewed_artifacts")
        reviewed = set(item.replace("\\", "/") for item in reviewed_items if isinstance(item, str)) if isinstance(reviewed_items, list) else set()
        if row.get("gate") == "H1_PROBLEM_UNDERSTANDING" and row.get("decision") == "APPROVED" and _H1_REQUIRED_ARTIFACTS <= reviewed:
            return _check("G1-H1-LINK-001", "PASS", "H1 signoff explicitly covers interpretation evidence", review_id=row.get("id"))
    return _check("G1-H1-LINK-001", "FAIL", "H1 signoff does not cover all interpretation evidence", ledger_errors=errors)


def evaluate_g1(project: Path, config: dict[str, Any]) -> dict[str, Any]:
    """Evaluate G1; formal modes fail closed and research mode is not applicable."""
    profile = _profile()
    mode = config.get("execution_mode", "research_autonomous")
    formal_modes = set(profile.get("formal_modes", ("competition_assisted", "competition_max")))
    if mode not in formal_modes:
        return {"gate": "G1_PROBLEM_UNDERSTANDING_LOCKED", "status": "NOT_APPLICABLE", "mode": mode, "checks": [], "conflicts": [], "missing_artifacts": []}
    candidates_data, candidate_error = _read_json(project / "artifacts" / "interpretation-candidates.json")
    missing = []
    if candidate_error == "missing artifact":
        missing.append("artifacts/interpretation-candidates.json")
    if not (project / "artifacts" / "interpretation-conflicts.json").is_file():
        missing.append("artifacts/interpretation-conflicts.json")
    if not (project / "artifacts" / "problem-map.json").is_file():
        missing.append("artifacts/problem-map.json")
    checks = []
    if candidate_error:
        checks.append(_check("G1-CANDIDATE-EVIDENCE-001", "UNASSESSED", "interpretation candidate evidence is unavailable", error=candidate_error))
        candidates = {}
    else:
        candidates = candidates_data or {}
        if candidates.get("schema_version") != 1 or not isinstance(candidates.get("problem_id"), str) or not candidates["problem_id"].strip():
            checks.append(_check("G1-ARTIFACT-METADATA-001", "FAIL", "interpretation candidate metadata is missing or invalid"))
    candidate_checks, valid_candidates = _candidate_checks(candidates, int(profile.get("minimum_independent_interpretations", 2)))
    checks.extend(candidate_checks)
    dimensions = tuple(profile.get("major_conflict_dimensions", _CONFLICT_FIELDS))
    computed = _computed_conflicts(valid_candidates, dimensions)
    conflict_checks, conflict_status = _conflict_checks(project, computed, [item["interpreter_id"] for item in valid_candidates])
    checks.extend(conflict_checks)
    problem_map, map_error = _read_json(project / "artifacts" / "problem-map.json")
    questions = problem_map.get("questions") if isinstance(problem_map, dict) else None
    map_valid = isinstance(questions, list) and bool(questions) and all(isinstance(q, dict) and isinstance(q.get("id"), str) and isinstance(q.get("dependencies"), list) for q in questions)
    checks.append(_check("G1-PROBLEM-MAP-001", "PASS" if map_valid else "UNASSESSED", "problem map contains question dependencies" if map_valid else "problem map is incomplete", error=map_error))
    checks.append(_h1_check(project))
    status = conflict_status or ("PASS" if checks and all(check["status"] == "PASS" for check in checks) else "FAIL")
    return {"gate": "G1_PROBLEM_UNDERSTANDING_LOCKED", "status": status, "mode": mode, "profile": profile.get("profile_id"), "rule_version": profile.get("rule_version"), "checks": checks, "conflicts": computed, "missing_artifacts": sorted(set(missing))}
