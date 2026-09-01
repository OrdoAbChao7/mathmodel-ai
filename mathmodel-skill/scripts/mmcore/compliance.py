"""Data-driven CUMCM compliance and human-governance checks."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

_DEFAULT_GATES = (
    "H1_PROBLEM_UNDERSTANDING",
    "H2_METHOD_SELECTION",
    "H3_RESULT_VERIFICATION",
    "H4_FINAL_SUBMISSION",
)
_AI_REQUIRED = (
    "id", "timestamp", "agent_role", "model_name", "model_version", "purpose", "stage",
    "prompt_summary", "prompt_hash", "output_artifacts", "accepted", "human_modified",
    "human_verified",
)
_HUMAN_REQUIRED = (
    "id", "gate", "reviewed_artifacts", "reviewer_name", "reviewer_role", "timestamp",
    "decision", "evidence_notes",
)


def _profile() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[2] / "profiles" / "cumcm" / "profile.yaml"
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return {}
    return value if isinstance(value, dict) else {}


def _check(rule: str, status: str, message: str, **evidence: Any) -> dict[str, Any]:
    return {"rule": rule, "status": status, "message": message, "evidence": evidence}


def _read_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    if not path.is_file():
        return [], ["ledger file is missing"]
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {number}: invalid JSON ({exc.msg})")
            continue
        if not isinstance(value, dict):
            errors.append(f"line {number}: record must be an object")
            continue
        rows.append(value)
    return rows, errors


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _timestamp_ok(value: Any, max_age_days: int) -> bool:
    if not _text(value):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    age = (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds()
    return 0 <= age <= max_age_days * 86400


def _ai_checks(rows: list[dict[str, Any]], errors: list[str], patterns: list[str]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    if errors:
        checks.append(_check("G0-AI-JSONL-001", "FAIL", "AI usage ledger has malformed records", errors=errors))
    if not rows:
        checks.append(_check("G0-AI-LEDGER-001", "FAIL", "AI usage ledger has no usable records"))
    for row in rows:
        missing = [field for field in _AI_REQUIRED if field not in row]
        if missing:
            checks.append(_check("G0-AI-SHAPE-001", "FAIL", "AI usage record is missing required fields", id=row.get("id"), missing=missing))
            continue
        serialized = json.dumps(row, ensure_ascii=False)
        sensitive = [pattern for pattern in patterns if re.search(pattern, serialized, re.IGNORECASE)]
        valid_lists = isinstance(row["output_artifacts"], list) and bool(row["output_artifacts"])
        verified = row["human_verified"] is True and (_text(row.get("human_review_id")) if row["accepted"] is True else True)
        if sensitive or not valid_lists or not verified or not _text(row["prompt_hash"]):
            checks.append(_check("G0-AI-INTEGRITY-001", "FAIL", "AI usage record fails integrity requirements", id=row.get("id"), sensitive=sensitive, verified=verified))
    if rows and not any(check["status"] == "FAIL" for check in checks):
        checks.append(_check("G0-AI-LEDGER-001", "PASS", "AI usage ledger is valid", records=len(rows)))
    return checks


def _reviewed_artifacts(project: Path, values: Any) -> tuple[bool, list[str]]:
    if not isinstance(values, list) or not values:
        return False, ["reviewed_artifacts must be a non-empty array"]
    root = Path(project).resolve()
    invalid: list[str] = []
    for value in values:
        if not isinstance(value, str) or not value.strip():
            invalid.append(str(value))
            continue
        candidate = Path(value)
        if candidate.is_absolute():
            invalid.append(value)
            continue
        resolved = (root / candidate).resolve()
        if (resolved != root and root not in resolved.parents) or not resolved.is_file():
            invalid.append(value)
    return not invalid, invalid


def _human_checks(project: Path, rows: list[dict[str, Any]], errors: list[str], gates: tuple[str, ...], max_age_days: int) -> tuple[list[dict[str, Any]], list[str]]:
    checks: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        missing = [field for field in _HUMAN_REQUIRED if field not in row]
        gate = row.get("gate")
        if missing:
            checks.append(_check("G0-HUMAN-SHAPE-001", "FAIL", "human review record is missing required fields", id=row.get("id"), missing=missing))
            continue
        seen.add(gate)
        artifacts_ok, invalid_artifacts = _reviewed_artifacts(project, row["reviewed_artifacts"])
        valid = (
            gate in gates and artifacts_ok
            and _text(row["reviewer_name"]) and _text(row["reviewer_role"]) and _text(row["evidence_notes"])
            and row["decision"] == "APPROVED" and _timestamp_ok(row["timestamp"], max_age_days)
        )
        if not valid:
            checks.append(_check("G0-HUMAN-INTEGRITY-001", "FAIL", "human review record is not an accepted current signoff", id=row.get("id"), gate=gate, invalid_reviewed_artifacts=invalid_artifacts))
    missing_gates = sorted(set(gates) - seen)
    if errors:
        checks.append(_check("G0-HUMAN-JSONL-001", "FAIL", "human review ledger has malformed records", errors=errors))
    if missing_gates:
        checks.append(_check("G0-HUMAN-COVERAGE-001", "FAIL", "required human gates are missing", missing=missing_gates))
    if rows and not missing_gates and not any(check["status"] == "FAIL" for check in checks):
        checks.append(_check("G0-HUMAN-COVERAGE-001", "PASS", "all required human gates have current signoff", gates=list(gates)))
    return checks, missing_gates


def evaluate_compliance(project: Path, config: dict[str, Any]) -> dict[str, Any]:
    """Evaluate G0 and H1-H4; formal modes fail closed, research mode is N/A."""
    profile = _profile()
    mode = config.get("execution_mode", "research_autonomous")
    gates = tuple(profile.get("required_human_gates", _DEFAULT_GATES))
    formal_modes = set(profile.get("formal_modes", ("competition_assisted", "competition_max")))
    if mode not in formal_modes:
        return {"status": "NOT_APPLICABLE", "mode": mode, "required_human_gates": list(gates), "checks": []}
    ai_rules_path = Path(__file__).resolve().parents[2] / "profiles" / "cumcm" / "ai-rules.yaml"
    try:
        ai_rules = yaml.safe_load(ai_rules_path.read_text(encoding="utf-8")) or {}
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        ai_rules = {}
    patterns = ai_rules.get("forbid_sensitive_patterns", ["api[_-]?key", "token", "secret"])
    max_age = int(ai_rules.get("max_review_age_days", 30))
    ai_rows, ai_errors = _read_jsonl(Path(project) / "artifacts" / "ai-usage-ledger.jsonl")
    human_rows, human_errors = _read_jsonl(Path(project) / "artifacts" / "human-review-ledger.jsonl")
    checks = _ai_checks(ai_rows, ai_errors, patterns if isinstance(patterns, list) else [])
    human_checks, missing = _human_checks(Path(project), human_rows, human_errors, gates, max_age)
    checks.extend(human_checks)
    status = "PASS" if checks and all(check["status"] == "PASS" for check in checks) else "FAIL"
    return {"status": status, "mode": mode, "profile": profile.get("profile_id"), "rule_version": profile.get("rule_version"), "required_human_gates": list(gates), "missing_human_gates": missing, "checks": checks}


def requires_formal_compliance(config: dict[str, Any]) -> bool:
    """Return whether the active profile makes G0 mandatory for this config."""
    profile = _profile()
    return config.get("execution_mode", "research_autonomous") in set(
        profile.get("formal_modes", ("competition_assisted", "competition_max"))
    )


def evaluate_human_checkpoints(project: Path, config: dict[str, Any], required_gates: tuple[str, ...]) -> dict[str, Any]:
    """Check only the human gates needed before one orchestrated stage.

    This is deliberately separate from the final all-gates compliance report:
    a formal pipeline may proceed from H1/H2 to build while H3/H4 are still
    legitimately pending, but it must stop before crossing either checkpoint.
    """
    if not requires_formal_compliance(config):
        return {"status": "NOT_APPLICABLE", "required_human_gates": list(required_gates), "missing_human_gates": [], "checks": []}
    ai_rules_path = Path(__file__).resolve().parents[2] / "profiles" / "cumcm" / "ai-rules.yaml"
    try:
        ai_rules = yaml.safe_load(ai_rules_path.read_text(encoding="utf-8")) or {}
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        ai_rules = {}
    max_age = int(ai_rules.get("max_review_age_days", 30))
    human_rows, human_errors = _read_jsonl(Path(project) / "artifacts" / "human-review-ledger.jsonl")
    checks, missing = _human_checks(Path(project), human_rows, human_errors, required_gates, max_age)
    failed = [check for check in checks if check.get("status") == "FAIL"]
    return {
        "status": "PASS" if not missing and not failed else "BLOCKED_HUMAN_INPUT",
        "required_human_gates": list(required_gates),
        "missing_human_gates": missing,
        "checks": checks,
    }
