import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mmcore.compliance import evaluate_compliance


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def valid_rows():
    now = datetime.now(timezone.utc).isoformat()
    ai = {
        "id": "AI-0001", "timestamp": now, "agent_role": "model-scout", "model_name": "test",
        "model_version": "1", "purpose": "candidate model generation", "stage": "MODEL_SEARCH",
        "prompt_summary": "compare two defensible candidates", "prompt_hash": "a" * 64,
        "output_artifacts": ["artifacts/candidate-registry.json"], "accepted": True,
        "human_modified": True, "human_verified": True, "human_review_id": "HR-0002",
    }
    human = []
    for number, gate in enumerate(("H1_PROBLEM_UNDERSTANDING", "H2_METHOD_SELECTION", "H3_RESULT_VERIFICATION", "H4_FINAL_SUBMISSION"), 1):
        human.append({
            "id": f"HR-{number:04d}", "gate": gate, "reviewed_artifacts": ["artifacts/problem-map.json"],
            "reviewer_name": "Human Reviewer", "reviewer_role": "team member", "timestamp": now,
            "decision": "APPROVED", "evidence_notes": "Reviewed evidence and recorded the decision.",
        })
    return ai, human


class ComplianceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cfg = {"contest": "CUMCM", "execution_mode": "competition_assisted"}
        (self.root / "artifacts").mkdir()
        (self.root / "artifacts" / "problem-map.json").write_text("{}", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_formal_mode_missing_ledgers_fails_with_all_human_gates(self):
        report = evaluate_compliance(self.root, self.cfg)
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(set(report["missing_human_gates"]), {"H1_PROBLEM_UNDERSTANDING", "H2_METHOD_SELECTION", "H3_RESULT_VERIFICATION", "H4_FINAL_SUBMISSION"})

    def test_formal_mode_accepts_complete_ledgers(self):
        ai, human = valid_rows()
        write_jsonl(self.root / "artifacts" / "ai-usage-ledger.jsonl", [ai])
        write_jsonl(self.root / "artifacts" / "human-review-ledger.jsonl", human)
        report = evaluate_compliance(self.root, self.cfg)
        self.assertEqual(report["status"], "PASS", report)

    def test_malformed_or_sensitive_ai_ledger_fails(self):
        ai, _ = valid_rows()
        ai["prompt_summary"] = "api_key=secret"
        write_jsonl(self.root / "artifacts" / "ai-usage-ledger.jsonl", [ai, "not-json"])
        report = evaluate_compliance(self.root, self.cfg)
        self.assertEqual(report["status"], "FAIL")

    def test_stale_or_unapproved_human_review_fails(self):
        ai, human = valid_rows()
        human[0]["timestamp"] = "2020-01-01T00:00:00+00:00"
        human[1]["decision"] = "REJECTED"
        write_jsonl(self.root / "artifacts" / "ai-usage-ledger.jsonl", [ai])
        write_jsonl(self.root / "artifacts" / "human-review-ledger.jsonl", human)
        report = evaluate_compliance(self.root, self.cfg)
        self.assertEqual(report["status"], "FAIL")

    def test_human_review_rejects_missing_or_unsafe_reviewed_artifacts(self):
        ai, human = valid_rows()
        human[0]["reviewed_artifacts"] = ["artifacts/does-not-exist.json"]
        write_jsonl(self.root / "artifacts" / "ai-usage-ledger.jsonl", [ai])
        write_jsonl(self.root / "artifacts" / "human-review-ledger.jsonl", human)
        report = evaluate_compliance(self.root, self.cfg)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any(check["rule"] == "G0-HUMAN-INTEGRITY-001" for check in report["checks"]))

    def test_research_mode_is_not_applicable(self):
        report = evaluate_compliance(self.root, {"contest": "CUMCM", "execution_mode": "research_autonomous"})
        self.assertEqual(report["status"], "NOT_APPLICABLE")


if __name__ == "__main__":
    unittest.main()
