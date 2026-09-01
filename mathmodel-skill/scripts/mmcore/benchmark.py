"""Controlled A/B benchmark harness for capability promotion decisions."""

from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
from pathlib import Path
from typing import Any, Callable

from .schema import supported_artifact_schema


class BenchmarkError(ValueError):
    """Raised when a benchmark registry or result violates its contract."""


_PROBLEM_TYPES = {
    "forecasting",
    "optimization",
    "evaluation",
    "mechanism",
    "simulation",
    "classification",
    "statistics",
    "hybrid",
}
_LOWER_IS_BETTER = {
    "unsupported_claim_count",
    "critical_reviewer_findings",
    "data_leakage_incidents",
    "reproducibility_failures",
    "cross_question_inconsistencies",
    "citation_errors",
    "paper_result_mismatch",
    "runtime",
    "token_context_cost",
    "human_intervention_count",
}
_HARD_REGRESSIONS = {
    "data_leakage_incidents",
    "reproducibility_failures",
    "critical_reviewer_findings",
    "cross_question_inconsistencies",
    "citation_errors",
    "paper_result_mismatch",
}
_REQUIRED_METRICS = {
    "problem_interpretation_accuracy",
    "candidate_diversity",
    "model_appropriateness",
    "baseline_quality",
    "validation_completeness",
    "unsupported_claim_count",
    "critical_reviewer_findings",
    "data_leakage_incidents",
    "reproducibility_failures",
    "cross_question_inconsistencies",
    "citation_errors",
    "paper_result_mismatch",
    "runtime",
    "token_context_cost",
    "human_intervention_count",
    "judge_view_clarity",
}
_REQUIRED_CONTROL_FIELDS = {"provider", "model", "budget", "evidence"}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _project_path(root: Path, value: Any, name: str) -> Path:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise BenchmarkError(f"{name} must be a non-empty project-relative path")
    path = (root / value).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise BenchmarkError(f"{name} escapes project root") from exc
    return path


def load_case_registry(project: Path, registry_path: Path | str | None = None) -> dict[str, Any]:
    """Load and validate a historical-case registry without executing cases."""
    root = Path(project).resolve()
    path = Path(registry_path) if registry_path is not None else root / "benchmarks" / "cases" / "registry.json"
    path = path if path.is_absolute() else root / path
    try:
        path = path.resolve()
        path.relative_to(root)
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise BenchmarkError(f"invalid benchmark registry: {path}") from exc
    if not supported_artifact_schema(payload) or not isinstance(payload.get("cases"), list) or not payload["cases"]:
        raise BenchmarkError("benchmark registry requires a supported schema_version and a non-empty cases array")
    seen: set[str] = set()
    cases: list[dict[str, Any]] = []
    for index, case in enumerate(payload["cases"]):
        if not isinstance(case, dict):
            raise BenchmarkError(f"cases[{index}] must be an object")
        case_id = case.get("case_id")
        problem_type = case.get("problem_type")
        title = case.get("title")
        if not isinstance(case_id, str) or not case_id or case_id in seen:
            raise BenchmarkError(f"cases[{index}].case_id must be unique and non-empty")
        if not isinstance(title, str) or not title:
            raise BenchmarkError(f"cases[{index}].title must be a non-empty string")
        if not isinstance(case.get("source"), str) or not case["source"].strip():
            raise BenchmarkError(f"cases[{index}].source must be a non-empty provenance reference")
        if problem_type not in _PROBLEM_TYPES:
            raise BenchmarkError(f"cases[{index}].problem_type is unsupported")
        seen.add(case_id)
        normalized = dict(case)
        if "project" in case:
            resolved = _project_path(root, case["project"], f"cases[{index}].project")
            if case.get("enabled", True) and not resolved.is_dir():
                raise BenchmarkError(f"enabled case project is missing: {case['project']}")
            normalized["project"] = resolved.relative_to(root).as_posix()
        elif case.get("enabled", True):
            raise BenchmarkError(f"enabled case {case_id} requires project")
        normalized.setdefault("enabled", True)
        cases.append(normalized)
    return {"schema_version": 1, "cases": cases, "registry_path": path.relative_to(root).as_posix()}


