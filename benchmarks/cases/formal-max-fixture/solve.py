"""Materialize a deterministic, fully evidenced competition-max fixture."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
sys.path.insert(0, str(REPO / "mathmodel-skill" / "scripts"))
from mmcore.architecture_freeze import compute_upstream_hashes  # noqa: E402


NOW = "2026-09-01T00:00:00+00:00"
RISK_FIELDS = (
    "assumption_fit", "data_sufficiency", "data_quality", "implementation_feasibility",
    "solver_availability", "runtime_feasibility", "parameter_identifiability",
    "output_degeneracy", "leakage_risk", "sensitivity_risk", "validation_feasibility",
    "baseline_plausibility",
)


def write_json(relative: str, value: object) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(relative: str, rows: list[dict[str, object]]) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def digest(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def model(model_id: str, role: str, family: str, card_id: str) -> dict[str, object]:
    return {
        "id": model_id, "question_id": "Q1", "role": role,
        "conceptual_family": family, "assumption_family": f"assumptions-{family}",
        "optimization_or_inference_structure": f"structure-{family}",
        "method_card_id": card_id, "simpler_alternative": "linear baseline",
        "why_simpler_is_insufficient": "baseline reference" if role == "baseline" else f"{family} route captures a distinct constraint structure",
        "complexity_cost": "low" if role == "baseline" else "medium",
        "expected_gain": "reference point" if role == "baseline" else "distinct feasible allocation search",
    }


def method_card(card_id: str, family: str) -> dict[str, object]:
    return {
        "id": card_id, "family": family, "suitable_when": ["small constrained allocation"],
        "danger_when": ["capacity data are inconsistent"], "required_validation": ["feasibility", "baseline"],
        "common_failure_modes": ["constraint violation"], "simpler_alternatives": ["linear baseline"],
        "complexity_cost": "medium", "interpretability": "high",
    }


def human_review(review_id: str, gate: str, artifacts: list[str], notes: str) -> dict[str, object]:
    return {
        "id": review_id, "gate": gate, "reviewed_artifacts": artifacts,
        "reviewer_name": "Fixture human reviewer", "reviewer_role": "team member",
        "timestamp": NOW, "decision": "APPROVED", "evidence_notes": notes,
        "human_reasoning_summary": notes,
        "verified_points": ["reviewed linked artifacts", "confirmed the recorded decision"],
    }


def main() -> None:
    (ROOT / "analysis").mkdir(exist_ok=True)
    (ROOT / "figures").mkdir(exist_ok=True)
    (ROOT / "analysis" / "results.json").write_text("{\"allocation\": 4, \"objective\": 4}\n", encoding="utf-8")
    (ROOT / "analysis" / "metrics.json").write_text("{\"objective\": 4, \"feasible\": true}\n", encoding="utf-8")
    (ROOT / "figures" / "result.png").write_bytes(b"fixture-figure")

    models = [model("M0", "baseline", "linear", "CARD-linear")]
    models.extend(model(f"M{index}", "candidate", family, f"CARD-{family}") for index, family in enumerate(("tree", "simulation", "mechanism"), 1))
    write_json("artifacts/data-audit.json", {"status": "SUCCESS", "files": [{"path": "data/input.csv", "missingness": 0, "preprocessing": "none"}]})
    write_json("artifacts/problem-map.json", {"questions": [{"id": "Q1", "objective": "minimize allocation cost", "inputs": ["data/input.csv"], "outputs": ["R1"], "method": "constrained allocation", "validation": ["V1"], "model_ids": [item["id"] for item in models], "result_ids": ["R1"], "validation_ids": ["V1"], "claim_ids": ["C1"], "dependencies": []}]})
    write_json("artifacts/model-registry.json", {"models": models})
    write_json("artifacts/result-registry.json", {"results": [{"id": "R1", "value": 4, "unit": "units", "precision": 2, "source": "analysis/results.json", "source_sha256": digest("analysis/results.json"), "field": "objective", "question_id": "Q1", "model_id": "M1", "validation_ids": ["V1"]}]})
    write_json("artifacts/claim-registry.json", {"claims": [{"id": "C1", "body": "The selected route returns a feasible allocation for the stated fixture instance.", "result_ids": ["R1"], "validation_ids": ["V1"], "scope": "fixture instance", "failure_case": "different demand data", "section": "body"}]})
    write_json("artifacts/figure-registry.json", {"figures": [{"id": "F1", "role": "result", "file": "figures/result.png", "claim_ids": ["C1"]}]})
    semantic = {field: {"status": "PASS", "evidence": f"checked {field}"} for field in ("solver_status", "feasibility", "constraint_violation", "objective_recomputation", "baseline_policy")}
    write_json("artifacts/validation.json", {"schema_version": 1, "validations": [{"id": "V1", "question_id": "Q1", "metric": "objective", "operator": "<", "threshold": 5.0, "observed": 4.0, "evidence_source": "analysis/metrics.json", "status": "PASS", "checks": semantic}]})
    write_json("artifacts/experiment-registry.json", {"schema_version": 1, "generated_by": "local_fixture_runner", "experiments": [{"id": "EXP1", "run_id": "RUN1", "question_id": "Q1", "model_id": "M1", "code_hashes": {"solve.py": digest("solve.py")}, "input_hashes": {"data/input.csv": digest("data/input.csv")}, "config_hash": digest("mathmodel.json"), "seed": 7, "environment": {"python_version": sys.version.split()[0], "platform": "fixture"}, "started_at": NOW, "ended_at": NOW, "metrics": ["analysis/metrics.json"], "figures": ["figures/result.png"], "result_artifacts": ["analysis/results.json"]}]})
    write_json("artifacts/falsification.json", {"schema_version": 1, "generated_by": "local_falsification_engine", "attacks": [{"id": "F1", "validation_id": "V1", "attack_type": "constraint_attack", "evidence_source": "analysis/metrics.json", "outcome": "SURVIVED", "evidence_note": "feasibility remains satisfied under the recorded constraint check"}]})

    write_json("artifacts/interpretation-candidates.json", {"schema_version": 1, "problem_id": "P1", "candidates": [{"interpreter_id": "I-A", "independence_note": "independent reading A", "questions": ["Q1"], "objectives": ["minimize allocation cost"], "decision_variables": ["x"], "hard_constraints": ["x <= capacity"], "implicit_constraints": ["x >= demand"], "outputs": ["allocation"], "dependencies": [], "ambiguities": []}, {"interpreter_id": "I-B", "independence_note": "independent reading B", "questions": ["Q1"], "objectives": ["minimize allocation cost"], "decision_variables": ["x"], "hard_constraints": ["x <= capacity"], "implicit_constraints": ["x >= demand"], "outputs": ["allocation"], "dependencies": [], "ambiguities": []}]})
    write_json("artifacts/interpretation-conflicts.json", {"schema_version": 1, "generated_by": "local_interpretation_engine", "candidate_ids": ["I-A", "I-B"], "conflicts": [], "computed_status": "PASS"})
    write_json("artifacts/method-cards.json", {"schema_version": 1, "cards": [method_card("CARD-linear", "linear"), method_card("CARD-tree", "tree"), method_card("CARD-simulation", "simulation"), method_card("CARD-mechanism", "mechanism")]})
    write_json("artifacts/candidate-registry.json", {"schema_version": 1, "problem_id": "P1", "candidates": models})
    write_json("artifacts/risk-probe.json", {"schema_version": 1, "generated_by": "local_risk_engine", "probes": [{"candidate_id": item["id"], **{field: {"status": "PASS", "evidence": f"checked {field}"} for field in RISK_FIELDS}} for item in models]})
    decisions = [{"id": "D1", "candidate_id": "M1", "decision": "SELECTED", "reason": "best validated trade-off", "timestamp": NOW, "reviewed_artifacts": ["artifacts/candidate-registry.json"]}]
    decisions.extend({"id": f"D{index}", "candidate_id": f"M{candidate_index}", "decision": "REJECTED", "reason": "inferior trade-off for the stated objective", "timestamp": NOW, "reviewed_artifacts": ["artifacts/candidate-registry.json"]} for index, candidate_index in enumerate((0, 2, 3), 2))
    write_jsonl("artifacts/decision-ledger.jsonl", decisions)
    write_json("artifacts/decision-ledger.json", {"decisions": decisions})
    write_json("artifacts/model-architecture.json", {"schema_version": 1, "questions": [{"id": "Q1", "model_ids": ["M1"], "outputs": [{"id": "O1", "name": "allocation", "unit": "units", "uncertain": False}], "variables": [{"name": "allocation", "unit": "units"}], "parameters": [{"name": "capacity", "unit": "units"}], "assumptions": [{"id": "A1", "statement": "capacity is fixed"}], "data_sources": ["data/input.csv"]}], "links": []})
    write_json("artifacts/frozen-results.json", {"schema_version": 1, "results": [{"result_id": "R1", "value": 4, "unit": "units", "source": "analysis/results.json", "field": "objective"}]})

    write_json("artifacts/writer-package.json", {"schema_version": 1, "source_artifacts": ["artifacts/problem-map.json", "artifacts/model-architecture.json", "artifacts/frozen-results.json", "artifacts/claim-registry.json", "artifacts/figure-registry.json", "artifacts/decision-ledger.json"], "claim_bindings": [{"claim_id": "C1", "result_ids": ["R1"], "validation_ids": ["V1"]}], "figure_bindings": [{"figure_id": "F1", "source": "figures/result.png"}], "verified_citations": [{"id": "fixture-source", "verified": True, "source": "local fixture", "evidence_source": "paper/references.tex"}], "abstract_candidates": [{"id": "A1", "text": "解决分配问题并验证约束。"}, {"id": "A2", "text": "采用可解释约束模型求解分配。"}, {"id": "A3", "text": "通过基线与攻击验证结果。"}], "final_abstract_id": "A2", "judge_view": {"status": "PASS", "answers": {"problem": "分配", "method": "约束模型", "innovation": "结构化约束", "result": "可行分配", "trust": "机器验证", "risk": "数据范围"}}})
    reviews = [{"id": f"REV-{kind}", "reviewer_id": f"reviewer-{kind}", "reviewer_type": kind, "status": "COMPLETE", "independent": True, "findings": []} for kind in ("mathematical", "statistical", "evidence_consistency", "innovation", "red_team", "citation", "judge_view", "final_judge")]
    next(item for item in reviews if item["reviewer_type"] == "innovation")["innovation_assessment"] = {"problem_need": "addresses a concrete constraint issue", "counterfactual_value": "removing the structure weakens feasibility handling", "problem_origin": "derived from the fixture constraint", "empirical_support": "supported by registered comparison", "non_mechanical": "not a mechanical combination", "evidence_refs": ["artifacts/result-registry.json", "artifacts/validation.json"]}
    write_json("artifacts/review-registry.json", {"schema_version": 1, "reviews": reviews})
    (ROOT / "artifacts" / "ars-review.json").write_text("{\"finding_count\": 0}\n", encoding="utf-8")
    write_json("artifacts/competition-max-review.json", {"schema_version": 1, "generated_by": "local_max_rigor_engine", "model_scout_records": [{"id": f"scout-{i}"} for i in range(1, 4)], "candidate_route_records": [{"id": f"route-{i}"} for i in range(1, 5)], "robustness_attack_records": [{"id": "attack-1", "attack_type": "alternative_split"}, {"id": "attack-2", "attack_type": "extreme_scenario"}, {"id": "attack-3", "attack_type": "bootstrap"}], "red_team_round_records": [{"id": "red-1"}, {"id": "red-2"}], "external_reviews": [{"provider": "ars", "status": "COMPLETE", "evidence": "artifacts/ars-review.json"}]})
    write_jsonl("artifacts/human-review-ledger.jsonl", [human_review("HR1", "H1_PROBLEM_UNDERSTANDING", ["artifacts/interpretation-candidates.json", "artifacts/interpretation-conflicts.json", "artifacts/problem-map.json"], "Confirmed objectives, constraints, outputs, and dependencies."), human_review("HR2", "H2_METHOD_SELECTION", ["artifacts/candidate-registry.json", "artifacts/method-cards.json", "artifacts/risk-probe.json", "artifacts/decision-ledger.jsonl"], "Compared baseline, routes, risks, and complexity trade-offs."), human_review("HR3", "H3_RESULT_VERIFICATION", ["artifacts/frozen-results.json", "artifacts/freeze-manifest.json"], "Confirmed 数字真实；图正确；结论有边界；limitations 已理解。"), human_review("HR4", "H4_FINAL_SUBMISSION", ["paper/main.tex", "artifacts/submission-manifest.json", "artifacts/ai-usage-ledger.jsonl"], "Confirmed final paper, references, anonymity, support files, and AI disclosure.")])
    write_jsonl("artifacts/ai-usage-ledger.jsonl", [{"id": "AI1", "timestamp": NOW, "agent_role": "model-scout", "model_name": "fixture", "model_version": "1", "purpose": "candidate model generation", "stage": "MODEL_SEARCH", "prompt_summary": "compare constrained routes", "prompt_hash": "a" * 64, "output_artifacts": ["artifacts/candidate-registry.json"], "accepted": True, "human_modified": True, "human_verified": True, "human_review_id": "HR2"}])
    write_json("artifacts/submission-manifest.json", {"supporting_materials": ["data/input.csv"], "source_programs": ["solve.py"]})

    write_json("artifacts/freeze-manifest.json", {"schema_version": 1, "freeze_version": "1", "status": "CURRENT", "timestamp": NOW, "upstream_hashes": compute_upstream_hashes(ROOT, json.loads((ROOT / "mathmodel.json").read_text(encoding="utf-8"))), "h3_review_id": "HR3"})


if __name__ == "__main__":
    main()
