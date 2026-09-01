"""Fail-closed authority and semantic-status primitives for MathModel-AI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SUPPORTED_SCHEMA_VERSION = 1
STATUSES = {"PASS", "FAIL", "UNASSESSED", "CONFLICT"}


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


def resolve_conflict(conflict: Any) -> dict[str, str]:
    """Keep unresolved conflicts unassessed; only an explicit resolution passes."""
    if not isinstance(conflict, dict):
        return {"status": "FAIL", "reason": "conflict record must be an object"}
    status = conflict.get("status")
    if status in {"RESOLVED", "ACCEPTED"} and conflict.get("resolution"):
        return {"status": "PASS", "reason": "explicit resolution recorded"}
    if status in {"OPEN", "PENDING", "CONFLICT"}:
        return {"status": "UNASSESSED", "reason": "conflict requires an explicit decision"}
    return {"status": "FAIL", "reason": "invalid conflict status"}


def accept_external_status(status: Any) -> str:
    """Classify external output as advisory; local gates remain authoritative."""
    if not isinstance(status, str):
        return "REJECTED"
    if "RELEASE=PASS" in status or status.strip() == "PASS":
        return "REJECTED"
    return "ADVISORY" if status.strip() else "REJECTED"
