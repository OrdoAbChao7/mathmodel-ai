import os
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import sys

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mmcore.benchmark import (
    BenchmarkError,
    compare_metrics,
    load_case_registry,
    promotion_decision,
    run_ab_benchmark,
    run_configured_benchmark,
    write_benchmark_report,
)


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "cases" / "forecasting").mkdir(parents=True)
        (self.root / "cases" / "optimization").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def registry(self):
        path = self.root / "registry.json"
        path.write_text(json.dumps({
            "schema_version": 1,
            "cases": [
                {"case_id": "forecast-001", "title": "Forecast fixture", "problem_type": "forecasting", "project": "cases/forecasting", "source": "local-fixture"},
                {"case_id": "optim-001", "title": "Optimization fixture", "problem_type": "optimization", "project": "cases/optimization", "source": "local-fixture"},
            ],
        }), encoding="utf-8")
        return path

    def result(self, case, repeat, *, score, unsupported=0, critical=0, control=None):
        return {
            "status": "PASS",
            "control": control or {"provider": "fixture", "model": "v1", "budget": 100, "evidence": "same"},
            "metrics": {
                "problem_interpretation_accuracy": score,
                "candidate_diversity": score,
                "model_appropriateness": score,
                "baseline_quality": score,
                "validation_completeness": score,
                "unsupported_claim_count": unsupported,
                "critical_reviewer_findings": critical,
                "reproducibility_failures": 0,
                "data_leakage_incidents": 0,
                "cross_question_inconsistencies": 0,
                "citation_errors": 0,
                "paper_result_mismatch": 0,
                "runtime": 1.0,
                "token_context_cost": 100.0,
                "human_intervention_count": 0,
                "judge_view_clarity": score,
            },
        }

    def test_registry_validates_case_types_paths_and_duplicates(self):
        loaded = load_case_registry(self.root, self.registry())
        self.assertEqual([case["case_id"] for case in loaded["cases"]], ["forecast-001", "optim-001"])
        bad = self.root / "bad.json"
        bad.write_text(json.dumps({"schema_version": 1, "cases": [{"case_id": "x", "title": "x", "problem_type": "statistics", "project": "../outside"}]}), encoding="utf-8")
        with self.assertRaises(BenchmarkError):
            load_case_registry(self.root, bad)

    def test_registry_requires_case_provenance(self):
        path = self.root / "missing-source.json"
        path.write_text(json.dumps({
            "schema_version": 1,
            "cases": [{"case_id": "x", "title": "x", "problem_type": "statistics", "project": "cases/forecasting"}],
        }), encoding="utf-8")
        with self.assertRaises(BenchmarkError):
            load_case_registry(self.root, path)

    def test_registry_accepts_all_supported_problem_profiles(self):
        cases = []
        for index, problem_type in enumerate(("forecasting", "optimization", "evaluation", "mechanism", "simulation", "classification", "statistics", "hybrid")):
            case_project = self.root / "cases" / problem_type
            case_project.mkdir(parents=True, exist_ok=True)
            cases.append({
                "case_id": f"case-{index}",
                "title": problem_type,
                "problem_type": problem_type,
                "source": "local-test-fixture",
                "project": f"cases/{problem_type}",
            })
        registry_path = self.root / "all-profiles.json"
        registry_path.write_text(json.dumps({"schema_version": 1, "cases": cases}), encoding="utf-8")
        registry = load_case_registry(self.root, registry_path)
        self.assertEqual(len(registry["cases"]), 8)

    def test_ab_runner_aggregates_and_promotes_meaningful_improvement(self):
        registry = load_case_registry(self.root, self.registry())
        report = run_ab_benchmark(
            self.root,
            registry,
            lambda case, repeat: self.result(case, repeat, score=0.5),
            lambda case, repeat: self.result(case, repeat, score=0.8),
            repeats=2,
        )
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["promotion"]["status"], "DEFAULT")
        self.assertGreater(report["comparison"]["problem_interpretation_accuracy"]["delta"], 0)
        self.assertEqual(report["controls"]["repeats"], 2)

    def test_configured_benchmark_executes_declared_commands(self):
        baseline_script = self.root / "baseline.py"
        candidate_script = self.root / "candidate.py"
        baseline_script.write_text(
            "import json; print(json.dumps({\"status\": \"PASS\", \"control\": {\"provider\": \"cmd\", \"model\": \"v1\", \"budget\": 10, \"evidence\": \"command\"}, \"metrics\": {\"problem_interpretation_accuracy\": 0.5, \"candidate_diversity\": 0.4, \"model_appropriateness\": 0.5, \"baseline_quality\": 0.5, \"validation_completeness\": 0.5, \"unsupported_claim_count\": 0, \"critical_reviewer_findings\": 0, \"data_leakage_incidents\": 0, \"reproducibility_failures\": 0, \"cross_question_inconsistencies\": 0, \"citation_errors\": 0, \"paper_result_mismatch\": 0, \"judge_view_clarity\": 0.5, \"runtime\": 1, \"token_context_cost\": 10, \"human_intervention_count\": 0}}))",
            encoding="utf-8",
        )
        candidate_script.write_text(
            baseline_script.read_text(encoding="utf-8").replace("0.5", "0.8").replace("0.4", "0.7"),
            encoding="utf-8",
        )
        config = {"benchmark": {"baseline_command": [sys.executable, str(baseline_script)], "candidate_command": [sys.executable, str(candidate_script)], "timeout_seconds": 30}}
        registry = load_case_registry(self.root, self.registry())
        report = run_configured_benchmark(self.root, config, registry, repeats=2)
        self.assertEqual(report["status"], "PASS", report)
        self.assertEqual(report["baseline"]["records"], 4)
        self.assertEqual(report["candidate"]["records"], 4)
        self.assertEqual(report["promotion"]["status"], "DEFAULT")

    def test_fixture_command_runner_isolates_case_side_effects(self):
        runner = self.root / "fixture_command_runner.py"
        runner.write_text(
            "import json, os; from pathlib import Path; Path('side-effect.txt').write_text('sandbox-only'); print(json.dumps({'status':'PASS','control':{'provider':'x','model':'x','budget':1,'evidence':'x'},'metrics':{}}))",
            encoding="utf-8",
        )
        case = self.root / "case"
        case.mkdir()
        command_runner = Path(__file__).resolve().parents[2] / "benchmarks" / "fixture_command_runner.py"
        environment = os.environ.copy()
        environment["MATHMODEL_BENCHMARK_CASE"] = json.dumps({"case_id": "isolation", "benchmark_command": [sys.executable, str(runner)]})
        environment["MATHMODEL_BENCHMARK_VARIANT"] = "baseline"
        completed = subprocess.run(
            [sys.executable, str(command_runner)], cwd=case, env=environment,
            capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["status"], "PASS")
        self.assertFalse((case / "side-effect.txt").exists())

    def test_ab_runner_fails_closed_on_control_mismatch(self):
        registry = load_case_registry(self.root, self.registry())
        report = run_ab_benchmark(
            self.root,
            registry,
            lambda case, repeat: self.result(case, repeat, score=0.5),
            lambda case, repeat: self.result(case, repeat, score=0.8, control={"provider": "other", "model": "v2", "budget": 100, "evidence": "same"}),
        )
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any("control" in error.lower() for error in report["errors"]))

    def test_ab_runner_fails_closed_on_runner_exception(self):
        registry = load_case_registry(self.root, self.registry())
        def broken(case, repeat):
            raise RuntimeError("provider unavailable")
        report = run_ab_benchmark(self.root, registry, broken, broken)
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("provider unavailable", report["errors"][0])

    def test_ab_runner_rejects_control_drift_between_repeats(self):
        registry = load_case_registry(self.root, self.registry())
        def baseline(case, repeat):
            return self.result(case, repeat, score=0.5, control={"provider": "fixture", "model": f"v{repeat}", "budget": 100, "evidence": "same"})
        def candidate(case, repeat):
            return self.result(case, repeat, score=0.8, control={"provider": "fixture", "model": f"v{repeat}", "budget": 100, "evidence": "same"})
        report = run_ab_benchmark(self.root, registry, baseline, candidate, repeats=2)
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("drift", report["errors"][0])

    def test_hard_regression_rejects_promotion(self):
        comparison = compare_metrics({"reproducibility_failures": 0, "unsupported_claim_count": 0}, {"reproducibility_failures": 1, "unsupported_claim_count": 0})
        decision = promotion_decision(comparison)
        self.assertEqual(decision["status"], "REJECTED")
        self.assertTrue(decision["hard_regressions"])

    def test_no_improvement_is_optional(self):
        comparison = compare_metrics({"problem_interpretation_accuracy": 0.5}, {"problem_interpretation_accuracy": 0.5})
        self.assertEqual(promotion_decision(comparison)["status"], "OPTIONAL")

    def test_report_writer_is_deterministic_and_creates_reports_directory(self):
        report = {"status": "PASS", "promotion": {"status": "OPTIONAL"}, "cases": []}
        first = write_benchmark_report(self.root, report)
        second = write_benchmark_report(self.root, report)
        self.assertEqual(first, second)
        self.assertTrue(Path(first).is_file())


if __name__ == "__main__":
    unittest.main()
