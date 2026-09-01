"""Fail-closed authority and semantic-status primitives for MathModel-AI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SUPPORTED_SCHEMA_VERSION = 1
STATUSES = {"PASS", "FAIL", "UNASSESSED", "CONFLICT"}
_REGISTRY_CONTRACTS = {
    "capability": ("capabilities", ("id", "name", "status"), {"status": {"EXPERIMENTAL", "OPTIONAL", "DEFAULT", "REJECTED"}}),
    "source": ("sources", ("id", "repository", "license", "integration_mode"), {"integration_mode": {"ABSTRACT_INSPIRED", "EXTERNAL_ADAPTER", "REIMPLEMENTED"}}),
}


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON record and return a structured failure instead of guessing."""
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {"status": "FAIL", "error": f"cannot load JSON: {exc}"}
    if not isinstance(value, dict):
        return {"status": "FAIL", "error": "JSON root must be an object"}
    return {"status": "PASS", "record": value}


def validate_schema_version(record: Any, expected: int = SUPPORTED_SCHEMA_VERSION) -> str:
    """Return PASS only for the exact supported schema version."""
    if not isinstance(record, dict) or record.get("schema_version") != expected:
        return "FAIL"
    return "PASS"


def validate_registry(record: Any, kind: str) -> str:
    """Validate the small local registry contract without an optional dependency."""
    if validate_schema_version(record) != "PASS" or kind not in _REGISTRY_CONTRACTS:
        return "FAIL"
    collection, required, enums = _REGISTRY_CONTRACTS[kind]
    items = record.get(collection)
    if not isinstance(items, list):
        return "FAIL"
    for item in items:
        if not isinstance(item, dict) or any(not isinstance(item.get(field), str) or not item[field] for field in required):
            return "FAIL"
        if any(item.get(field) not in allowed for field, allowed in enums.items()):
            return "FAIL"
    return "PASS"


def resolve_conflict(conflict: Any) -> dict[str, str]:
    """Keep unresolved conflicts unassessed; only an explicit resolution passes."""
    if not isinstance(conflict, dict):
        return {"status": "FAIL", "reason": "conflict record must be an object"}
    status = conflict.get("status")
    is_text = lambda value: isinstance(value, str) and bool(value.strip())
    if (
        status in {"RESOLVED", "ACCEPTED"}
        and is_text(conflict.get("resolution"))
        and is_text(conflict.get("policy_id"))
        and is_text(conflict.get("human_decision"))
    ):
        return {"status": "PASS", "reason": "explicit resolution recorded"}
    if status in {"OPEN", "PENDING", "CONFLICT", "RESOLVED", "ACCEPTED"}:
        return {"status": "UNASSESSED", "reason": "conflict requires an explicit decision"}
    return {"status": "FAIL", "reason": "invalid conflict status"}


def accept_external_status(status: Any) -> str:
    """Classify external output as advisory; local gates remain authoritative."""
    if not isinstance(status, str):
        return "REJECTED"
    if "RELEASE=PASS" in status or status.strip() == "PASS":
        return "REJECTED"
    return "ADVISORY" if status.strip() else "REJECTED"
