"""Resumable, bounded, time-aware pipeline orchestration."""

from __future__ import annotations

import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from .time_budget import evaluate_budget


_STAGES = ("build", "audit", "package")


def _state_path(project: Path) -> Path:
    return Path(project).resolve() / ".mathmodel" / "orchestration-state.json"


def _load_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"schema_version": 1, "stages": {}, "attempts": []}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {"schema_version": 1, "stages": {}, "attempts": [], "error": "state file is malformed"}
    return state if isinstance(state, dict) else {"schema_version": 1, "stages": {}, "attempts": [], "error": "state root must be an object"}


def _save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _default_runner(project: Path, stage: str) -> dict[str, Any]:
    script = Path(__file__).resolve().parents[1] / "mathmodel.py"
    completed = subprocess.run([sys.executable, str(script), stage, str(project), "--json"], cwd=project, capture_output=True, text=True, check=False)
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        payload = {"status": "FAIL", "stdout": completed.stdout, "stderr": completed.stderr}
    if not isinstance(payload, dict):
        payload = {"status": "FAIL", "stdout": completed.stdout, "stderr": completed.stderr}
    payload.setdefault("status", "PASS" if completed.returncode == 0 else "FAIL")
    return payload


def run_parallel(tasks: list[tuple[str, Callable[[], Any]]], max_workers: int = 2) -> dict[str, Any]:
    """Run independent read-only tasks concurrently and return every result."""
    if not isinstance(tasks, list) or not tasks or isinstance(max_workers, bool) or not isinstance(max_workers, int) or max_workers < 1:
        return {"status": "FAIL", "results": {}, "errors": ["tasks and max_workers are invalid"]}
    results: dict[str, Any] = {}
    errors: list[dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=min(max_workers, len(tasks))) as pool:
        futures = {pool.submit(task): name for name, task in tasks if isinstance(name, str) and callable(task)}
        if len(futures) != len(tasks):
            return {"status": "FAIL", "results": {}, "errors": ["each task must contain a name and callable"]}
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as exc:  # noqa: BLE001 - convert worker faults to evidence
                errors.append({"task": name, "error": str(exc)})
    return {"status": "PASS" if not errors else "FAIL", "results": results, "errors": errors}


def run_pipeline(project: Path, config: dict[str, Any], runner: Callable[[str], dict[str, Any]] | None = None, *, now: datetime | None = None, resume: bool = False) -> dict[str, Any]:
    """Execute build→audit→package with resumable state and bounded retries."""
    root = Path(project).resolve()
    settings = config.get("orchestration", {}) if isinstance(config, dict) else None
    if settings is None or not isinstance(settings, dict):
        return {"status": "FAIL", "errors": ["orchestration must be an object"]}
    stages = settings.get("stages", list(_STAGES))
    retries = settings.get("max_retries", 0)
    if not isinstance(stages, list) or not stages or any(stage not in _STAGES for stage in stages) or isinstance(retries, bool) or not isinstance(retries, int) or retries < 0 or retries > 5:
        return {"status": "FAIL", "errors": ["stages or max_retries is invalid"]}
    budget = evaluate_budget(config, now)
    if budget.get("status") == "FAIL":
        return {"status": "FAIL", "budget": budget, "errors": budget.get("errors", [])}
    if budget.get("status") == "EXPIRED" or (budget.get("status") == "ACTIVE" and budget.get("remaining_seconds", 0) <= budget.get("submission_buffer_seconds", 0)):
        return {"status": "BLOCKED_TIME_BUDGET", "budget": budget, "stages": {}}
    path = _state_path(root)
    state = _load_state(path) if resume else {"schema_version": 1, "stages": {}, "attempts": []}
    if state.get("error") or state.get("schema_version") != 1:
        return {"status": "FAIL", "errors": [state.get("error", "orchestration state schema is unsupported")]}
    call = runner or (lambda stage: _default_runner(root, stage))
    results: dict[str, Any] = {}
    for stage in stages:
        if resume and isinstance(state.get("stages", {}).get(stage), dict) and state["stages"][stage].get("status") == "PASS":
            results[stage] = state["stages"][stage]
            continue
        outcome: dict[str, Any] = {"status": "FAIL"}
        for attempt in range(retries + 1):
            outcome = call(stage)
            if not isinstance(outcome, dict):
                outcome = {"status": "FAIL", "error": "runner must return an object"}
            state.setdefault("attempts", []).append({"stage": stage, "attempt": attempt + 1, "status": outcome.get("status")})
            if outcome.get("status") == "PASS":
                break
        state.setdefault("stages", {})[stage] = outcome
        _save_state(path, state)
        results[stage] = outcome
        if outcome.get("status") != "PASS":
            return {"status": "FAIL", "budget": budget, "stages": results, "state": str(path)}
    return {"status": "PASS", "budget": budget, "stages": results, "state": str(path), "resumed": resume}
