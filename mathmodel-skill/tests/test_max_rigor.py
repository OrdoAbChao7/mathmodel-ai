import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mmcore.max_rigor import evaluate_max_rigor


class MaxRigorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "artifacts").mkdir()
        (self.root / "artifacts" / "ars-review.json").write_text("{\"review\": \"complete\"}", encoding="utf-8")
        self.cfg = {"execution_mode": "competition_max"}

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, value):
        (self.root / "artifacts" / "competition-max-review.json").write_text(json.dumps(value), encoding="utf-8")

    def valid(self):
        return {
            "schema_version": 1,
            "generated_by": "local_max_rigor_engine",
            "model_scout_records": [{"id": "scout-1"}, {"id": "scout-2"}, {"id": "scout-3"}],
            "candidate_route_records": [{"id": "route-1"}, {"id": "route-2"}, {"id": "route-3"}, {"id": "route-4"}],
            "red_team_round_records": [{"id": "red-1"}, {"id": "red-2"}],
            "robustness_attack_records": [{"id": "attack-1", "attack_type": "alternative_split"}, {"id": "attack-2", "attack_type": "extreme_scenario"}, {"id": "attack-3", "attack_type": "bootstrap"}],
            "model_scouts": 3,
            "candidate_routes_reviewed": 4,
            "robustness_attacks": ["alternative_split", "extreme_scenario", "bootstrap"],
            "red_team_rounds": 2,
            "external_reviews": [{"provider": "ars", "status": "COMPLETE", "evidence": "artifacts/ars-review.json"}],
        }

    def test_max_depth_counts_must_be_backed_by_record_arrays(self):
        data = self.valid()
        data["model_scout_records"] = [{"id": "scout-1"}]
        data["candidate_route_records"] = [{"id": "route-1"}]
        data["red_team_round_records"] = [{"id": "red-1"}]
        self.write(data)
        report = evaluate_max_rigor(self.root, self.cfg)
        self.assertEqual(report["status"], "FAIL")
        depth_checks = [check for check in report["checks"] if check["rule"] == "G8-MAX-DEPTH-001"]
        self.assertTrue(any(check["status"] == "FAIL" for check in depth_checks))

    def test_max_mode_requires_all_extended_evidence(self):
        self.write(self.valid())
        report = evaluate_max_rigor(self.root, self.cfg)
        self.assertEqual(report["status"], "PASS", report)
        self.assertEqual(report["requirements"]["red_team_round_records"], 2)

    def test_max_robustness_cannot_be_satisfied_by_free_standing_attack_names(self):
        data = self.valid()
        data.pop("robustness_attack_records")
        self.write(data)
        report = evaluate_max_rigor(self.root, self.cfg)
        self.assertEqual(report["status"], "FAIL")
        robustness = next(check for check in report["checks"] if check["rule"] == "G8-MAX-ROBUSTNESS-001")
        self.assertEqual(robustness["status"], "FAIL")

    def test_max_mode_fails_without_ars_review(self):
        data = self.valid()
        data["external_reviews"] = []
        self.write(data)
        report = evaluate_max_rigor(self.root, self.cfg)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any(check["rule"] == "G8-MAX-ARS-001" for check in report["checks"]))

    def test_max_mode_requires_existing_project_relative_ars_evidence(self):
        (self.root / "artifacts" / "ars-review.json").unlink()
        self.write(self.valid())
        report = evaluate_max_rigor(self.root, self.cfg)
        self.assertEqual(report["status"], "FAIL")
        ars_check = next(check for check in report["checks"] if check["rule"] == "G8-MAX-ARS-001")
        self.assertEqual(ars_check["status"], "FAIL")

        evidence = self.root / "artifacts" / "ars-review.json"
        evidence.write_text("{\"review\": \"complete\"}", encoding="utf-8")
        data = self.valid()
        data["external_reviews"][0]["evidence"] = "artifacts/ars-review.json"
        self.write(data)
        report = evaluate_max_rigor(self.root, self.cfg)
        self.assertEqual(report["status"], "PASS", report)

        data["external_reviews"][0]["evidence"] = "C:/outside/ars-review.json"
        self.write(data)
        report = evaluate_max_rigor(self.root, self.cfg)
        self.assertEqual(report["status"], "FAIL")

    def test_assisted_mode_does_not_require_max_artifact(self):
        report = evaluate_max_rigor(self.root, {"execution_mode": "competition_assisted"})
        self.assertEqual(report["status"], "NOT_APPLICABLE")

    def test_research_mode_is_not_applicable(self):
        report = evaluate_max_rigor(self.root, {"execution_mode": "research_autonomous"})
        self.assertEqual(report["status"], "NOT_APPLICABLE")


if __name__ == "__main__":
    unittest.main()
