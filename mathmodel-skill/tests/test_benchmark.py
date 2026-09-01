import json
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
