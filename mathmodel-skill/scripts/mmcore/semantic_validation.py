"""Machine-computed validation and falsification gates (G4/G5)."""

from __future__ import annotations

import json
import math
import operator
from pathlib import Path
from typing import Any, Callable

import yaml

from .experiment import evaluate_experiment_provenance

_OPERATORS: dict[str, Callable[[float, float], bool]] = {
    "<": operator.lt, "<=": operator.le, ">": operator.gt,
    ">=": operator.ge, "==": operator.eq, "!=": operator.ne,
}
_DEFAULT_REQUIREMENTS = {
    "forecasting": ("chronological_split", "leakage_check", "baseline", "metric_recomputation"),
    "optimization": ("solver_status", "feasibility", "constraint_violation", "objective_recomputation", "baseline_policy"),
    "evaluation": ("indicator_direction", "normalization", "weight_provenance", "ranking_stability"),
    "simulation": ("seed", "replications", "convergence", "uncertainty_interval"),
    "mechanism": ("units", "boundary_behavior", "parameter_plausibility", "calibration"),
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


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _safe_path(project: Path, value: Any) -> tuple[Path | None, str | None]:
    if not isinstance(value, str) or not value.strip():
        return None, "path is missing or not a string"
    candidate = Path(value)
    if candidate.is_absolute():
        return None, "absolute paths are not allowed"
    root = Path(project).resolve()
    resolved = (root / candidate).resolve()
    if resolved != root and root not in resolved.parents:
        return None, "path escapes project root"
    return resolved, None


def _number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(float(value))
    except (OverflowError, ValueError):
        return False


def _validation_checks(project: Path, data: dict[str, Any], required: tuple[str, ...]) -> tuple[list[dict[str, Any]], list[str]]:
    checks = []
    validations = data.get("validations")
    if not isinstance(validations, list) or not validations:
        return [_check("G4-VALIDATION-SHAPE-001", "UNASSESSED", "validation artifact must contain a non-empty validations array")], []
    ids: set[str] = set()
    for record in validations:
        identifier = record.get("id") if isinstance(record, dict) else None
        if not isinstance(record, dict):
            checks.append(_check("G4-VALIDATION-SHAPE-001", "FAIL", "validation record must be an object"))
            continue
        required_fields = ("id", "question_id", "metric", "operator", "threshold", "observed", "evidence_source", "checks")
        missing = [field for field in required_fields if field not in record]
        if not _text(identifier) or identifier in ids or missing:
            checks.append(_check("G4-VALIDATION-SHAPE-001", "FAIL", "validation record is malformed or duplicated", id=identifier, missing=missing))
            continue
        ids.add(identifier)
        metric_ok = _text(record.get("metric")) and _text(record.get("question_id")) and isinstance(record.get("operator"), str) and record.get("operator") in _OPERATORS and _number(record.get("threshold")) and _number(record.get("observed"))
        evidence_path, path_error = _safe_path(project, record.get("evidence_source"))
        path_ok = path_error is None and evidence_path is not None and evidence_path.is_file()
        if not metric_ok:
            checks.append(_check("G4-METRIC-001", "FAIL", "validation metric/operator/numeric fields are invalid", id=identifier))
        elif _OPERATORS[record["operator"]](float(record["observed"]), float(record["threshold"])):
            checks.append(_check("G4-METRIC-001", "PASS", "metric threshold computed locally as PASS", id=identifier, observed=record["observed"], operator=record["operator"], threshold=record["threshold"], computed_status="PASS"))
        else:
            checks.append(_check("G4-METRIC-001", "FAIL", "metric threshold computed locally as FAIL", id=identifier, observed=record["observed"], operator=record["operator"], threshold=record["threshold"], computed_status="FAIL"))
        if not path_ok:
            checks.append(_check("G4-PATH-001", "FAIL", "validation evidence source is missing or unsafe", id=identifier, source=record.get("evidence_source"), error=path_error or "file does not exist"))
        semantic = record.get("checks")
        missing_semantic, failed_semantic = [], []
        if not isinstance(semantic, dict):
            missing_semantic = list(required)
        else:
            for field in required:
                item = semantic.get(field)
                if not isinstance(item, dict) or item.get("status") != "PASS" or not _text(item.get("evidence")):
                    (missing_semantic if field not in semantic else failed_semantic).append(field)
        if missing_semantic or failed_semantic:
            checks.append(_check("G4-SEMANTIC-CHECK-001", "FAIL", "problem-type validation checks are incomplete or failed", id=identifier, missing=missing_semantic, failed=failed_semantic))
        else:
            checks.append(_check("G4-SEMANTIC-CHECK-001", "PASS", "problem-type validation checks are complete", id=identifier, requirements=list(required)))
    return checks, sorted(ids)


def _falsification_checks(project: Path, data: dict[str, Any], validation_ids: list[str]) -> list[dict[str, Any]]:
    checks = []
    attacks = data.get("attacks")
    if not isinstance(attacks, list):
        return [_check("G5-FALSIFICATION-SHAPE-001", "UNASSESSED", "falsification artifact must contain an attacks array")]
    by_validation: dict[str, int] = {}
    seen_ids: set[str] = set()
    for attack in attacks:
        identifier = attack.get("id") if isinstance(attack, dict) else None
        if not isinstance(attack, dict) or not _text(identifier) or identifier in seen_ids:
            checks.append(_check("G5-FALSIFICATION-SHAPE-001", "FAIL", "falsification attack is malformed or duplicated", id=identifier))
            continue
        seen_ids.add(identifier)
        required = ("id", "validation_id", "attack_type", "evidence_source", "outcome", "evidence_note")
        missing = [field for field in required if field not in attack]
        valid_shape = not missing and all(_text(attack.get(field)) for field in ("id", "validation_id", "attack_type", "evidence_source", "outcome", "evidence_note")) and attack.get("outcome") in {"SURVIVED", "BROKEN"}
        evidence_path, path_error = _safe_path(project, attack.get("evidence_source"))
        if not valid_shape:
            checks.append(_check("G5-FALSIFICATION-SHAPE-001", "FAIL", "falsification attack is incomplete or invalid", id=identifier, missing=missing))
            continue
        by_validation[attack["validation_id"]] = by_validation.get(attack["validation_id"], 0) + 1
        if path_error or evidence_path is None or not evidence_path.is_file():
            checks.append(_check("G5-FALSIFICATION-PATH-001", "FAIL", "falsification evidence source is missing or unsafe", id=identifier, error=path_error or "file does not exist"))
        elif attack["outcome"] == "BROKEN":
            checks.append(_check("G5-FALSIFICATION-001", "FAIL", "falsification attack broke the result", id=identifier, validation_id=attack["validation_id"]))
        else:
            checks.append(_check("G5-FALSIFICATION-001", "PASS", "result survived falsification attack", id=identifier, validation_id=attack["validation_id"]))
    missing_coverage = sorted(set(validation_ids) - set(by_validation))
    unknown_coverage = sorted(set(by_validation) - set(validation_ids))
    if missing_coverage:
        checks.append(_check("G5-FALSIFICATION-COVERAGE-001", "FAIL", "every validation needs a falsification attack", missing=missing_coverage))
    if unknown_coverage:
        checks.append(_check("G5-FALSIFICATION-COVERAGE-001", "FAIL", "falsification attacks reference unknown validations", unknown=unknown_coverage))
    if not missing_coverage and not unknown_coverage and validation_ids:
        checks.append(_check("G5-FALSIFICATION-COVERAGE-001", "PASS", "all validations have falsification coverage", validations=validation_ids))
    return checks


def evaluate_semantic_validation(project: Path, config: dict[str, Any]) -> dict[str, Any]:
    """Evaluate G4/G5; formal modes fail closed, research mode is N/A."""
    profile = _profile()
    mode = config.get("execution_mode", "research_autonomous")
    formal_modes = set(profile.get("formal_modes", ("competition_assisted", "competition_max")))
    known_modes = formal_modes | {"research_autonomous"}
    if not isinstance(mode, str):
        check = _check("G4-CONFIG-001", "FAIL", "execution_mode must be a string", actual_type=type(mode).__name__)
        return {"status": "FAIL", "mode": "INVALID", "g4": {"status": "FAIL", "checks": [check]}, "g5": {"status": "FAIL", "checks": []}}
    if mode not in known_modes:
        check = _check("G4-CONFIG-003", "FAIL", "execution_mode is not supported", execution_mode=mode)
        return {"status": "FAIL", "mode": "INVALID", "g4": {"status": "FAIL", "checks": [check]}, "g5": {"status": "FAIL", "checks": []}}
    problem_type = config.get("problem_type")
    if not isinstance(problem_type, str) or not problem_type.strip():
        check = _check("G4-CONFIG-002", "FAIL", "problem_type must be a non-empty string", actual_type=type(problem_type).__name__)
        return {"status": "FAIL", "mode": mode, "g4": {"status": "FAIL", "checks": [check]}, "g5": {"status": "FAIL", "checks": []}}
    validation_requirements = profile.get("validation_requirements", {})
    known_problem_types = set(validation_requirements) if isinstance(validation_requirements, dict) else set()
    known_problem_types.update(_DEFAULT_REQUIREMENTS)
    known_problem_types.add("hybrid")
    if problem_type not in known_problem_types:
        check = _check("G4-CONFIG-004", "FAIL", "problem_type is not supported", problem_type=problem_type)
        return {"status": "FAIL", "mode": mode, "g4": {"status": "FAIL", "checks": [check]}, "g5": {"status": "FAIL", "checks": []}}
    if mode == "research_autonomous":
        return {"status": "NOT_APPLICABLE", "mode": mode, "g4": {"status": "NOT_APPLICABLE", "checks": []}, "g5": {"status": "NOT_APPLICABLE", "checks": []}}
    validation_data, validation_error = _read_json(Path(project) / "artifacts" / "validation.json")
    g4_checks = []
    if validation_error:
        g4_checks.append(_check("G4-VALIDATION-EVIDENCE-001", "UNASSESSED", "validation artifact is unavailable", error=validation_error))
        validation_ids = []
    else:
        if validation_data.get("schema_version") != 1:
            g4_checks.append(_check("G4-ARTIFACT-METADATA-001", "FAIL", "validation artifact schema_version must be 1"))
        requirements = tuple(validation_requirements.get(problem_type, _DEFAULT_REQUIREMENTS.get(problem_type, ())))
        validation_checks, validation_ids = _validation_checks(Path(project), validation_data, requirements)
        g4_checks.extend(validation_checks)
        raw = validation_data.get("validations")
        validation_ids = [item["id"] for item in raw if isinstance(item, dict) and _text(item.get("id"))] if isinstance(raw, list) else []
    experiment_report = evaluate_experiment_provenance(Path(project), config)
    g4_checks.extend(experiment_report.get("checks", []))
    g4_status = "PASS" if g4_checks and all(check["status"] == "PASS" for check in g4_checks) else "FAIL"
    falsification_data, falsification_error = _read_json(Path(project) / "artifacts" / "falsification.json")
    g5_checks = []
    if g4_status != "PASS":
        g5_checks.append(_check("G5-PREREQUISITE-001", "FAIL", "G5 requires G4 to pass"))
    if falsification_error:
        g5_checks.append(_check("G5-FALSIFICATION-EVIDENCE-001", "UNASSESSED", "falsification artifact is unavailable", error=falsification_error))
    else:
        if falsification_data.get("schema_version") != 1 or not _text(falsification_data.get("generated_by")):
            g5_checks.append(_check("G5-ARTIFACT-METADATA-001", "FAIL", "falsification artifact metadata is missing or invalid"))
        g5_checks.extend(_falsification_checks(Path(project), falsification_data, validation_ids))
    g5_status = "PASS" if g4_status == "PASS" and g5_checks and all(check["status"] == "PASS" for check in g5_checks) else "FAIL"
    return {"status": "PASS" if g4_status == "PASS" and g5_status == "PASS" else "FAIL", "mode": mode, "profile": profile.get("profile_id"), "rule_version": profile.get("rule_version"), "experiment_provenance": experiment_report, "g4": {"status": g4_status, "checks": g4_checks, "validation_ids": validation_ids}, "g5": {"status": g5_status, "checks": g5_checks}}
