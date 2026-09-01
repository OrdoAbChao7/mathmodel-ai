import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mmcore.architecture_freeze import (
    compute_upstream_hashes,
    evaluate_model_architecture,
    evaluate_results_freeze,
)


def write_json(root, relative, value):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


class ArchitectureFreezeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cfg = {"problem_type": "optimization", "execution_mode": "competition_assisted", "inputs": {"attachments": ["data/raw.csv"], "statements": []}}
        (self.root / "data").mkdir()
        (self.root / "data/raw.csv").write_text("x,y\n1,2\n", encoding="utf-8")
        write_json(self.root, "mathmodel.json", self.cfg)
        write_json(self.root, "artifacts/problem-map.json", {"questions": [{"id": "q1"}, {"id": "q2"}]})
        write_json(self.root, "artifacts/model-registry.json", {"models": [{"id": "m1", "question_id": "q1"}, {"id": "m2", "question_id": "q2"}]})
        write_json(self.root, "artifacts/result-registry.json", {"results": [{"id": "r1", "question_id": "q1", "value": 4, "unit": "kg", "source": "results.json", "field": "q1_value"}]})
        write_json(self.root, "artifacts/validation.json", {"validations": [{"id": "v1", "question_id": "q1", "status": "PASS"}]})
        (self.root / "results.json").write_text('{"q1_value": 4}', encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def install_architecture(self, uncertainty="interval"):
        write_json(self.root, "artifacts/model-architecture.json", {
            "schema_version": 1,
            "questions": [
                {"id": "q1", "model_ids": ["m1"], "outputs": [{"id": "o1", "name": "demand", "unit": "kg", "uncertain": True}], "variables": [{"name": "demand", "unit": "kg"}], "parameters": [{"name": "capacity", "unit": "kg"}], "assumptions": [{"id": "a1", "statement": "capacity is fixed"}], "data_sources": ["data/raw.csv"]},
                {"id": "q2", "model_ids": ["m2"], "outputs": [{"id": "o2", "name": "plan", "unit": "kg", "uncertain": False}], "variables": [{"name": "demand", "unit": "kg"}], "parameters": [{"name": "capacity", "unit": "kg"}], "assumptions": [{"id": "a1", "statement": "capacity is fixed"}], "data_sources": ["data/raw.csv"]},
            ],
            "links": [{"from_question_id": "q1", "to_question_id": "q2", "output_ids": ["o1"], "uncertainty_propagation": uncertainty}],
        })

    def install_freeze(self):
        write_json(self.root, "artifacts/frozen-results.json", {"schema_version": 1, "results": [{"result_id": "r1", "value": 4, "unit": "kg", "source": "results.json", "field": "q1_value"}]})
        (self.root / "artifacts/decision-ledger.json").write_text('{}', encoding="utf-8")
        hashes = compute_upstream_hashes(self.root, self.cfg)
        write_json(self.root, "artifacts/freeze-manifest.json", {"schema_version": 1, "freeze_version": "1", "status": "CURRENT", "timestamp": "2026-09-01T00:00:00+00:00", "upstream_hashes": hashes, "h3_review_id": "h3-1"})
        (self.root / "artifacts/human-review-ledger.jsonl").write_text(json.dumps({"id": "h3-1", "gate": "H3_RESULT_VERIFICATION", "reviewed_artifacts": ["artifacts/frozen-results.json", "artifacts/freeze-manifest.json"], "reviewer_name": "human", "reviewer_role": "team", "timestamp": "2026-09-01T00:00:00+00:00", "decision": "APPROVED", "evidence_notes": "主要数字真实；主要图正确；核心结论有边界；limitations 已理解。"}) + "\n", encoding="utf-8")

    def test_valid_architecture_passes(self):
        self.install_architecture()
        report = evaluate_model_architecture(self.root, self.cfg)
        self.assertEqual(report["status"], "PASS", report)

    def test_uncertainty_gap_fails_g55(self):
        self.install_architecture("none")
        report = evaluate_model_architecture(self.root, self.cfg)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any(check["rule"] == "UNCERTAINTY_PROPAGATION_GAP" for check in report["checks"]))

    def test_conflicting_shared_unit_fails_g55(self):
        self.install_architecture()
        architecture = json.loads((self.root / "artifacts/model-architecture.json").read_text(encoding="utf-8"))
        architecture["questions"][1]["variables"][0]["unit"] = "ton"
        write_json(self.root, "artifacts/model-architecture.json", architecture)
        report = evaluate_model_architecture(self.root, self.cfg)
        self.assertEqual(report["status"], "FAIL")

    def test_stale_upstream_blocks_g6(self):
        self.install_freeze()
        (self.root / "data/raw.csv").write_text("x,y\n1,3\n", encoding="utf-8")
        report = evaluate_results_freeze(self.root, self.cfg)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(report["stale_nodes"])

    def test_frozen_result_mismatch_blocks_g6(self):
        self.install_freeze()
        frozen = json.loads((self.root / "artifacts/frozen-results.json").read_text(encoding="utf-8"))
        frozen["results"][0]["value"] = 5
        write_json(self.root, "artifacts/frozen-results.json", frozen)
        report = evaluate_results_freeze(self.root, self.cfg)
        self.assertEqual(report["status"], "FAIL")

    def test_missing_h3_signoff_blocks_g6(self):
        self.install_freeze()
        (self.root / "artifacts/human-review-ledger.jsonl").unlink()
        report = evaluate_results_freeze(self.root, self.cfg)
        self.assertEqual(report["status"], "FAIL")

    def test_malformed_frozen_result_id_returns_structured_failure(self):
        self.install_freeze()
        frozen = json.loads((self.root / "artifacts/frozen-results.json").read_text(encoding="utf-8"))
        frozen["results"][0]["result_id"] = []
        write_json(self.root, "artifacts/frozen-results.json", frozen)
        report = evaluate_results_freeze(self.root, self.cfg)
        self.assertEqual(report["status"], "FAIL")

    def test_malformed_architecture_id_returns_structured_failure(self):
        self.install_architecture()
        architecture = json.loads((self.root / "artifacts/model-architecture.json").read_text(encoding="utf-8"))
        architecture["questions"][0]["id"] = []
        write_json(self.root, "artifacts/model-architecture.json", architecture)
        report = evaluate_model_architecture(self.root, self.cfg)
        self.assertEqual(report["status"], "FAIL")

    def test_research_mode_is_not_applicable(self):
        report = evaluate_model_architecture(self.root, {**self.cfg, "execution_mode": "research_autonomous"})
        self.assertEqual(report["status"], "NOT_APPLICABLE")


if __name__ == "__main__":
    unittest.main()
