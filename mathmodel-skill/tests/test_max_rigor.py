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
        self.cfg = {"execution_mode": "competition_max"}

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, value):
        (self.root / "artifacts" / "competition-max-review.json").write_text(json.dumps(value), encoding="utf-8")

    def valid(self):
        return {
            "schema_version": 1,
            "generated_by": "local_max_rigor_engine",
            "model_scouts": 3,
            "candidate_routes_reviewed": 4,
            "robustness_attacks": ["alternative_split", "extreme_scenario", "bootstrap"],
            "red_team_rounds": 2,
            "external_reviews": [{"provider": "ars", "status": "COMPLETE", "evidence": "artifacts/ars-review.json"}],
        }

    def test_max_mode_requires_all_extended_evidence(self):
        self.write(self.valid())
        report = evaluate_max_rigor(self.root, self.cfg)
        self.assertEqual(report["status"], "PASS", report)
        self.assertEqual(report["requirements"]["red_team_rounds"], 2)

    def test_max_mode_fails_without_ars_review(self):
        data = self.valid()
        data["external_reviews"] = []
        self.write(data)
        report = evaluate_max_rigor(self.root, self.cfg)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any(check["rule"] == "G8-MAX-ARS-001" for check in report["checks"]))

    def test_assisted_mode_does_not_require_max_artifact(self):
        report = evaluate_max_rigor(self.root, {"execution_mode": "competition_assisted"})
        self.assertEqual(report["status"], "NOT_APPLICABLE")

    def test_research_mode_is_not_applicable(self):
        report = evaluate_max_rigor(self.root, {"execution_mode": "research_autonomous"})
        self.assertEqual(report["status"], "NOT_APPLICABLE")


if __name__ == "__main__":
    unittest.main()
