import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mmcore.paper_review import evaluate_review_registry, evaluate_writer_package


def write_json(root, relative, value):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


class PaperReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cfg = {"problem_type": "optimization", "execution_mode": "competition_assisted"}
        (self.root / "figures").mkdir()
        (self.root / "figures/result.png").write_bytes(b"png")
        write_json(self.root, "artifacts/claim-registry.json", {"claims": [{"id": "c1", "body": "方法达到最优排班", "result_ids": ["r1"], "validation_ids": ["v1"]}]})
        write_json(self.root, "artifacts/result-registry.json", {"results": [{"id": "r1"}]})
        write_json(self.root, "artifacts/validation.json", {"validations": [{"id": "v1", "status": "PASS"}]})
        write_json(self.root, "artifacts/figure-registry.json", {"figures": [{"id": "f1", "file": "figures/result.png"}]})
        write_json(self.root, "artifacts/frozen-results.json", {"schema_version": 1, "results": [{"result_id": "r1", "value": 10}]})
        write_json(self.root, "artifacts/decision-ledger.json", {"decisions": []})

    def tearDown(self):
        self.tmp.cleanup()

    def install_writer_package(self):
        write_json(self.root, "artifacts/writer-package.json", {
            "schema_version": 1,
            "source_artifacts": ["artifacts/problem-map.json", "artifacts/model-architecture.json", "artifacts/frozen-results.json", "artifacts/claim-registry.json", "artifacts/figure-registry.json", "artifacts/decision-ledger.json"],
            "claim_bindings": [{"claim_id": "c1", "result_ids": ["r1"], "validation_ids": ["v1"]}],
            "figure_bindings": [{"figure_id": "f1", "source": "figures/result.png"}],
            "verified_citations": [{"id": "ref1", "verified": True, "source": "https://example.org/paper"}],
            "abstract_candidates": [{"id": "a1", "text": "解决排班问题，采用优化模型。"}, {"id": "a2", "text": "采用约束模型解决排班问题。"}, {"id": "a3", "text": "模型给出可验证排班结果。"}],
            "final_abstract_id": "a2",
            "judge_view": {"status": "PASS", "answers": {"problem": "排班", "method": "优化模型", "innovation": "约束设计", "result": "排班结果", "trust": "验证", "risk": "数据范围"}},
        })
        write_json(self.root, "artifacts/problem-map.json", {"questions": [{"id": "q1"}]})
        write_json(self.root, "artifacts/model-architecture.json", {"schema_version": 1})

    def test_valid_writer_package_passes(self):
        self.install_writer_package()
        report = evaluate_writer_package(self.root, self.cfg)
        self.assertEqual(report["status"], "PASS", report)

    def test_strong_claim_without_binding_fails_g7(self):
        self.install_writer_package()
        package = json.loads((self.root / "artifacts/writer-package.json").read_text(encoding="utf-8"))
        package["claim_bindings"] = []
        write_json(self.root, "artifacts/writer-package.json", package)
        report = evaluate_writer_package(self.root, self.cfg)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any(check["rule"] == "UNSUPPORTED_STRONG_CLAIM" for check in report["checks"]))

    def test_claim_binding_must_match_registry_support(self):
        self.install_writer_package()
        package = json.loads((self.root / "artifacts/writer-package.json").read_text(encoding="utf-8"))
        package["claim_bindings"][0]["result_ids"] = ["r-other"]
        write_json(self.root, "artifacts/writer-package.json", package)
        report = evaluate_writer_package(self.root, self.cfg)
        self.assertEqual(report["status"], "FAIL")

    def test_figure_binding_must_use_canonical_registry_file(self):
        self.install_writer_package()
        package = json.loads((self.root / "artifacts/writer-package.json").read_text(encoding="utf-8"))
        (self.root / "figures/other.png").write_bytes(b"other")
        package["figure_bindings"][0]["source"] = "figures/other.png"
        write_json(self.root, "artifacts/writer-package.json", package)
        report = evaluate_writer_package(self.root, self.cfg)
        self.assertEqual(report["status"], "FAIL")

    def test_malformed_source_and_figure_ids_return_structured_failure(self):
        self.install_writer_package()
        package = json.loads((self.root / "artifacts/writer-package.json").read_text(encoding="utf-8"))
        package["source_artifacts"].append([])
        package["figure_bindings"][0]["figure_id"] = []
        write_json(self.root, "artifacts/writer-package.json", package)
        report = evaluate_writer_package(self.root, self.cfg)
        self.assertEqual(report["status"], "FAIL")

    def test_abstract_tournament_requires_three_candidates_and_judge(self):
        self.install_writer_package()
        package = json.loads((self.root / "artifacts/writer-package.json").read_text(encoding="utf-8"))
        package["abstract_candidates"] = package["abstract_candidates"][:2]
        write_json(self.root, "artifacts/writer-package.json", package)
        report = evaluate_writer_package(self.root, self.cfg)
        self.assertEqual(report["status"], "FAIL")

    def test_review_registry_requires_all_reviewers(self):
        types = ["mathematical", "statistical", "evidence_consistency", "red_team", "citation", "judge_view", "final_judge"]
        write_json(self.root, "artifacts/review-registry.json", {"schema_version": 1, "reviews": [{"id": f"rev-{item}", "reviewer_id": f"person-{item}", "reviewer_type": item, "status": "COMPLETE", "independent": True, "findings": []} for item in types]})
        report = evaluate_review_registry(self.root, self.cfg)
        self.assertEqual(report["status"], "PASS", report)

    def test_open_critical_red_team_finding_fails_g8(self):
        types = ["mathematical", "statistical", "evidence_consistency", "red_team", "citation", "judge_view", "final_judge"]
        reviews = [{"id": f"rev-{item}", "reviewer_id": f"person-{item}", "reviewer_type": item, "status": "COMPLETE", "independent": True, "findings": []} for item in types]
        reviews[3]["findings"] = [{"id": "REV-1", "severity": "CRITICAL", "status": "OPEN"}]
        write_json(self.root, "artifacts/review-registry.json", {"schema_version": 1, "reviews": reviews})
        report = evaluate_review_registry(self.root, self.cfg)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any(check["rule"] == "G8-OPEN-CRITICAL-001" for check in report["checks"]))

    def test_malformed_reviewer_type_returns_structured_failure(self):
        write_json(self.root, "artifacts/review-registry.json", {"schema_version": 1, "reviews": [{"id": "rev-1", "reviewer_type": [], "status": "COMPLETE", "independent": True, "findings": []}]})
        report = evaluate_review_registry(self.root, self.cfg)
        self.assertEqual(report["status"], "FAIL")

    def test_duplicate_review_identity_returns_structured_failure(self):
        types = ["mathematical", "statistical", "evidence_consistency", "red_team", "citation", "judge_view", "final_judge"]
        reviews = [{"id": "same", "reviewer_id": "same-person", "reviewer_type": item, "status": "COMPLETE", "independent": True, "findings": []} for item in types]
        write_json(self.root, "artifacts/review-registry.json", {"schema_version": 1, "reviews": reviews})
        report = evaluate_review_registry(self.root, self.cfg)
        self.assertEqual(report["status"], "FAIL")

    def test_malformed_finding_returns_structured_failure(self):
        types = ["mathematical", "statistical", "evidence_consistency", "red_team", "citation", "judge_view", "final_judge"]
        reviews = [{"id": f"rev-{item}", "reviewer_id": f"person-{item}", "reviewer_type": item, "status": "COMPLETE", "independent": True, "findings": []} for item in types]
        reviews[3]["findings"] = [{"id": "bad", "severity": [], "status": "OPEN"}]
        write_json(self.root, "artifacts/review-registry.json", {"schema_version": 1, "reviews": reviews})
        report = evaluate_review_registry(self.root, self.cfg)
        self.assertEqual(report["status"], "FAIL")

    def test_research_mode_is_not_applicable(self):
        report = evaluate_writer_package(self.root, {**self.cfg, "execution_mode": "research_autonomous"})
        self.assertEqual(report["status"], "NOT_APPLICABLE")


if __name__ == "__main__":
    unittest.main()
