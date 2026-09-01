"""Resumable, bounded, time-aware pipeline orchestration."""

from __future__ import annotations

import json
import hashlib
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


def _outcome_hash(outcome: dict[str, Any]) -> str:
    encoded = json.dumps(outcome, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _evidence_snapshot(project: Path, stage: str) -> dict[str, Any] | None:
    """Hash the on-disk outputs that make a completed stage resumable."""
    root = Path(project).resolve()
    if stage == "build":
        # audit legitimately refreshes quality-report.json; build-report.json is
        # the stable completion marker for the earlier stage.
        paths = [root / "build" / "build-report.json"]
    elif stage == "audit":
        paths = [root / "build" / "quality-report.json"]
    elif stage == "package":
        paths = sorted((root / "release").glob("*-package-manifest.json"))
    else:
        return None
    if not paths or any(not path.is_file() for path in paths):
        return None
    digest = hashlib.sha256()
    relative_paths: list[str] = []
    for path in paths:
        relative = path.relative_to(root).as_posix()
        relative_paths.append(relative)
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return {"hash": digest.hexdigest(), "paths": relative_paths}


def _stage_outputs_pass(project: Path, stage: str) -> bool:
    """Require the persisted files themselves to contain a passing result."""
    root = Path(project).resolve()
    try:
        quality_path = root / "build" / "quality-report.json"
        if stage in {"build", "audit"}:
            quality = json.loads(quality_path.read_text(encoding="utf-8"))
            quality_section = quality.get("quality") if isinstance(quality, dict) else None
            if not isinstance(quality_section, dict) or quality_section.get("release_status") != "PASS":
                return False
            gates = quality.get("page_gates")
            if not isinstance(gates, list) or not gates or any(not isinstance(gate, dict) or gate.get("status") != "PASS" for gate in gates):
                return False
            if stage == "audit":
                return True
        if stage == "build":
            report = json.loads((root / "build" / "build-report.json").read_text(encoding="utf-8"))
            return isinstance(report, dict) and report.get("status") == "PASS"
        if stage == "package":
            manifests = sorted((root / "release").glob("*-package-manifest.json"))
            if not manifests:
                return False
            manifest = json.loads(manifests[-1].read_text(encoding="utf-8"))
            if not isinstance(manifest, dict) or manifest.get("status") != "PASS":
                return False
            pdf = manifest.get("pdf")
            if isinstance(pdf, dict) and isinstance(pdf.get("path"), str):
                pdf_path = (root / pdf["path"]).resolve()
                pdf_path.relative_to(root)
                if not pdf_path.is_file():
                    return False
            return True
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, ValueError):
        return False
    return False


def _stage_passes(outcome: dict[str, Any], stage: str) -> bool:
    """Do not let an injected runner bypass the stage-specific gate contract."""
    if not isinstance(outcome, dict) or outcome.get("status") != "PASS":
        return False
    if outcome.get("stage") not in (None, stage):
        return False
    if stage in {"build", "audit"}:
        gates = outcome.get("page_gates")
        return isinstance(gates, list) and bool(gates) and all(isinstance(gate, dict) and gate.get("status") == "PASS" for gate in gates)
    return isinstance(outcome.get("checks"), list)


def _default_runner(project: Path, stage: str, timeout_seconds: int = 300) -> dict[str, Any]:
    script = Path(__file__).resolve().parents[2] / "mathmodel.py"
    try:
        completed = subprocess.run([sys.executable, str(script), stage, str(project), "--json"], cwd=project, capture_output=True, text=True, timeout=max(1, timeout_seconds), check=False)
    except subprocess.TimeoutExpired as exc:
        return {"status": "FAIL", "error": f"stage exceeded orchestration timeout: {exc}"}
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
    if not isinstance(tasks, list) or not tasks or isinstance(max_workers, bool) or not isinstance(max_workers, int) or max_workers < 1 or any(not isinstance(item, (list, tuple)) or len(item) != 2 or not isinstance(item[0], str) or not item[0] or not callable(item[1]) for item in tasks) or len({item[0] for item in tasks}) != len(tasks):
        return {"status": "FAIL", "results": {}, "errors": ["tasks and max_workers are invalid"]}
    results: dict[str, Any] = {}
    errors: list[dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=min(max_workers, len(tasks))) as pool:
        futures = {pool.submit(task): name for name, task in tasks}
        if len(futures) != len(tasks):
            return {"status": "FAIL", "results": {}, "errors": ["task names must be unique"]}
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as exc:  # noqa: BLE001 - convert worker faults to evidence
                errors.append({"task": name, "error": str(exc)})
    return {"status": "PASS" if not errors else "FAIL", "results": results, "errors": errors}


