import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mmcore.model_tournament import evaluate_model_tournament


RISK_FIELDS = (
    "assumption_fit", "data_sufficiency", "data_quality", "implementation_feasibility",
    "solver_availability", "runtime_feasibility", "parameter_identifiability",
    "output_degeneracy", "leakage_risk", "sensitivity_risk", "validation_feasibility",
    "baseline_plausibility",
)


def write_json(root, relative, value):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def write_jsonl(root, relative, rows):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def risk(status="PASS"):
    return {field: {"status": status, "evidence": f"checked {field}"} for field in RISK_FIELDS}


def model(model_id, role, family, card_id):
    return {
        "id": model_id,
        "question_id": "Q1",
        "role": role,
        "conceptual_family": family,
        "assumption_family": f"assumptions-{family}",
        "optimization_or_inference_structure": f"structure-{family}",
        "method_card_id": card_id,
        "simpler_alternative": "linear baseline",
        "why_simpler_is_insufficient": "baseline reference for comparison" if role == "baseline" else f"nonlinear {family} effect is material",
        "complexity_cost": "low" if role == "baseline" else "medium",
        "expected_gain": "reference point" if role == "baseline" else "captures a distinct mechanism",
    }


def card(card_id, family):
    return {
        "id": card_id, "family": family, "suitable_when": ["structured data"],
        "danger_when": ["tiny sample"], "required_validation": ["baseline", "holdout"],
        "common_failure_modes": ["overfitting"], "simpler_alternatives": ["linear regression"],
        "complexity_cost": "medium", "interpretability": "medium",
    }


def h2():
    return {
        "id": "HR-0002", "gate": "H2_METHOD_SELECTION",
        "reviewed_artifacts": ["artifacts/candidate-registry.json", "artifacts/method-cards.json", "artifacts/risk-probe.json", "artifacts/decision-ledger.jsonl"],
        "reviewer_name": "Human Reviewer", "reviewer_role": "team member",
        "timestamp": datetime.now(timezone.utc).isoformat(), "decision": "APPROVED",
        "evidence_notes": "Compared the baseline, route diversity, risks, and complexity trade-offs.",
        "human_reasoning_summary": "The selected route is justified against the baseline and probe results.",
        "verified_points": ["baseline", "route diversity", "risk findings"],
    }


class ModelTournamentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cfg = {"contest": "CUMCM", "execution_mode": "competition_assisted"}

    def tearDown(self):
        self.tmp.cleanup()

    def install_valid(self):
        models = [model("M0", "baseline", "linear", "CARD-linear")]
        for index, family in enumerate(("tree", "simulation", "mechanism"), 1):
            models.append(model(f"M{index}", "candidate", family, f"CARD-{family}"))
        write_json(self.root, "artifacts/candidate-registry.json", {"schema_version": 1, "problem_id": "P1", "candidates": models, "status": "PASS"})
        write_json(self.root, "artifacts/method-cards.json", {"schema_version": 1, "cards": [card("CARD-linear", "linear"), card("CARD-tree", "tree"), card("CARD-simulation", "simulation"), card("CARD-mechanism", "mechanism")]})
        write_json(self.root, "artifacts/risk-probe.json", {"schema_version": 1, "generated_by": "local_risk_engine", "probes": [{"candidate_id": item["id"], **risk()} for item in models], "status": "PASS"})
        decisions = [{"id": "D-0001", "candidate_id": "M1", "decision": "SELECTED", "reason": "best validated trade-off", "timestamp": datetime.now(timezone.utc).isoformat(), "reviewed_artifacts": ["artifacts/candidate-registry.json"]}]
        for index in (0, 2, 3):
            decisions.append({"id": f"D-000{index + 2}", "candidate_id": f"M{index}", "decision": "REJECTED", "reason": "inferior trade-off for the stated objective", "timestamp": datetime.now(timezone.utc).isoformat(), "reviewed_artifacts": ["artifacts/candidate-registry.json"]})
        write_jsonl(self.root, "artifacts/decision-ledger.jsonl", decisions)
        write_jsonl(self.root, "artifacts/human-review-ledger.jsonl", [h2()])

    def test_valid_tournament_passes_g2_and_g3(self):
        self.install_valid()
        report = evaluate_model_tournament(self.root, self.cfg)
        self.assertEqual(report["status"], "PASS", report)
        self.assertEqual(report["g2"]["status"], "PASS")
        self.assertEqual(report["g3"]["status"], "PASS")

    def test_fast_rigor_allows_smaller_candidate_breadth_but_keeps_h2(self):
        self.install_valid()
        candidates = json.loads((self.root / "artifacts/candidate-registry.json").read_text(encoding="utf-8"))["candidates"][:2]
        write_json(self.root, "artifacts/candidate-registry.json", {"schema_version": 1, "problem_id": "P1", "candidates": candidates})
        write_json(self.root, "artifacts/method-cards.json", {"schema_version": 1, "cards": [card("CARD-linear", "linear"), card("CARD-tree", "tree")]})
        write_json(self.root, "artifacts/risk-probe.json", {"schema_version": 1, "generated_by": "local_risk_engine", "probes": [{"candidate_id": item["id"], **risk()} for item in candidates]})
        write_jsonl(self.root, "artifacts/decision-ledger.jsonl", [
            {"id": "D-0001", "candidate_id": "M1", "decision": "SELECTED", "reason": "validated alternate", "timestamp": datetime.now(timezone.utc).isoformat(), "reviewed_artifacts": ["artifacts/candidate-registry.json"]},
            {"id": "D-0002", "candidate_id": "M0", "decision": "REJECTED", "reason": "baseline comparator", "timestamp": datetime.now(timezone.utc).isoformat(), "reviewed_artifacts": ["artifacts/candidate-registry.json"]},
        ])
        report = evaluate_model_tournament(self.root, {**self.cfg, "rigor": "fast"})
        self.assertEqual(report["status"], "PASS", report)
        self.assertEqual(report["rigor"], "fast")
        self.assertEqual(report["limits"]["minimum_total_candidates"], 2)

    def test_fast_rigor_does_not_weaken_critical_risk_gate(self):
        self.install_valid()
        data = json.loads((self.root / "artifacts/risk-probe.json").read_text(encoding="utf-8"))
        data["probes"][1]["leakage_risk"] = {"status": "CRITICAL", "evidence": "future data leakage"}
        write_json(self.root, "artifacts/risk-probe.json", data)
        report = evaluate_model_tournament(self.root, {**self.cfg, "rigor": "fast"})
        self.assertEqual(report["g2"]["status"], "FAIL")
        self.assertTrue(any(check["rule"] == "G2-RISK-001" for check in report["g2"]["checks"]))

    def test_missing_baseline_fails_g2(self):
        self.install_valid()
        data = json.loads((self.root / "artifacts/candidate-registry.json").read_text(encoding="utf-8"))
        data["candidates"][0]["role"] = "candidate"
        write_json(self.root, "artifacts/candidate-registry.json", data)
        report = evaluate_model_tournament(self.root, self.cfg)
        self.assertEqual(report["g2"]["status"], "FAIL")
        self.assertTrue(any(check["rule"] == "G2-BASELINE-001" for check in report["g2"]["checks"]))

    def test_same_conceptual_family_does_not_count_as_three_routes(self):
        self.install_valid()
        data = json.loads((self.root / "artifacts/candidate-registry.json").read_text(encoding="utf-8"))
        for item in data["candidates"][2:]:
            item["conceptual_family"] = "tree"
            item["assumption_family"] = "assumptions-tree"
            item["optimization_or_inference_structure"] = "structure-tree"
        write_json(self.root, "artifacts/candidate-registry.json", data)
        report = evaluate_model_tournament(self.root, self.cfg)
        self.assertEqual(report["g2"]["status"], "FAIL")
        self.assertTrue(any(check["rule"] == "G2-DIVERSITY-001" for check in report["g2"]["checks"]))

    def test_critical_risk_probe_blocks_g2(self):
        self.install_valid()
        data = json.loads((self.root / "artifacts/risk-probe.json").read_text(encoding="utf-8"))
        data["probes"][1]["leakage_risk"] = {"status": "CRITICAL", "evidence": "future data leakage"}
        write_json(self.root, "artifacts/risk-probe.json", data)
        report = evaluate_model_tournament(self.root, self.cfg)
        self.assertEqual(report["g2"]["status"], "FAIL")
        self.assertTrue(any(check["rule"] == "G2-RISK-001" for check in report["g2"]["checks"]))

    def test_missing_method_card_blocks_g2(self):
        self.install_valid()
        cards = json.loads((self.root / "artifacts/method-cards.json").read_text(encoding="utf-8"))
        cards["cards"] = cards["cards"][:-1]
        write_json(self.root, "artifacts/method-cards.json", cards)
        report = evaluate_model_tournament(self.root, self.cfg)
        self.assertEqual(report["g2"]["status"], "FAIL")
        self.assertTrue(any(check["rule"] == "G2-METHOD-CARD-LINK-001" for check in report["g2"]["checks"]))

    def test_missing_h2_link_blocks_g3(self):
        self.install_valid()
        write_jsonl(self.root, "artifacts/human-review-ledger.jsonl", [{**h2(), "reviewed_artifacts": ["artifacts/candidate-registry.json"]}])
        report = evaluate_model_tournament(self.root, self.cfg)
        self.assertEqual(report["g3"]["status"], "FAIL")
        self.assertTrue(any(check["rule"] == "G3-H2-LINK-001" for check in report["g3"]["checks"]))

    def test_method_card_list_members_must_be_strings(self):
        self.install_valid()
        cards = json.loads((self.root / "artifacts/method-cards.json").read_text(encoding="utf-8"))
        cards["cards"][0]["suitable_when"] = [7]
        write_json(self.root, "artifacts/method-cards.json", cards)
        report = evaluate_model_tournament(self.root, self.cfg)
        self.assertEqual(report["g2"]["status"], "FAIL")

    def test_malformed_h2_row_cannot_be_hidden_by_valid_row(self):
        self.install_valid()
        with (self.root / "artifacts/human-review-ledger.jsonl").open("a", encoding="utf-8") as stream:
            stream.write("not-json\n")
        report = evaluate_model_tournament(self.root, self.cfg)
        self.assertEqual(report["g3"]["status"], "FAIL")

    def test_h2_signoff_requires_reviewer_metadata_and_string_artifacts(self):
        self.install_valid()
        invalid = h2()
        invalid.pop("reviewer_name")
        invalid.pop("reviewer_role")
        invalid.pop("timestamp")
        invalid.pop("evidence_notes")
        invalid["reviewed_artifacts"].append(7)
        write_jsonl(self.root, "artifacts/human-review-ledger.jsonl", [invalid])
        report = evaluate_model_tournament(self.root, self.cfg)
        self.assertEqual(report["g3"]["status"], "FAIL")

    def test_multiple_selected_candidates_fail_g3(self):
        self.install_valid()
        with (self.root / "artifacts/decision-ledger.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"id": "D-0006", "candidate_id": "M2", "decision": "SELECTED", "reason": "also selected", "timestamp": datetime.now(timezone.utc).isoformat(), "reviewed_artifacts": ["artifacts/candidate-registry.json"]}) + "\n")
        report = evaluate_model_tournament(self.root, self.cfg)
        self.assertEqual(report["g3"]["status"], "FAIL")
        self.assertTrue(any(check["rule"] == "G3-SELECTION-001" for check in report["g3"]["checks"]))

    def test_missing_rejection_reason_fails_g3(self):
        self.install_valid()
        lines = (self.root / "artifacts/decision-ledger.jsonl").read_text(encoding="utf-8").splitlines()
        rejected = json.loads(lines[1])
        rejected["reason"] = ""
        lines[1] = json.dumps(rejected)
        (self.root / "artifacts/decision-ledger.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
        report = evaluate_model_tournament(self.root, self.cfg)
        self.assertEqual(report["g3"]["status"], "FAIL")
        self.assertTrue(any(check["rule"] == "G3-DECISION-001" for check in report["g3"]["checks"]))

    def test_duplicate_decision_record_id_fails_g3(self):
        self.install_valid()
        lines = (self.root / "artifacts/decision-ledger.jsonl").read_text(encoding="utf-8").splitlines()
        duplicate = json.loads(lines[0])
        duplicate["candidate_id"] = "M2"
        duplicate["decision"] = "REJECTED"
        lines.append(json.dumps(duplicate))
        (self.root / "artifacts/decision-ledger.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
        report = evaluate_model_tournament(self.root, self.cfg)
        self.assertEqual(report["g3"]["status"], "FAIL")
        self.assertTrue(any(check["rule"] == "G3-DECISION-JSONL-001" for check in report["g3"]["checks"]))

    def test_forged_aggregate_status_is_ignored(self):
        self.install_valid()
        data = json.loads((self.root / "artifacts/candidate-registry.json").read_text(encoding="utf-8"))
        data["candidates"] = data["candidates"][:1]
        write_json(self.root, "artifacts/candidate-registry.json", data)
        report = evaluate_model_tournament(self.root, self.cfg)
        self.assertEqual(report["status"], "FAIL")

    def test_research_mode_is_not_applicable(self):
        report = evaluate_model_tournament(self.root, {"contest": "CUMCM", "execution_mode": "research_autonomous"})
        self.assertEqual(report["status"], "NOT_APPLICABLE")

    def test_malformed_execution_mode_returns_structured_failure(self):
        report = evaluate_model_tournament(self.root, {"contest": "CUMCM", "execution_mode": []})
        self.assertEqual(report["status"], "FAIL")

    def test_malformed_rigor_returns_structured_failure(self):
        report = evaluate_model_tournament(self.root, {"contest": "CUMCM", "execution_mode": "competition_assisted", "rigor": []})
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["g2"]["checks"][0]["rule"], "G2-CONFIG-002")


if __name__ == "__main__":
    unittest.main()