def _validate_result(result: Any, case_id: str, variant: str) -> dict[str, Any]:
    if not isinstance(result, dict) or result.get("status") != "PASS":
        raise BenchmarkError(f"{variant} failed for case {case_id}")
    metrics = result.get("metrics")
    if not isinstance(metrics, dict):
        raise BenchmarkError(f"{variant} metrics are missing for case {case_id}")
    missing = sorted(_REQUIRED_METRICS - metrics.keys())
    if missing:
        raise BenchmarkError(f"{variant} metrics missing for case {case_id}: {', '.join(missing)}")
    clean = dict(result)
    clean["metrics"] = {}
    for name in sorted(_REQUIRED_METRICS):
        value = metrics[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise BenchmarkError(f"{variant} metric {name} is not a finite number for case {case_id}")
        clean["metrics"][name] = float(value)
    control = result.get("control")
    if not isinstance(control, dict) or not _REQUIRED_CONTROL_FIELDS <= control.keys():
        raise BenchmarkError(f"{variant} control metadata is missing for case {case_id}")
    clean["control"] = control
    return clean


def _aggregate(records: list[dict[str, Any]]) -> dict[str, float]:
    values: dict[str, list[float]] = {}
    for record in records:
        for name, value in record["metrics"].items():
            values.setdefault(name, []).append(float(value))
    return {name: sum(items) / len(items) for name, items in sorted(values.items())}


def compare_metrics(baseline: dict[str, float], candidate: dict[str, float]) -> dict[str, dict[str, Any]]:
    """Return signed deltas and normalized improvements for every metric."""
    if set(baseline) != set(candidate):
        raise BenchmarkError("baseline and candidate metric sets must match")
    comparison: dict[str, dict[str, Any]] = {}
    for name in sorted(baseline):
        base = float(baseline[name])
        new = float(candidate[name])
        if not math.isfinite(base) or not math.isfinite(new):
            raise BenchmarkError(f"metric {name} must contain finite values")
        delta = new - base
        relative = delta / abs(base) if base else delta
        if name in _LOWER_IS_BETTER:
            improvement = base - new
        else:
            improvement = delta
        comparison[name] = {
            "baseline": base,
            "candidate": new,
            "delta": delta,
            "relative_delta": relative,
            "direction": "lower" if name in _LOWER_IS_BETTER else "higher",
            "improvement": improvement,
        }
    return comparison


def promotion_decision(comparison: dict[str, dict[str, Any]], meaningful_threshold: float = 0.01) -> dict[str, Any]:
    """Apply the conservative DEFAULT/OPTIONAL/REJECTED promotion policy."""
    hard: list[str] = []
    meaningful: list[str] = []
    for name, item in comparison.items():
        improvement = float(item.get("improvement", 0))
        baseline = abs(float(item.get("baseline", 0)))
        relative = improvement / baseline if baseline else improvement
        if name in _HARD_REGRESSIONS and improvement < 0:
            hard.append(name)
        if improvement > 0 and relative >= meaningful_threshold:
            meaningful.append(name)
    if hard:
        status = "REJECTED"
    elif meaningful:
        status = "DEFAULT"
    else:
        status = "OPTIONAL"
    return {"status": status, "meaningful_improvements": sorted(meaningful), "hard_regressions": sorted(hard), "threshold": meaningful_threshold}


def run_ab_benchmark(
    project: Path,
    registry: dict[str, Any],
    baseline_runner: Callable[[dict[str, Any], int], dict[str, Any]],
    candidate_runner: Callable[[dict[str, Any], int], dict[str, Any]],
    *,
    repeats: int = 1,
) -> dict[str, Any]:
    """Run paired repetitions under identical case and control constraints."""
    root = Path(project).resolve()
    if isinstance(repeats, bool) or not isinstance(repeats, int) or not 1 <= repeats <= 20:
        return {"status": "FAIL", "errors": ["repeats must be an integer in [1, 20]"]}
    if not isinstance(registry, dict) or not isinstance(registry.get("cases"), list):
        return {"status": "FAIL", "errors": ["registry is invalid"]}
    baseline_records: list[dict[str, Any]] = []
    candidate_records: list[dict[str, Any]] = []
    case_reports: list[dict[str, Any]] = []
    expected_control: str | None = None
    try:
        for case in registry["cases"]:
            if not isinstance(case, dict) or not case.get("enabled", True):
                continue
            case_id = case.get("case_id", "unknown")
            paired: list[dict[str, Any]] = []
            for repeat in range(repeats):
                try:
                    base_result = baseline_runner(case, repeat)
                    candidate_result = candidate_runner(case, repeat)
                except Exception as exc:  # noqa: BLE001 - benchmark failures are evidence
                    raise BenchmarkError(f"runner failed for case {case_id}, repeat {repeat}: {exc}") from exc
                base = _validate_result(base_result, case_id, "baseline")
                candidate = _validate_result(candidate_result, case_id, "candidate")
                base_control = _canonical(base["control"])
                candidate_control = _canonical(candidate["control"])
                if base_control != candidate_control:
                    raise BenchmarkError(f"control variables differ for case {case_id}, repeat {repeat}")
                if expected_control is None:
                    expected_control = base_control
                elif base_control != expected_control:
                    raise BenchmarkError(f"control variables drift between repeats for case {case_id}, repeat {repeat}")
                baseline_records.append(base)
                candidate_records.append(candidate)
                paired.append({"repeat": repeat, "baseline": base, "candidate": candidate})
            case_reports.append({"case_id": case_id, "problem_type": case.get("problem_type"), "repeats": paired})
        if not baseline_records:
            raise BenchmarkError("registry contains no enabled cases")
        baseline_metrics = _aggregate(baseline_records)
        candidate_metrics = _aggregate(candidate_records)
        comparison = compare_metrics(baseline_metrics, candidate_metrics)
        return {
            "status": "PASS",
            "registry": registry.get("registry_path"),
            "cases": case_reports,
            "controls": {"same_case": True, "paired": True, "repeats": repeats},
            "baseline": {"metrics": baseline_metrics, "records": len(baseline_records)},
            "candidate": {"metrics": candidate_metrics, "records": len(candidate_records)},
            "comparison": comparison,
            "promotion": promotion_decision(comparison),
        }
    except (BenchmarkError, OSError, TypeError, ValueError) as exc:
        return {"status": "FAIL", "errors": [str(exc)], "cases": case_reports}


def _command_runner(project: Path, command: Any, variant: str, timeout_seconds: int) -> Callable[[dict[str, Any], int], dict[str, Any]]:
    if not isinstance(command, list) or not command or any(not isinstance(item, str) or not item for item in command):
        raise BenchmarkError(f"benchmark.{variant}_command must be a non-empty array of strings")

    def invoke(case: dict[str, Any], repeat: int) -> dict[str, Any]:
        case_project = project
        if isinstance(case.get("project"), str):
            case_project = _project_path(project, case["project"], f"case {case.get('case_id')}.project")
        environment = os.environ.copy()
        environment.update({
            "MATHMODEL_BENCHMARK_CASE": _canonical(case),
            "MATHMODEL_BENCHMARK_CASE_ID": str(case.get("case_id", "")),
            "MATHMODEL_BENCHMARK_VARIANT": variant,
            "MATHMODEL_BENCHMARK_REPEAT": str(repeat),
        })
        try:
            completed = subprocess.run(command, cwd=case_project, env=environment, capture_output=True, text=True, timeout=timeout_seconds, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {"status": "FAIL", "error": f"{variant} command failed: {exc}"}
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError:
            return {"status": "FAIL", "error": f"{variant} command did not return JSON", "stdout": completed.stdout, "stderr": completed.stderr}
        if not isinstance(payload, dict):
            return {"status": "FAIL", "error": f"{variant} command returned a non-object JSON value"}
        if completed.returncode != 0:
            payload.setdefault("status", "FAIL")
        return payload

    return invoke


def run_configured_benchmark(project: Path, config: dict[str, Any], registry: dict[str, Any], *, repeats: int = 1) -> dict[str, Any]:
    """Run a benchmark using commands declared by the project configuration."""
    settings = config.get("benchmark") if isinstance(config, dict) else None
    if not isinstance(settings, dict):
        return {"status": "FAIL", "errors": ["benchmark configuration is missing"]}
    timeout = settings.get("timeout_seconds", 300)
    if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout < 1 or timeout > 3600:
        return {"status": "FAIL", "errors": ["benchmark.timeout_seconds must be an integer in [1, 3600]"]}
    try:
        baseline = _command_runner(Path(project).resolve(), settings.get("baseline_command"), "baseline", timeout)
        candidate = _command_runner(Path(project).resolve(), settings.get("candidate_command"), "candidate", timeout)
        return run_ab_benchmark(project, registry, baseline, candidate, repeats=repeats)
    except BenchmarkError as exc:
        return {"status": "FAIL", "errors": [str(exc)]}


def write_benchmark_report(project: Path, report: dict[str, Any]) -> str:
    """Persist a content-addressed comparison report under benchmarks/reports."""
    root = Path(project).resolve()
    payload = json.loads(_canonical(report))
    digest = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()[:12]
    destination = root / "benchmarks" / "reports" / f"benchmark-{digest}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(destination)