def run_pipeline(project: Path, config: dict[str, Any], runner: Callable[[str], dict[str, Any]] | None = None, *, now: datetime | None = None, clock: Callable[[], datetime] | None = None, resume: bool = False) -> dict[str, Any]:
    """Execute build→audit→package with resumable state and bounded retries."""
    root = Path(project).resolve()
    settings = config.get("orchestration", {}) if isinstance(config, dict) else None
    if settings is None or not isinstance(settings, dict):
        return {"status": "FAIL", "errors": ["orchestration must be an object"]}
    stages = settings.get("stages", list(_STAGES))
    retries = settings.get("max_retries", 0)
    if not isinstance(stages, list) or stages != list(_STAGES) or isinstance(retries, bool) or not isinstance(retries, int) or retries < 0 or retries > 5:
        return {"status": "FAIL", "errors": ["stages or max_retries is invalid"]}
    budget = evaluate_budget(config, now)
    if budget.get("status") == "FAIL":
        return {"status": "FAIL", "budget": budget, "errors": budget.get("errors", [])}
    if budget.get("status") == "EXPIRED" or (budget.get("status") == "ACTIVE" and budget.get("remaining_seconds", 0) <= budget.get("submission_buffer_seconds", 0)):
        return {"status": "BLOCKED_TIME_BUDGET", "budget": budget, "stages": {}}
    path = _state_path(root)
    state = _load_state(path) if resume else {"schema_version": 1, "stages": {}, "attempts": []}
    if state.get("error") or state.get("schema_version") != 1 or not isinstance(state.get("stages"), dict) or not isinstance(state.get("attempts"), list):
        return {"status": "FAIL", "errors": [state.get("error", "orchestration state schema is unsupported")]}
    if runner is not None:
        call = runner
    else:
        def call(stage: str) -> dict[str, Any]:
            remaining = budget.get("remaining_seconds")
            timeout = max(1, min(300, remaining - budget.get("submission_buffer_seconds", 0))) if isinstance(remaining, int) and not isinstance(remaining, bool) else 300
            return _default_runner(root, stage, timeout)
    results: dict[str, Any] = {}
    for stage in stages:
        current_budget = evaluate_budget(config, clock() if clock else now)
        if current_budget.get("status") == "FAIL":
            return {"status": "FAIL", "budget": current_budget, "stages": results, "errors": current_budget.get("errors", [])}
        if current_budget.get("status") == "EXPIRED" or (current_budget.get("status") == "ACTIVE" and current_budget.get("remaining_seconds", 0) <= current_budget.get("submission_buffer_seconds", 0)):
            return {"status": "BLOCKED_TIME_BUDGET", "budget": current_budget, "stages": results}
        saved = state.get("stages", {}).get(stage)
        if resume and isinstance(saved, dict) and saved.get("status") == "PASS":
            snapshot = _evidence_snapshot(root, stage)
            saved_result = saved.get("result")
            if (
                not isinstance(saved_result, dict)
                or not _stage_passes(saved_result, stage)
                or saved.get("evidence_hash") != _outcome_hash(saved_result)
                or not isinstance(snapshot, dict)
                or saved.get("project_evidence_hash") != snapshot.get("hash")
                or saved.get("project_evidence_paths") != snapshot.get("paths")
                or not _stage_outputs_pass(root, stage)
            ):
                return {"status": "FAIL", "budget": current_budget, "stages": results, "errors": [f"resume evidence for {stage} is missing or invalid"]}
            results[stage] = saved_result
            continue
        outcome: dict[str, Any] = {"status": "FAIL"}
        for attempt in range(retries + 1):
            try:
                outcome = call(stage)
            except Exception as exc:  # noqa: BLE001 - convert runner faults to structured evidence
                outcome = {"status": "FAIL", "error": str(exc)}
            if not isinstance(outcome, dict):
                outcome = {"status": "FAIL", "error": "runner must return an object"}
            state.setdefault("attempts", []).append({"stage": stage, "attempt": attempt + 1, "status": outcome.get("status")})
            after_budget = evaluate_budget(config, clock() if clock else None if now is None else now)
            if after_budget.get("status") == "EXPIRED" or (after_budget.get("status") == "ACTIVE" and after_budget.get("remaining_seconds", 0) <= after_budget.get("submission_buffer_seconds", 0)):
                return {"status": "BLOCKED_TIME_BUDGET", "budget": after_budget, "stages": results, "state": str(path)}
            if _stage_passes(outcome, stage) and _stage_outputs_pass(root, stage):
                break
        snapshot = _evidence_snapshot(root, stage)
        if not _stage_passes(outcome, stage) or snapshot is None or not _stage_outputs_pass(root, stage):
            outcome = {"status": "FAIL", "stage": stage, "error": "stage output evidence is missing or invalid"}
            snapshot = None
        state.setdefault("stages", {})[stage] = {"status": outcome.get("status"), "evidence_hash": _outcome_hash(outcome), "result": outcome, "project_evidence_hash": snapshot.get("hash") if snapshot else None, "project_evidence_paths": snapshot.get("paths") if snapshot else []}
        _save_state(path, state)
        results[stage] = outcome
        if outcome.get("status") != "PASS":
            return {"status": "FAIL", "budget": budget, "stages": results, "state": str(path)}
    return {"status": "PASS", "budget": budget, "stages": results, "state": str(path), "resumed": resume}
