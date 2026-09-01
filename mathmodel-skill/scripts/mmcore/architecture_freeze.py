"""Cross-question architecture (G5.5) and frozen-results (G6) gates."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


_FORMAL_MODES = {"competition_assisted", "competition_max"}
_PROBLEM_TYPES = {"forecasting", "optimization", "evaluation", "mechanism", "simulation", "hybrid"}
_HASH_FILES = {
    "model_registry_hash": "artifacts/model-registry.json",
    "result_registry_hash": "artifacts/result-registry.json",
    "validation_hash": "artifacts/validation.json",
    "decision_ledger_hash": "artifacts/decision-ledger.json",
}


def _check(rule: str, status: str, message: str, **evidence: Any) -> dict[str, Any]:
    return {"rule": rule, "status": status, "message": message, "evidence": evidence}


def _read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, str(exc)
    return (value, None) if isinstance(value, dict) else (None, "artifact root must be an object")


def _safe_file(root: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    candidate = Path(value)
    if candidate.is_absolute():
        return None
    resolved = (root / candidate).resolve()
    if resolved != root and root not in resolved.parents:
        return None
    return resolved if resolved.is_file() else None


def _mode_status(config: dict[str, Any]) -> tuple[str, str | None, dict[str, Any] | None]:
    if not isinstance(config, dict):
        return "FAIL", None, {"rule": "G55-CONFIG-000", "status": "FAIL", "message": "configuration must be an object"}
    mode = config.get("execution_mode", "research_autonomous")
    if not isinstance(mode, str):
        return "FAIL", None, {"rule": "G55-CONFIG-001", "status": "FAIL", "message": "execution_mode must be a string"}
    if mode == "research_autonomous":
        return "NOT_APPLICABLE", mode, None
    if mode not in _FORMAL_MODES:
        return "FAIL", mode, {"rule": "G55-CONFIG-002", "status": "FAIL", "message": "execution_mode is not supported"}
    problem_type = config.get("problem_type")
    if not isinstance(problem_type, str) or problem_type not in _PROBLEM_TYPES:
        return "FAIL", mode, {"rule": "G55-CONFIG-003", "status": "FAIL", "message": "problem_type is not supported"}
    return "FORMAL", mode, None


def _items(value: Any, field: str) -> list[dict[str, Any]]:
    if not isinstance(value, dict) or not isinstance(value.get(field), list):
        return []
    return [item for item in value[field] if isinstance(item, dict)]


def evaluate_model_architecture(project: Path, config: dict[str, Any]) -> dict[str, Any]:
    """Evaluate the directed model architecture and cross-question coherence."""
    mode_status, mode, config_error = _mode_status(config)
    if mode_status == "NOT_APPLICABLE":
        return {"status": "NOT_APPLICABLE", "mode": mode, "checks": []}
    if config_error:
        return {"status": "FAIL", "mode": mode or "INVALID", "checks": [config_error]}
    root = Path(project).resolve()
    checks: list[dict[str, Any]] = []
    problem_map, problem_error = _read_json(root / "artifacts" / "problem-map.json")
    architecture, architecture_error = _read_json(root / "artifacts" / "model-architecture.json")
    if problem_error or architecture_error:
        checks.append(_check("G55-EVIDENCE-001", "FAIL", "problem map and model architecture are required", problem_map_error=problem_error, architecture_error=architecture_error))
        return {"status": "FAIL", "mode": mode, "checks": checks}
    raw_problem_questions = problem_map.get("questions")
    if not isinstance(raw_problem_questions, list) or not raw_problem_questions or any(not isinstance(item, dict) for item in raw_problem_questions):
        checks.append(_check("G55-SHAPE-002", "FAIL", "problem-map questions must be a non-empty array of objects"))
        return {"status": "FAIL", "mode": mode, "checks": checks}
    question_ids = {item.get("id") for item in raw_problem_questions if isinstance(item.get("id"), str) and item.get("id")}
    raw_questions = architecture.get("questions")
    architecture_questions = _items(architecture, "questions")
    if architecture.get("schema_version") != 1 or not architecture_questions or not isinstance(raw_questions, list) or any(not isinstance(item, dict) for item in raw_questions):
        checks.append(_check("G55-SHAPE-001", "FAIL", "model architecture must use schema_version 1 and a non-empty questions array"))
        return {"status": "FAIL", "mode": mode, "checks": checks}
    architecture_ids = [item.get("id") for item in architecture_questions]
    valid_architecture_ids = [item for item in architecture_ids if isinstance(item, str) and item]
    if set(valid_architecture_ids) != question_ids or len(set(valid_architecture_ids)) != len(architecture_ids):
        checks.append(_check("G55-COVERAGE-001", "FAIL", "architecture question nodes must exactly cover the problem map", problem_questions=sorted(question_ids), architecture_questions=architecture_ids))
    else:
        checks.append(_check("G55-COVERAGE-001", "PASS", "architecture covers every problem-map question"))
    model_registry, _ = _read_json(root / "artifacts" / "model-registry.json")
    raw_models = model_registry.get("models") if isinstance(model_registry, dict) else None
    if not isinstance(raw_models, list) or not raw_models or any(not isinstance(item, dict) for item in raw_models):
        checks.append(_check("G55-MODEL-SHAPE-001", "FAIL", "model-registry models must be a non-empty array of objects"))
    model_ids = {item.get("id") for item in _items(model_registry, "models") if isinstance(item.get("id"), str) and item.get("id")}
    symbol_units: dict[str, str] = {}
    parameter_units: dict[str, str] = {}
    assumption_text: dict[str, str] = {}
    output_ids: set[str] = set()
    for question in architecture_questions:
        qid = question.get("id")
        models = question.get("model_ids", [])
        if not isinstance(models, list) or not models or any(not isinstance(item, str) or item not in model_ids for item in models):
            checks.append(_check("G55-MODEL-DEPENDENCY-001", "FAIL", "architecture model dependency is missing or unresolved", question_id=qid))
        for output in question.get("outputs", []) if isinstance(question.get("outputs"), list) else []:
            if not isinstance(output, dict) or not isinstance(output.get("id"), str) or not output.get("id"):
                checks.append(_check("G55-OUTPUT-001", "FAIL", "output records must include a non-empty string id", question_id=qid))
            else:
                output_ids.add(output["id"])
        for field, units, rule in (("variables", symbol_units, "G55-SYMBOL-UNIT-001"), ("parameters", parameter_units, "G55-PARAMETER-001")):
            values = question.get(field, [])
            if not isinstance(values, list):
                checks.append(_check(rule, "FAIL", f"{field} must be an array", question_id=qid))
                continue
            for item in values:
                if not isinstance(item, dict) or not isinstance(item.get("name"), str) or not isinstance(item.get("unit"), str):
                    checks.append(_check(rule, "FAIL", f"{field} records must include name and unit", question_id=qid))
                    continue
                name, unit = item["name"], item["unit"]
                if name in units and units[name] != unit:
                    checks.append(_check(rule, "FAIL", "shared symbol or parameter has conflicting units", name=name, previous=units[name], current=unit))
                units[name] = unit
        assumptions = question.get("assumptions", [])
        if not isinstance(assumptions, list):
            checks.append(_check("G55-ASSUMPTION-001", "FAIL", "assumptions must be an array", question_id=qid))
        else:
            for item in assumptions:
                if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not isinstance(item.get("statement"), str):
                    checks.append(_check("G55-ASSUMPTION-001", "FAIL", "assumption records must include id and statement", question_id=qid))
                    continue
                if item["id"] in assumption_text and assumption_text[item["id"]] != item["statement"]:
                    checks.append(_check("G55-ASSUMPTION-001", "FAIL", "shared assumption has conflicting statements", assumption_id=item["id"]))
                assumption_text[item["id"]] = item["statement"]
        sources = question.get("data_sources", [])
        if not isinstance(sources, list) or any(_safe_file(root, source) is None for source in sources):
            checks.append(_check("G55-DATA-LINEAGE-001", "FAIL", "architecture data sources must be existing project-relative files", question_id=qid))
    links = architecture.get("links")
    if not isinstance(links, list):
        checks.append(_check("G55-LINK-001", "FAIL", "architecture must contain a links array"))
    else:
        for link in links:
            if not isinstance(link, dict) or not isinstance(link.get("from_question_id"), str) or not isinstance(link.get("to_question_id"), str) or link.get("from_question_id") not in question_ids or link.get("to_question_id") not in question_ids:
                checks.append(_check("G55-LINK-001", "FAIL", "architecture link references unknown questions"))
                continue
            linked_outputs = link.get("output_ids", [])
            if not isinstance(linked_outputs, list) or any(not isinstance(item, str) or item not in output_ids for item in linked_outputs):
                checks.append(_check("G55-LINK-001", "FAIL", "architecture link references unknown outputs"))
            source_question = next((item for item in architecture_questions if item.get("id") == link["from_question_id"]), None)
            if source_question is None:
                checks.append(_check("G55-LINK-001", "FAIL", "architecture link source node is missing", link=link))
                continue
            uncertain = {item.get("id") for item in source_question.get("outputs", []) if isinstance(item, dict) and isinstance(item.get("id"), str) and item.get("uncertain") is True}
            if "uncertainty_propagation" in link and not isinstance(link.get("uncertainty_propagation"), str):
                checks.append(_check("G55-LINK-001", "FAIL", "uncertainty_propagation must be a string", link=link))
                continue
            if uncertain.intersection(linked_outputs) and link.get("uncertainty_propagation") in {None, "none", "ignored"}:
                checks.append(_check("UNCERTAINTY_PROPAGATION_GAP", "FAIL", "uncertain output is consumed without declared uncertainty propagation", link=link))
    if not any(item["rule"] == "G55-SYMBOL-UNIT-001" for item in checks):
        checks.append(_check("G55-SYMBOL-UNIT-001", "PASS", "shared symbols have consistent units"))
    if not any(item["rule"] == "G55-PARAMETER-001" for item in checks):
        checks.append(_check("G55-PARAMETER-001", "PASS", "shared parameters have consistent units"))
    if not any(item["rule"] == "G55-ASSUMPTION-001" for item in checks):
        checks.append(_check("G55-ASSUMPTION-001", "PASS", "shared assumptions are consistent"))
    if not any(item["rule"] == "G55-DATA-LINEAGE-001" for item in checks):
        checks.append(_check("G55-DATA-LINEAGE-001", "PASS", "data lineage sources are safe and existing"))
    status = "PASS" if checks and all(item["status"] == "PASS" for item in checks) else "FAIL"
    return {"status": status, "mode": mode, "checks": checks, "question_ids": sorted(question_ids)}


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _hash_paths(root: Path, paths: list[Path]) -> str | None:
    if not paths:
        return None
    digest = hashlib.sha256()
    for path in sorted({Path(path).resolve() for path in paths}, key=str):
        try:
            relative = path.relative_to(root).as_posix()
        except ValueError:
            relative = f"OUTSIDE:{path}"
        digest.update(relative.encode())
        if path.is_file():
            digest.update(path.read_bytes())
        else:
            digest.update(b"<MISSING>")
    return digest.hexdigest()


def compute_upstream_hashes(project: Path, config: dict[str, Any]) -> dict[str, Any]:
    """Compute the deterministic hash set recorded by a freeze manifest."""
    root = Path(project).resolve()
    input_paths = []
    for field in ("statements", "attachments"):
        values = config.get("inputs", {}).get(field, []) if isinstance(config.get("inputs"), dict) else []
        values = values if isinstance(values, list) else []
        input_paths.extend((root / item).resolve() for item in values if isinstance(item, str))
    code_paths = [path for folder in (root / "analysis", root / "paper") for path in folder.rglob("*") if path.is_file() and path.suffix.lower() in {".py", ".m", ".r", ".jl", ".tex"}] if (root / "analysis").exists() or (root / "paper").exists() else []
    hashes: dict[str, Any] = {
        "raw_data_hash": _hash_paths(root, input_paths),
        "clean_data_hash": _hash_paths(root, [path for path in (root / "data").rglob("*") if path.is_file() and "raw" not in path.parts]),
        "code_hashes": {path.relative_to(root).as_posix(): _sha256(path) for path in sorted(code_paths, key=str)},
        "config_hash": _sha256(root / "mathmodel.json"),
    }
    for key, relative in _HASH_FILES.items():
        hashes[key] = _sha256(root / relative)
    return hashes


def _human_h3(root: Path, review_id: Any) -> tuple[bool, str]:
    path = root / "artifacts" / "human-review-ledger.jsonl"
    if not path.is_file():
        return False, "human review ledger is missing"
    try:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False, "human review ledger is malformed"
    for row in rows:
        if not isinstance(row, dict) or row.get("id") != review_id or row.get("gate") != "H3_RESULT_VERIFICATION":
            continue
        reviewed = {item.replace("\\", "/") for item in row.get("reviewed_artifacts", []) if isinstance(item, str)}
        notes = row.get("evidence_notes", "").lower() if isinstance(row.get("evidence_notes"), str) else ""
        required_phrases = (("数字", "number"), ("图", "figure"), ("结论", "conclusion"), ("limitation", "局限"))
        phrase_ok = all(any(phrase in notes for phrase in group) for group in required_phrases)
        ok = row.get("decision") == "APPROVED" and {"artifacts/frozen-results.json", "artifacts/freeze-manifest.json"} <= reviewed and phrase_ok
        return ok, "H3 signoff accepted" if ok else "H3 signoff does not cover all required result checks"
    return False, "referenced H3 signoff is missing"


def evaluate_results_freeze(project: Path, config: dict[str, Any]) -> dict[str, Any]:
    """Evaluate frozen published numbers, upstream hashes, stale propagation, and H3."""
    mode_status, mode, config_error = _mode_status(config)
    if mode_status == "NOT_APPLICABLE":
        return {"status": "NOT_APPLICABLE", "mode": mode, "checks": [], "stale_nodes": []}
    if config_error:
        return {"status": "FAIL", "mode": mode or "INVALID", "checks": [config_error], "stale_nodes": []}
    root = Path(project).resolve()
    checks: list[dict[str, Any]] = []
    registry, registry_error = _read_json(root / "artifacts" / "result-registry.json")
    frozen, frozen_error = _read_json(root / "artifacts" / "frozen-results.json")
    manifest, manifest_error = _read_json(root / "artifacts" / "freeze-manifest.json")
    if registry_error or frozen_error or manifest_error:
        checks.append(_check("G6-EVIDENCE-001", "FAIL", "result registry, frozen results, and freeze manifest are required", registry_error=registry_error, frozen_error=frozen_error, manifest_error=manifest_error))
        return {"status": "FAIL", "mode": mode, "checks": checks, "stale_nodes": ["freeze"]}
    registry_items = _items(registry, "results")
    raw_frozen_results = frozen.get("results")
    raw_registry_results = registry.get("results") if isinstance(registry, dict) else None
    if not isinstance(raw_registry_results, list) or not raw_registry_results or any(not isinstance(item, dict) for item in raw_registry_results):
        checks.append(_check("G6-REGISTRY-SHAPE-001", "FAIL", "result-registry results must be a non-empty array of objects"))
    frozen_items = _items(frozen, "results")
    frozen_by_id = {item.get("result_id"): item for item in frozen_items if isinstance(item.get("result_id"), str) and item.get("result_id")}
    if not isinstance(raw_frozen_results, list) or not raw_frozen_results or any(not isinstance(item, dict) for item in raw_frozen_results):
        checks.append(_check("G6-FROZEN-SHAPE-001", "FAIL", "frozen-results must contain only object records in a non-empty results array"))
    registry_ids = {item.get("id") for item in registry_items if isinstance(item.get("id"), str) and item.get("id")}
    mismatches = []
    for result in registry_items:
        frozen_result = frozen_by_id.get(result.get("id"))
        expected = {"value": result.get("value"), "unit": result.get("unit"), "source": result.get("source"), "field": result.get("field")}
        actual = {key: frozen_result.get(key) for key in expected} if frozen_result else None
        if actual != expected:
            mismatches.append(result.get("id"))
    if set(frozen_by_id) != registry_ids or len(registry_ids) != len(registry_items) or mismatches:
        checks.append(_check("G6-FROZEN-RESULT-001", "FAIL", "frozen results do not exactly match the current result registry", mismatches=mismatches))
    else:
        checks.append(_check("G6-FROZEN-RESULT-001", "PASS", "frozen results match the current result registry"))
    input_config = config.get("inputs") if isinstance(config.get("inputs"), dict) else None
    malformed_inputs = input_config is None or any(
        not isinstance(input_config.get(field), list) or any(not isinstance(item, str) for item in input_config.get(field, []))
        for field in ("statements", "attachments")
    )
    if malformed_inputs:
        checks.append(_check("G6-CONFIG-INPUT-001", "FAIL", "configured statements and attachments must be arrays of strings"))
    current_hashes = compute_upstream_hashes(root, config)
    expected_hashes = manifest.get("upstream_hashes") if isinstance(manifest.get("upstream_hashes"), dict) else {}
    changed = sorted(key for key, value in current_hashes.items() if expected_hashes.get(key) != value)
    stale_nodes: set[str] = set()
    for key in changed:
        if key in {"raw_data_hash", "clean_data_hash", "code_hashes"}:
            stale_nodes.update({"experiment", "result", "validation", "freeze", "paper_evidence", "reviews"})
        elif key in {"config_hash", "model_registry_hash", "decision_ledger_hash"}:
            stale_nodes.update({"selection", "experiment", "result", "validation", "freeze", "paper_evidence", "reviews"})
        elif key == "result_registry_hash":
            stale_nodes.update({"result", "validation", "freeze", "paper_evidence", "reviews"})
        elif key == "validation_hash":
            stale_nodes.update({"validation", "freeze", "paper_evidence", "reviews"})
    if manifest.get("status") != "CURRENT" or manifest.get("schema_version") != 1:
        stale_nodes.add("freeze")
    checks.append(_check("G6-STALE-001", "PASS" if not stale_nodes else "FAIL", "no upstream evidence is stale" if not stale_nodes else "upstream changes propagated stale state", changed_hashes=changed, stale_nodes=sorted(stale_nodes)))
    review_id = manifest.get("h3_review_id")
    h3_ok, h3_message = _human_h3(root, review_id) if isinstance(review_id, str) and review_id.strip() else (False, "freeze manifest must reference a non-empty H3 review ID")
    checks.append(_check("G6-H3-001", "PASS" if h3_ok else "FAIL", h3_message, review_id=manifest.get("h3_review_id")))
    status = "PASS" if checks and all(item["status"] == "PASS" for item in checks) else "FAIL"
    return {"status": status, "mode": mode, "checks": checks, "stale_nodes": sorted(stale_nodes), "changed_hashes": changed}
