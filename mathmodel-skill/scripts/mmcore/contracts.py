"""Evidence-contract validation for mathmodel project artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_REQUIRED_FIGURE_ROLES = ("data", "method", "result", "validation")
REQUIRED_ARTIFACTS = (
    "problem-map.json",
    "data-audit.json",
    "model-registry.json",
    "result-registry.json",
    "claim-registry.json",
    "figure-registry.json",
    "validation.json",
)
REGISTRY_COLLECTIONS = {
    "problem-map": ("questions", "question"),
    "model-registry": ("models", "model"),
    "result-registry": ("results", "result"),
    "claim-registry": ("claims", "claim"),
    "figure-registry": ("figures", "figure"),
    "validation": ("validations", "validation"),
}


def _check(
    rule: str,
    severity: str,
    status: str,
    message: str,
    *,
    path: str | None = None,
    evidence: Any | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "rule": rule,
        "severity": severity,
        "status": status,
        "message": message,
    }
    record["path"] = path
    record["evidence"] = {} if evidence is None else evidence
    return record


def _artifact_key(filename: str) -> str:
    return filename[:-5] if filename.endswith(".json") else filename


def _load_artifacts(project: Path, required: tuple[str, ...]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    artifacts: dict[str, Any] = {}
    checks: list[dict[str, Any]] = []
    for filename in required:
        path = project / "artifacts" / filename
        relative = f"artifacts/{filename}"
        if not path.exists():
            checks.append(_check("ARTIFACT-FILE-001", "FAIL", "FAIL", f"missing required artifact {filename}", path=relative))
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            checks.append(_check("ARTIFACT-JSON-001", "FAIL", "FAIL", f"malformed JSON in {filename}: {exc}", path=relative))
            continue
        artifacts[_artifact_key(filename)] = value
        checks.append(_check("ARTIFACT-FILE-001", "FAIL", "PASS", f"loaded required artifact {filename}", path=relative))
    return artifacts, checks


def _shape_checks(artifacts: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    data_audit = artifacts.get("data-audit")
    if not isinstance(data_audit, dict):
        checks.append(
            _check(
                "ARTIFACT-SHAPE-001",
                "FAIL",
                "FAIL",
                "data-audit.json must contain a JSON object",
                path="artifacts/data-audit.json",
                evidence={"expected": "object", "actual": type(data_audit).__name__},
            )
        )
    elif not isinstance(data_audit.get("status"), str) or not data_audit.get("status"):
        checks.append(
            _check(
                "ARTIFACT-SHAPE-001",
                "FAIL",
                "FAIL",
                "data-audit.json must include a non-empty status field",
                path="artifacts/data-audit.json",
                evidence={"field": "status"},
            )
        )
    else:
        checks.append(
            _check(
                "ARTIFACT-SHAPE-001",
                "FAIL",
                "PASS",
                "data-audit.json has the required top-level object shape",
                path="artifacts/data-audit.json",
            )
        )

    for artifact, (field, label) in REGISTRY_COLLECTIONS.items():
        container = artifacts.get(artifact)
        relative = f"artifacts/{artifact}.json"
        if not isinstance(container, dict):
            checks.append(
                _check(
                    "ARTIFACT-SHAPE-001",
                    "FAIL",
                    "FAIL",
                    f"{artifact}.json must contain a JSON object",
                    path=relative,
                    evidence={"expected": "object", "actual": type(container).__name__},
                )
            )
            continue
        collection = container.get(field)
        if not isinstance(collection, list) or not collection:
            checks.append(
                _check(
                    "ARTIFACT-SHAPE-001",
                    "FAIL",
                    "FAIL",
                    f"{artifact}.json must contain a non-empty {field} array",
                    path=relative,
                    evidence={"field": field, "actual": type(collection).__name__},
                )
            )
            continue
        bad_indexes = [index for index, item in enumerate(collection) if not isinstance(item, dict)]
        if bad_indexes:
            checks.append(
                _check(
                    "ARTIFACT-SHAPE-001",
                    "FAIL",
                    "FAIL",
                    f"{label} records must be JSON objects",
                    path=relative,
                    evidence={"field": field, "non_object_indexes": bad_indexes},
                )
            )
            continue
        checks.append(
            _check(
                "ARTIFACT-SHAPE-001",
                "FAIL",
                "PASS",
                f"{artifact}.json has the required {field} collection",
                path=relative,
                evidence={"field": field, "count": len(collection)},
            )
        )
    return checks


def _items(container: Any, field: str) -> list[dict[str, Any]]:
    if isinstance(container, dict):
        value = container.get(field, [])
    else:
        value = []
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _ids(items: list[dict[str, Any]]) -> set[str]:
    return {item["id"] for item in items if isinstance(item.get("id"), str) and item.get("id")}


def _duplicate_checks(artifacts: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for artifact, (field, label) in REGISTRY_COLLECTIONS.items():
        seen: set[str] = set()
        duplicates: set[str] = set()
        missing = 0
        for item in _items(artifacts.get(artifact), field):
            item_id = item.get("id")
            if not isinstance(item_id, str) or not item_id:
                missing += 1
                continue
            if item_id in seen:
                duplicates.add(item_id)
            seen.add(item_id)
        if duplicates or missing:
            detail = {"duplicates": sorted(duplicates), "missing_id_count": missing}
            checks.append(
                _check(
                    "ARTIFACT-ID-001",
                    "FAIL",
                    "FAIL",
                    f"{label} records must have unique stable IDs",
                    path=f"artifacts/{artifact}.json",
                    evidence=detail,
                )
            )
        else:
            checks.append(
                _check(
                    "ARTIFACT-ID-001",
                    "FAIL",
                    "PASS",
                    f"{label} IDs are stable and unique",
                    path=f"artifacts/{artifact}.json",
                )
            )
    return checks


def _missing_references(values: Any, known: set[str]) -> list[str]:
    if not isinstance(values, list):
        return []
    return sorted({value for value in values if isinstance(value, str) and value not in known})


def _required_id_list(record: dict[str, Any], field: str) -> tuple[bool, list[str]]:
    value = record.get(field)
    if not isinstance(value, list) or not value:
        return False, []
    valid_values = [item for item in value if isinstance(item, str) and item]
    return len(valid_values) == len(value), valid_values


def _support_checks(questions: list[dict[str, Any]], claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for question in questions:
        missing_or_invalid = []
        for field in ("model_ids", "result_ids", "validation_ids", "claim_ids"):
            ok, _ = _required_id_list(question, field)
            if not ok:
                missing_or_invalid.append(field)
        checks.append(
            _check(
                "EVIDENCE-QUESTION-SUPPORT-001",
                "FAIL",
                "FAIL" if missing_or_invalid else "PASS",
                "question has required evidence associations"
                if not missing_or_invalid
                else "question is missing required evidence associations",
                path="artifacts/problem-map.json",
                evidence={"question_id": question.get("id"), "missing_or_invalid": missing_or_invalid},
            )
        )
    for claim in claims:
        missing_or_invalid = []
        for field in ("result_ids", "validation_ids"):
            ok, _ = _required_id_list(claim, field)
            if not ok:
                missing_or_invalid.append(field)
        checks.append(
            _check(
                "EVIDENCE-CLAIM-SUPPORT-001",
                "FAIL",
                "FAIL" if missing_or_invalid else "PASS",
                "claim has required result and validation support"
                if not missing_or_invalid
                else "claim is missing required result or validation support",
                path="artifacts/claim-registry.json",
                evidence={"claim_id": claim.get("id"), "missing_or_invalid": missing_or_invalid},
            )
        )
    return checks


def audit_cross_references(artifacts: dict[str, Any]) -> list[dict[str, Any]]:
    """Check question/model/result/claim/figure/validation ID references."""
    questions = _items(artifacts.get("problem-map"), "questions")
    models = _items(artifacts.get("model-registry"), "models")
    results = _items(artifacts.get("result-registry"), "results")
    claims = _items(artifacts.get("claim-registry"), "claims")
    figures = _items(artifacts.get("figure-registry"), "figures")
    validations = _items(artifacts.get("validation"), "validations")
    question_ids = _ids(questions)
    model_ids = _ids(models)
    result_ids = _ids(results)
    claim_ids = _ids(claims)
    validation_ids = _ids(validations)
    checks: list[dict[str, Any]] = []
    checks.extend(_support_checks(questions, claims))

    for question in questions:
        evidence = {
            "question_id": question.get("id"),
            "missing_models": _missing_references(question.get("model_ids"), model_ids),
            "missing_results": _missing_references(question.get("result_ids"), result_ids),
            "missing_validations": _missing_references(question.get("validation_ids"), validation_ids),
            "missing_claims": _missing_references(question.get("claim_ids"), claim_ids),
        }
        missing = [value for key, value in evidence.items() if key.startswith("missing_") and value]
        checks.append(
            _check(
                "EVIDENCE-QUESTION-001",
                "FAIL",
                "FAIL" if missing else "PASS",
                "question references resolve" if not missing else "question contains broken evidence references",
                path="artifacts/problem-map.json",
                evidence=evidence,
            )
        )

    for model in models:
        question_id = model.get("question_id")
        ok = isinstance(question_id, str) and question_id in question_ids
        checks.append(
            _check(
                "EVIDENCE-MODEL-001",
                "FAIL",
                "PASS" if ok else "FAIL",
                "model is tied to a known question" if ok else "model references an unknown question",
                path="artifacts/model-registry.json",
                evidence={"model_id": model.get("id"), "question_id": question_id},
            )
        )

    for claim in claims:
        missing_results = _missing_references(claim.get("result_ids"), result_ids)
        missing_validations = _missing_references(claim.get("validation_ids"), validation_ids)
        checks.append(
            _check(
                "EVIDENCE-CLAIM-001",
                "FAIL",
                "FAIL" if missing_results or missing_validations else "PASS",
                "claim support resolves" if not missing_results and not missing_validations else "claim references missing support",
                path="artifacts/claim-registry.json",
                evidence={
                    "claim_id": claim.get("id"),
                    "missing_results": missing_results,
                    "missing_validations": missing_validations,
                },
            )
        )

    for figure in figures:
        missing_claims = _missing_references(figure.get("claim_ids"), claim_ids)
        checks.append(
            _check(
                "EVIDENCE-FIGURE-001",
                "FAIL",
                "FAIL" if missing_claims else "PASS",
                "figure claim references resolve" if not missing_claims else "figure references missing claims",
                path="artifacts/figure-registry.json",
                evidence={"figure_id": figure.get("id"), "missing_claims": missing_claims},
            )
        )

    for validation in validations:
        question_id = validation.get("question_id")
        ok = isinstance(question_id, str) and question_id in question_ids
        checks.append(
            _check(
                "EVIDENCE-VALIDATION-001",
                "FAIL",
                "PASS" if ok else "FAIL",
                "validation is tied to a known question" if ok else "validation references an unknown question",
                path="artifacts/validation.json",
                evidence={"validation_id": validation.get("id"), "question_id": question_id},
            )
        )
    return checks


def _file_checks(project: Path, artifacts: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for result in _items(artifacts.get("result-registry"), "results"):
        source = result.get("source")
        resolved, path_error = _safe_project_path(project, source)
        if path_error:
            checks.append(
                _check(
                    "EVIDENCE-RESULT-PATH-001",
                    "FAIL",
                    "FAIL",
                    "result source path must be project-relative and stay inside the project",
                    path=source if isinstance(source, str) and source else "artifacts/result-registry.json",
                    evidence={"result_id": result.get("id"), "source": source, "error": path_error},
                )
            )
            continue
        ok = resolved.is_file()
        checks.append(
            _check(
                "EVIDENCE-RESULT-SOURCE-001",
                "FAIL",
                "PASS" if ok else "FAIL",
                "result source exists" if ok else "result source is missing",
                path=source if isinstance(source, str) and source else "artifacts/result-registry.json",
                evidence={"result_id": result.get("id"), "source": source},
            )
        )
    for figure in _items(artifacts.get("figure-registry"), "figures"):
        file_path = figure.get("file")
        resolved, path_error = _safe_project_path(project, file_path)
        if path_error:
            checks.append(
                _check(
                    "FIGURE-PATH-001",
                    "FAIL",
                    "FAIL",
                    "figure file path must be project-relative and stay inside the project",
                    path=file_path if isinstance(file_path, str) and file_path else "artifacts/figure-registry.json",
                    evidence={"figure_id": figure.get("id"), "file": file_path, "error": path_error},
                )
            )
            continue
        ok = resolved.is_file()
        checks.append(
            _check(
                "FIGURE-FILE-001",
                "FAIL",
                "PASS" if ok else "FAIL",
                "figure file exists" if ok else "figure file is missing",
                path=file_path if isinstance(file_path, str) and file_path else "artifacts/figure-registry.json",
                evidence={"figure_id": figure.get("id"), "file": file_path},
            )
        )
    return checks


def _safe_project_path(project: Path, value: Any) -> tuple[Path, str | None]:
    root = Path(project).resolve()
    if not isinstance(value, str) or not value:
        return root, "path is missing or not a string"
    candidate = Path(value)
    if candidate.is_absolute():
        return root, "absolute paths are not allowed"
    resolved = (root / candidate).resolve()
    if resolved != root and root not in resolved.parents:
        return root, "path escapes project root"
    return resolved, None


def _required_roles(project: Path) -> tuple[str, ...]:
    config_path = project / "mathmodel.json"
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            roles = config.get("quality", {}).get("required_figure_roles")
            if isinstance(roles, list) and all(isinstance(role, str) and role for role in roles):
                return tuple(roles)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            pass
    return DEFAULT_REQUIRED_FIGURE_ROLES


def _role_checks(project: Path, artifacts: dict[str, Any]) -> list[dict[str, Any]]:
    roles = {figure.get("role") for figure in _items(artifacts.get("figure-registry"), "figures")}
    missing = sorted(role for role in _required_roles(project) if role not in roles)
    return [
        _check(
            "FIGURE-ROLE-001",
            "FAIL",
            "FAIL" if missing else "PASS",
            "required figure roles are present" if not missing else "missing required figure roles",
            path="artifacts/figure-registry.json",
            evidence={"missing_roles": missing},
        )
    ]


def _validation_status_checks(artifacts: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    validations = _items(artifacts.get("validation"), "validations")
    for validation in validations:
        ok = validation.get("status") == "PASS"
        checks.append(
            _check(
                "VALIDATION-STATUS-001",
                "FAIL",
                "PASS" if ok else "FAIL",
                "validation status is PASS" if ok else "validation status is not PASS",
                path="artifacts/validation.json",
                evidence={"validation_id": validation.get("id"), "status": validation.get("status")},
            )
        )
    return checks


def validate_artifacts(project: Path, required: tuple[str, ...]) -> dict[str, Any]:
    """Validate artifact files and evidence cross-references for a project."""
    root = Path(project).resolve()
    artifacts, checks = _load_artifacts(root, required)
    checks.extend(_shape_checks(artifacts))
    checks.extend(_duplicate_checks(artifacts))
    checks.extend(audit_cross_references(artifacts))
    checks.extend(_file_checks(root, artifacts))
    checks.extend(_role_checks(root, artifacts))
    checks.extend(_validation_status_checks(artifacts))
    status = "FAIL" if any(check["severity"] == "FAIL" and check["status"] == "FAIL" for check in checks) else "PASS"
    return {"status": status, "checks": checks}
