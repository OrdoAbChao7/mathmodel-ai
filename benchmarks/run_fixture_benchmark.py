"""Execute a deterministic local A/B smoke benchmark through the real harness."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
SCRIPTS = PROJECT / "mathmodel-skill" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from mmcore.benchmark import load_case_registry, run_ab_benchmark, write_benchmark_report


def _result(case: dict, repeat: int, score: float, diversity: float) -> dict:
    return {
        "status": "PASS",
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
        "case_id": case["case_id"],
        "repeat": repeat,
    }


def main() -> int:
    project = PROJECT
    registry = load_case_registry(project, ROOT / "cases" / "registry.json")
    report = run_ab_benchmark(
        project,
        registry,
        lambda case, repeat: _result(case, repeat, 0.55, 0.40),
        lambda case, repeat: _result(case, repeat, 0.78, 0.72),
        repeats=3,
    )
    report["run_config"] = "benchmarks/configs/local-fixture-benchmark.json"
    report["report_path"] = write_benchmark_report(project, report)
    print(json.dumps({"status": report["status"], "promotion": report.get("promotion"), "report_path": report["report_path"], "records": report.get("baseline", {}).get("records")}, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
