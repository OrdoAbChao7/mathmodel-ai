"""Machine checks for reproducible formal experiment provenance."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .schema import supported_artifact_schema


_REQUIRED = ("id", "run_id", "question_id", "model_id", "code_hashes", "input_hashes", "config_hash", "seed", "environment", "started_at", "ended_at", "metrics", "figures", "result_artifacts")


def _check(rule: str, status: str, message: str, **evidence: Any) -> dict[str, Any]:
    return {"rule": rule, "status": status, "message": message, "evidence": evidence}


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inside(root: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value.strip() or Path(value).is_absolute():
        return None
    candidate = (root / value).resolve()
    if candidate != root and root not in candidate.parents:
        return None
    return candidate


def evaluate_experiment_provenance(project: Path, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validate experiment metadata and recompute every referenced file hash."""
    root = Path(project).resolve()
    path = root / "artifacts" / "experiment-registry.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {"status": "FAIL", "checks": [_check("G4-EXPERIMENT-EVIDENCE-001", "FAIL", "experiment-registry.json is required for formal experiments", error=str(exc))]}
    checks: list[dict[str, Any]] = []
    if not supported_artifact_schema(data) or not _text(data.get("generated_by")):
        checks.append(_check("G4-EXPERIMENT-SHAPE-001", "FAIL", "experiment registry metadata is invalid"))
    rows = data.get("experiments") if isinstance(data, dict) else None
    if not isinstance(rows, list) or not rows:
        return {"status": "FAIL", "checks": checks + [_check("G4-EXPERIMENT-SHAPE-001", "FAIL", "experiment registry must contain a non-empty experiments array")]}
    seen: set[str] = set()
    for row in rows:
        identifier = row.get("id") if isinstance(row, dict) else None
        missing = [field for field in _REQUIRED if not isinstance(row, dict) or field not in row]
        shape_ok = isinstance(row, dict) and _text(identifier) and identifier not in seen and not missing and _text(row.get("run_id")) and _text(row.get("question_id")) and _text(row.get("model_id")) and isinstance(row.get("seed"), int) and not isinstance(row.get("seed"), bool) and isinstance(row.get("environment"), dict) and all(_text(row["environment"].get(field)) for field in ("python_version", "platform")) and _text(row.get("started_at")) and _text(row.get("ended_at"))
        if _text(identifier):
            seen.add(identifier)
        checks.append(_check("G4-EXPERIMENT-SHAPE-001", "PASS" if shape_ok else "FAIL", "experiment provenance fields are complete" if shape_ok else "experiment provenance fields are incomplete or duplicated", id=identifier, missing=missing))
        if not shape_ok:
            continue
        hashes_ok = True
        for field in ("code_hashes", "input_hashes"):
            mapping = row.get(field)
            if not isinstance(mapping, dict) or not mapping:
                hashes_ok = False
                continue
            for relative, expected in mapping.items():
                candidate = _inside(root, relative)
                actual = _hash(candidate) if candidate is not None and candidate.is_file() else None
                valid = isinstance(expected, str) and len(expected) == 64 and actual == expected
                hashes_ok = hashes_ok and valid
        config_path = root / "mathmodel.json"
        hashes_ok = hashes_ok and isinstance(row.get("config_hash"), str) and row.get("config_hash") == (_hash(config_path) if config_path.is_file() else None)
        checks.append(_check("G4-EXPERIMENT-HASH-001", "PASS" if hashes_ok else "FAIL", "code, input, and configuration hashes match" if hashes_ok else "experiment hashes are missing or stale", id=identifier))
        path_fields_ok = True
        for field in ("metrics", "figures", "result_artifacts"):
            values = row.get(field)
            valid = isinstance(values, list) and (field == "figures" or bool(values)) and all(_inside(root, value) is not None and _inside(root, value).is_file() for value in values)
            path_fields_ok = path_fields_ok and valid
        checks.append(_check("G4-EXPERIMENT-OUTPUT-001", "PASS" if path_fields_ok else "FAIL", "experiment output artifacts resolve" if path_fields_ok else "experiment output artifact paths are missing or unsafe", id=identifier))
    status = "PASS" if checks and all(item["status"] == "PASS" for item in checks) else "FAIL"
    return {"status": status, "checks": checks, "experiment_ids": sorted(seen)}
