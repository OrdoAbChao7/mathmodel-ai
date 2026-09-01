import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mmcore.interpretation import evaluate_g1


def write_json(root, relative, value):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def write_jsonl(root, relative, rows):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def candidate(interpreter_id, objective="minimize total cost"):
    return {
        "interpreter_id": interpreter_id,
        "independence_note": f"{interpreter_id} read the statement independently",
        "questions": ["Q1"],
        "objectives": [objective],
        "decision_variables": ["x_i"],
        "hard_constraints": ["capacity >= demand"],
        "implicit_constraints": ["nonnegative quantities"],
        "outputs": ["optimal allocation"],
        "dependencies": [],
        "ambiguities": [],
    }


def h1(reviewed_artifacts=None):
    return {
        "id": "HR-0001",
        "gate": "H1_PROBLEM_UNDERSTANDING",
        "reviewed_artifacts": reviewed_artifacts or [
            "artifacts/interpretation-candidates.json",
            "artifacts/interpretation-conflicts.json",
            "artifacts/problem-map.json",
        ],
        "reviewer_name": "Human Reviewer",
        "reviewer_role": "team member",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "decision": "APPROVED",
        "evidence_notes": "Confirmed objectives, constraints, outputs, and dependencies.",
    }


class InterpretationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cfg = {"contest": "CUMCM", "execution_mode": "competition_assisted"}

    def tearDown(self):
        self.tmp.cleanup()

    def install_valid_evidence(self, second_objective="minimize total cost", reviewed_artifacts=None):
        write_json(self.root, "artifacts/interpretation-candidates.json", {
            "schema_version": 1,
            "problem_id": "P1",
            "candidates": [candidate("I-A"), candidate("I-B", second_objective)],
        })
        write_json(self.root, "artifacts/interpretation-conflicts.json", {
            "schema_version": 1,
            "generated_by": "local_interpretation_engine",
            "candidate_ids": ["I-A", "I-B"],
            "conflicts": [],
            "computed_status": "PASS",
        })
        write_json(self.root, "artifacts/problem-map.json", {
            "questions": [{"id": "Q1", "dependencies": []}],
        })
        write_jsonl(self.root, "artifacts/human-review-ledger.jsonl", [h1(reviewed_artifacts)])

    def test_missing_candidates_fails_closed(self):
        report = evaluate_g1(self.root, self.cfg)
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("artifacts/interpretation-candidates.json", report["missing_artifacts"])

    def test_one_candidate_is_not_an_independent_tournament(self):
        write_json(self.root, "artifacts/interpretation-candidates.json", {"candidates": [candidate("I-A")]})
        report = evaluate_g1(self.root, self.cfg)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any(check["rule"] == "G1-CANDIDATE-COVERAGE-001" for check in report["checks"]))

    def test_major_conflict_blocks_even_when_supplied_status_says_pass(self):
        self.install_valid_evidence(second_objective="maximize service level")
        write_json(self.root, "artifacts/interpretation-conflicts.json", {
            "schema_version": 1,
            "generated_by": "local_interpretation_engine",
            "candidate_ids": ["I-A", "I-B"],
            "conflicts": [{"id": "CONFLICT-OBJECTIVES-I-A-I-B", "dimension": "objectives", "severity": "MAJOR", "candidate_ids": ["I-A", "I-B"], "description": "different objectives", "resolution_status": "OPEN"}],
            "computed_status": "PASS",
        })
        report = evaluate_g1(self.root, self.cfg)
        self.assertEqual(report["status"], "BLOCKED_INTERPRETATION_CONFLICT")
        self.assertTrue(any(conflict["severity"] == "MAJOR" for conflict in report["conflicts"]))

    def test_resolved_conflict_requires_matching_machine_evidence(self):
        self.install_valid_evidence(second_objective="maximize service level")
        conflict_id = "CONFLICT-OBJECTIVES-I-A-I-B"
        write_json(self.root, "artifacts/interpretation-conflicts.json", {
            "schema_version": 1,
            "generated_by": "local_interpretation_engine",
            "candidate_ids": ["I-A", "I-B"],
            "conflicts": [{"id": conflict_id, "dimension": "objectives", "severity": "MAJOR", "candidate_ids": ["I-A", "I-B"], "description": "different objectives", "resolution_status": "RESOLVED"}],
            "computed_status": "PASS",
        })
        report = evaluate_g1(self.root, self.cfg)
        self.assertEqual(report["status"], "PASS", report)

    def test_tampered_conflict_metadata_cannot_mark_recomputed_conflict_resolved(self):
        self.install_valid_evidence(second_objective="maximize service level")
        write_json(self.root, "artifacts/interpretation-conflicts.json", {
            "schema_version": 1,
            "generated_by": "local_interpretation_engine",
            "candidate_ids": ["I-A", "I-B"],
            "conflicts": [{"id": "CONFLICT-OBJECTIVES-I-A-I-B", "dimension": "outputs", "severity": "MAJOR", "candidate_ids": ["I-A", "I-B"], "description": "tampered", "resolution_status": "RESOLVED"}],
        })
        report = evaluate_g1(self.root, self.cfg)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any(check["rule"] == "G1-CONFLICT-INTEGRITY-001" for check in report["checks"]))

    def test_required_artifact_metadata_is_fail_closed(self):
        self.install_valid_evidence()
        candidates = json.loads((self.root / "artifacts/interpretation-candidates.json").read_text(encoding="utf-8"))
        candidates.pop("schema_version")
        (self.root / "artifacts/interpretation-candidates.json").write_text(json.dumps(candidates), encoding="utf-8")
        report = evaluate_g1(self.root, self.cfg)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any(check["rule"] == "G1-ARTIFACT-METADATA-001" for check in report["checks"]))

    def test_malformed_h1_record_returns_structured_failure(self):
        self.install_valid_evidence()
        write_jsonl(self.root, "artifacts/human-review-ledger.jsonl", [{**h1(), "reviewed_artifacts": None}])
        report = evaluate_g1(self.root, self.cfg)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any(check["rule"] == "G1-H1-LINK-001" for check in report["checks"]))

    def test_malformed_conflict_types_return_structured_failure(self):
        self.install_valid_evidence()
        write_json(self.root, "artifacts/interpretation-conflicts.json", {
            "schema_version": 1,
            "generated_by": "local_interpretation_engine",
            "candidate_ids": ["I-A", None],
            "conflicts": [{"id": [], "dimension": "objectives", "severity": "MAJOR", "candidate_ids": ["I-A", "I-B"], "resolution_status": "RESOLVED"}],
        })
        report = evaluate_g1(self.root, self.cfg)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any(check["rule"] == "G1-ARTIFACT-METADATA-001" for check in report["checks"]))

    def test_conflict_record_requires_description(self):
        self.install_valid_evidence(second_objective="maximize service level")
        write_json(self.root, "artifacts/interpretation-conflicts.json", {
            "schema_version": 1,
            "generated_by": "local_interpretation_engine",
            "candidate_ids": ["I-A", "I-B"],
            "conflicts": [{"id": "CONFLICT-OBJECTIVES-I-A-I-B", "dimension": "objectives", "severity": "MAJOR", "candidate_ids": ["I-A", "I-B"], "resolution_status": "RESOLVED"}],
        })
        report = evaluate_g1(self.root, self.cfg)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any(check["rule"] == "G1-CONFLICT-INTEGRITY-001" for check in report["checks"]))

    def test_missing_h1_artifact_link_blocks_gate(self):
        self.install_valid_evidence(reviewed_artifacts=["artifacts/problem-map.json"])
        report = evaluate_g1(self.root, self.cfg)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any(check["rule"] == "G1-H1-LINK-001" for check in report["checks"]))

    def test_research_mode_is_not_applicable(self):
        report = evaluate_g1(self.root, {"contest": "CUMCM", "execution_mode": "research_autonomous"})
        self.assertEqual(report["status"], "NOT_APPLICABLE")


if __name__ == "__main__":
    unittest.main()
