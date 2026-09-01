import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mmcore.semantic_validation import evaluate_semantic_validation


FORECAST_CHECKS = {
    "chronological_split": {"status": "PASS", "evidence": "train precedes holdout"},
    "leakage_check": {"status": "PASS", "evidence": "future columns excluded"},
    "baseline": {"status": "PASS", "evidence": "seasonal naive baseline"},
    "metric_recomputation": {"status": "PASS", "evidence": "RMSE recomputed from predictions"},
}


def write_json(root, relative, value):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


class SemanticValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cfg = {"contest": "CUMCM", "problem_type": "forecasting", "execution_mode": "competition_assisted"}

    def tearDown(self):
        self.tmp.cleanup()

    def install_valid(self, observed=6.47, claimed_status="FAIL"):
        write_json(self.root, "analysis/metrics.json", {"rmse": observed})
        validation = {
            "schema_version": 1,
            "validations": [{
                "id": "V-Q1-001", "question_id": "Q1", "metric": "RMSE", "operator": "<", "threshold": 8.0,
                "observed": observed, "evidence_source": "analysis/metrics.json", "status": claimed_status,
                "checks": FORECAST_CHECKS,
            }],
        }
        write_json(self.root, "artifacts/validation.json", validation)
        write_json(self.root, "artifacts/falsification.json", {
            "schema_version": 1, "generated_by": "local_falsification_engine",
            "attacks": [{"id": "F-001", "validation_id": "V-Q1-001", "attack_type": "noise_injection", "evidence_source": "analysis/metrics.json", "outcome": "SURVIVED", "evidence_note": "error remains below threshold"}],
            "status": "FAIL",
        })

    def test_machine_computation_ignores_claimed_status(self):
        self.install_valid(claimed_status="FAIL")
        report = evaluate_semantic_validation(self.root, self.cfg)
        self.assertEqual(report["g4"]["status"], "PASS", report)
        self.assertEqual(report["g5"]["status"], "PASS", report)

    def test_observed_threshold_violation_fails_even_when_claimed_pass(self):
        self.install_valid(observed=9.2, claimed_status="PASS")
        report = evaluate_semantic_validation(self.root, self.cfg)
        self.assertEqual(report["g4"]["status"], "FAIL")
        self.assertTrue(any(check["rule"] == "G4-METRIC-001" for check in report["g4"]["checks"]))

    def test_invalid_operator_and_path_escape_fail_closed(self):
        self.install_valid()
        validation = json.loads((self.root / "artifacts/validation.json").read_text(encoding="utf-8"))
        validation["validations"][0]["operator"] = "approx"
        validation["validations"][0]["evidence_source"] = "../outside.json"
        write_json(self.root, "artifacts/validation.json", validation)
        report = evaluate_semantic_validation(self.root, self.cfg)
        self.assertEqual(report["g4"]["status"], "FAIL")
        self.assertTrue(any(check["rule"] == "G4-METRIC-001" for check in report["g4"]["checks"]))
        self.assertTrue(any(check["rule"] == "G4-PATH-001" for check in report["g4"]["checks"]))

    def test_missing_problem_type_check_fails_g4(self):
        self.install_valid()
        validation = json.loads((self.root / "artifacts/validation.json").read_text(encoding="utf-8"))
        validation["validations"][0]["checks"].pop("leakage_check")
        write_json(self.root, "artifacts/validation.json", validation)
        report = evaluate_semantic_validation(self.root, self.cfg)
        self.assertEqual(report["g4"]["status"], "FAIL")
        self.assertTrue(any(check["rule"] == "G4-SEMANTIC-CHECK-001" for check in report["g4"]["checks"]))

    def test_broken_attack_blocks_g5(self):
        self.install_valid()
        falsification = json.loads((self.root / "artifacts/falsification.json").read_text(encoding="utf-8"))
        falsification["attacks"][0]["outcome"] = "BROKEN"
        write_json(self.root, "artifacts/falsification.json", falsification)
        report = evaluate_semantic_validation(self.root, self.cfg)
        self.assertEqual(report["g4"]["status"], "PASS")
        self.assertEqual(report["g5"]["status"], "FAIL")
        self.assertTrue(any(check["rule"] == "G5-FALSIFICATION-001" for check in report["g5"]["checks"]))

    def test_missing_attack_coverage_blocks_g5_even_with_forged_status(self):
        self.install_valid()
        write_json(self.root, "artifacts/falsification.json", {"schema_version": 1, "generated_by": "local", "attacks": [], "status": "PASS"})
        report = evaluate_semantic_validation(self.root, self.cfg)
        self.assertEqual(report["g5"]["status"], "FAIL")
        self.assertTrue(any(check["rule"] == "G5-FALSIFICATION-COVERAGE-001" for check in report["g5"]["checks"]))

    def test_attack_for_unknown_validation_id_fails_g5(self):
        self.install_valid()
        falsification = json.loads((self.root / "artifacts/falsification.json").read_text(encoding="utf-8"))
        falsification["attacks"][0]["validation_id"] = "V-UNKNOWN"
        write_json(self.root, "artifacts/falsification.json", falsification)
        report = evaluate_semantic_validation(self.root, self.cfg)
        self.assertEqual(report["g5"]["status"], "FAIL")

    def test_malformed_validation_types_return_structured_failure(self):
        self.install_valid()
        validation = json.loads((self.root / "artifacts/validation.json").read_text(encoding="utf-8"))
        validation["validations"][0]["threshold"] = [8]
        write_json(self.root, "artifacts/validation.json", validation)
        report = evaluate_semantic_validation(self.root, self.cfg)
        self.assertEqual(report["status"], "FAIL")

    def test_malformed_operator_type_returns_structured_failure(self):
        self.install_valid()
        validation = json.loads((self.root / "artifacts/validation.json").read_text(encoding="utf-8"))
        validation["validations"][0]["operator"] = []
        write_json(self.root, "artifacts/validation.json", validation)
        report = evaluate_semantic_validation(self.root, self.cfg)
        self.assertEqual(report["g4"]["status"], "FAIL")

    def test_non_finite_observed_value_fails_machine_validation(self):
        self.install_valid()
        validation = json.loads((self.root / "artifacts/validation.json").read_text(encoding="utf-8"))
        validation["validations"][0]["observed"] = float("nan")
        validation["validations"][0]["operator"] = "!="
        write_json(self.root, "artifacts/validation.json", validation)
        report = evaluate_semantic_validation(self.root, self.cfg)
        self.assertEqual(report["g4"]["status"], "FAIL")

    def test_hybrid_problem_type_requires_profiled_semantic_checks(self):
        self.install_valid()
        report = evaluate_semantic_validation(self.root, {**self.cfg, "problem_type": "hybrid"})
        self.assertEqual(report["g4"]["status"], "FAIL")

    def test_research_mode_is_not_applicable(self):
        report = evaluate_semantic_validation(self.root, {"problem_type": "forecasting", "execution_mode": "research_autonomous"})
        self.assertEqual(report["status"], "NOT_APPLICABLE")


if __name__ == "__main__":
    unittest.main()
