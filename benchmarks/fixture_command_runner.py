"""Run a registered local fixture command and emit a benchmark result."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _result(status: str, variant: str, error: str | None = None) -> dict[str, object]:
    score = 0.78 if variant == "candidate" else 0.55
    diversity = 0.72 if variant == "candidate" else 0.40
    payload: dict[str, object] = {
        "status": status,
        "control": {"provider": "deterministic-fixture", "model": "fixture-v1", "budget": 100, "evidence": "repository-fixtures"},
        "metrics": {
            "problem_interpretation_accuracy": score,
            "candidate_diversity": diversity,
            "model_appropriateness": score,
            "baseline_quality": score,
            "validation_completeness": score,
            "unsupported_claim_count": 0,
            "critical_reviewer_findings": 0,
            "data_leakage_incidents": 0,
            "reproducibility_failures": 0,
            "cross_question_inconsistencies": 0,
            "citation_errors": 0,
            "paper_result_mismatch": 0,
            "judge_view_clarity": score,
            "runtime": 1.0,
            "token_context_cost": 100.0,
            "human_intervention_count": 0,
        },
    }
    if error:
        payload["error"] = error
    return payload


def main() -> int:
    try:
        case = json.loads(os.environ["MATHMODEL_BENCHMARK_CASE"])
        command = case.get("benchmark_command")
        if not isinstance(command, list) or not command or any(not isinstance(item, str) or not item for item in command):
            raise ValueError("case benchmark_command must be a non-empty string array")
        with tempfile.TemporaryDirectory(prefix="mathmodel-benchmark-") as temporary:
            sandbox = Path(temporary) / "case"
            shutil.copytree(Path.cwd(), sandbox)
            child_environment = os.environ.copy()
            child_environment["MATHMODEL_REPO_ROOT"] = str(Path(__file__).resolve().parents[1])
            completed = subprocess.run(
                command,
                cwd=sandbox,
                env=child_environment,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
                check=False,
            )
        if completed.returncode != 0:
            payload = _result("FAIL", os.environ.get("MATHMODEL_BENCHMARK_VARIANT", ""), f"fixture command exited {completed.returncode}")
            payload["stdout"] = completed.stdout[-2000:]
            payload["stderr"] = completed.stderr[-2000:]
        else:
            payload = _result("PASS", os.environ.get("MATHMODEL_BENCHMARK_VARIANT", ""))
    except (KeyError, OSError, subprocess.TimeoutExpired, ValueError, json.JSONDecodeError) as exc:
        payload = _result("FAIL", os.environ.get("MATHMODEL_BENCHMARK_VARIANT", ""), str(exc))
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
