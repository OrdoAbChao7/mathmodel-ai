"""Execute a deterministic local A/B smoke benchmark through the real harness."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
SCRIPTS = PROJECT / "mathmodel-skill" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from mmcore.benchmark import load_case_registry, run_configured_benchmark, write_benchmark_report


def main() -> int:
    project = PROJECT
    registry = load_case_registry(project, ROOT / "cases" / "registry.json")
    runner = [sys.executable, str(ROOT / "fixture_command_runner.py")]
    config = {"benchmark": {"baseline_command": runner, "candidate_command": runner, "timeout_seconds": 120}}
    report = run_configured_benchmark(project, config, registry, repeats=3)
    report["run_config"] = "benchmarks/configs/local-fixture-benchmark.json"
    report["report_path"] = write_benchmark_report(project, report)
    print(json.dumps({"status": report["status"], "promotion": report.get("promotion"), "report_path": report["report_path"], "records": report.get("baseline", {}).get("records")}, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
