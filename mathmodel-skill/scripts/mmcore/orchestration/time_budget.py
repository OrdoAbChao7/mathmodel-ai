"""Contest timeline and evidence-based stopping policy."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _parse(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def evaluate_budget(config: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    """Return a structured timeline state; missing orchestration is non-fatal."""
    if not isinstance(config, dict):
        return {"status": "FAIL", "errors": ["configuration must be an object"]}
    settings = config.get("orchestration")
    if settings is None:
        return {"status": "UNCONFIGURED", "remaining_seconds": None, "milestones": {}}
    if not isinstance(settings, dict):
        return {"status": "FAIL", "errors": ["orchestration must be an object"]}
    start = _parse(settings.get("contest_start"))
    deadline = _parse(settings.get("contest_deadline"))
    if settings.get("contest_start") is None and settings.get("contest_deadline") is None:
        return {"status": "UNCONFIGURED", "remaining_seconds": None, "milestones": {}, "submission_buffer_seconds": 0, "exploration_threshold_seconds": 0}
    if start is None or deadline is None or deadline <= start:
        return {"status": "FAIL", "errors": ["contest_start and contest_deadline must be ordered ISO timestamps"]}
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    remaining = int((deadline - current).total_seconds())
    if current < start:
        status = "NOT_STARTED"
    elif remaining < 0:
        status = "EXPIRED"
    else:
        status = "ACTIVE"
    raw_milestones = settings.get("milestones", {})
    if not isinstance(raw_milestones, dict):
        return {"status": "FAIL", "errors": ["milestones must be an object"]}
    milestones = {}
    for name, value in raw_milestones.items():
        point = _parse(value)
        if point is None:
            return {"status": "FAIL", "errors": [f"milestone {name} must be an ISO timestamp"]}
        milestones[name] = "PASSED" if current >= point else "PENDING"
    buffer_value = settings.get("submission_buffer_seconds", 0)
    threshold = settings.get("exploration_threshold_seconds", 0)
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in (buffer_value, threshold)):
        return {"status": "FAIL", "errors": ["time thresholds must be non-negative integers"]}
    return {"status": status, "contest_start": start.isoformat(), "contest_deadline": deadline.isoformat(), "remaining_seconds": remaining, "submission_buffer_seconds": buffer_value, "exploration_threshold_seconds": threshold, "milestones": milestones}


def stopping_decision(evidence: dict[str, Any], budget: dict[str, Any]) -> dict[str, Any]:
    """Stop model search only when quality evidence and time policy agree."""
    if not isinstance(evidence, dict) or not isinstance(budget, dict):
        return {"action": "CONTINUE_MODEL_SEARCH", "reason": "malformed evidence or budget"}
    required = evidence.get("selected_beats_baseline") is True and evidence.get("validation_passed") is True and evidence.get("open_critical") == 0
    remaining = budget.get("remaining_seconds")
    threshold = budget.get("exploration_threshold_seconds")
    if required and budget.get("status") == "ACTIVE" and isinstance(remaining, int) and isinstance(threshold, int) and remaining <= threshold:
        return {"action": "STOP_MODEL_SEARCH", "next_action": "FOCUS_ON_VALIDATION_AND_PAPER", "reason": "quality evidence passed and exploration time is below threshold"}
    return {"action": "CONTINUE_MODEL_SEARCH", "reason": "quality evidence or time condition is incomplete"}
