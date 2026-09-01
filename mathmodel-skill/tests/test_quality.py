import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mathmodel import main
from mmcore.contracts import validate_artifacts
from mmcore.quality import score_quality


REQUIRED = (
    "problem-map.json",
    "data-audit.json",
    "model-registry.json",
    "result-registry.json",
    "claim-registry.json",
    "figure-registry.json",
    "validation.json",
)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def valid_config():
    return {
        "schema_version": 1,
        "project_id": "quality-001",
        "title": "Quality Fixture",
        "contest": "CUMCM",
        "problem_type": "hybrid",
        "inputs": {"statements": ["problem/problem.pdf"], "attachments": ["data/raw/attachment.xlsx"]},
        "commands": {"analyze": ["python", "analysis/run.py"]},
        "paper": {"main": "paper/main.tex", "engine": "xelatex", "jobname": "paper"},
        "quality": {
            "target_total_pages": [32, 40],
            "target_body_pages": [26, 34],
            "max_appendix_body_ratio": 0.25,
            "minimum_score": 85,
            "minimum_figures": 4,
            "required_figure_roles": ["data", "method", "result", "validation"],
        },
    }


def base_artifacts(result_ids=None, claim_support=None):
    result_ids = result_ids or ["R-1"]
    claim_support = claim_support or result_ids
    return {
        "problem-map": {
            "questions": [
                {
                    "id": "q1",
                    "model_ids": ["M1"],
                    "result_ids": result_ids,
                    "validation_ids": ["V1"],
                    "claim_ids": ["C1"],
                }
            ]
        },
        "data-audit": {"status": "SUCCESS", "files": []},
        "model-registry": {"models": [{"id": "M1", "question_id": "q1"}]},
        "result-registry": {
            "results": [
                {"id": result_id, "source": f"analysis/{result_id}.py", "value": 1, "unit": "unit"}
                for result_id in result_ids
            ]
        },
        "claim-registry": {"claims": [{"id": "C1", "result_ids": claim_support, "validation_ids": ["V1"]}]},
        "figure-registry": {
            "figures": [
                {"id": "F-data", "role": "data", "file": "paper/figures/data.pdf", "claim_ids": ["C1"]},
                {"id": "F-method", "role": "method", "file": "paper/figures/method.pdf", "claim_ids": ["C1"]},
                {"id": "F-result", "role": "result", "file": "paper/figures/result.pdf", "claim_ids": ["C1"]},
                {
                    "id": "F-validation",
                    "role": "validation",
                    "file": "paper/figures/validation.pdf",
                    "claim_ids": ["C1"],
                },
            ]
        },
        "validation": {"validations": [{"id": "V1", "status": "PASS", "question_id": "q1"}]},
    }


def write_artifacts(root, result_ids=None, claim_support=None):
    artifacts = base_artifacts(result_ids=result_ids, claim_support=claim_support)
    write_artifact_set(root, artifacts)


def write_artifact_set(root, artifacts, create_evidence_files=True):
    for stem, value in artifacts.items():
        write_json(root / "artifacts" / f"{stem}.json", value)
    if not create_evidence_files:
        return
    for result in artifacts.get("result-registry", {}).get("results", []):
        if not isinstance(result, dict) or not isinstance(result.get("source"), str):
            continue
        path = root / result["source"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("print('source')", encoding="utf-8")
    for figure in artifacts.get("figure-registry", {}).get("figures", []):
        if not isinstance(figure, dict) or not isinstance(figure.get("file"), str):
            continue
        path = root / figure["file"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"%PDF-1.4\n")


def write_complete_artifacts(root):
    write_artifacts(root)


class QualityTests(unittest.TestCase):
    def setUp(self):
        self._tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tempdir.name)

    def tearDown(self):
        self._tempdir.cleanup()

    def test_missing_machine_checks_are_unassessed_and_block_release(self):
        scored = score_quality([])
        self.assertEqual(scored["release_status"], "PENDING_MANUAL_REVIEW")
        self.assertEqual(scored["total"], 0)
        self.assertEqual(set(scored["unassessed_dimensions"]), set(scored["weights"]))
        self.assertTrue(all(detail["assessment_status"] == "UNASSESSED" for detail in scored["dimensions"].values()))

    def test_official_judge_view_exposes_four_competition_dimensions_without_inventing_creativity(self):
        scored = score_quality([])
        view = scored["official_judge_view"]
        self.assertEqual(set(view["dimensions"]), {
            "modeling_reasonableness", "modeling_creativity",
            "result_correctness_trust", "communication_clarity",
        })
        self.assertEqual(view["weights"], {
            "modeling_reasonableness": 30,
            "modeling_creativity": 20,
            "result_correctness_trust": 30,
            "communication_clarity": 20,
        })
        self.assertEqual(view["dimensions"]["modeling_creativity"]["assessment_status"], "UNASSESSED")
        self.assertLess(view["total"], 100)

    def test_missing_claim_support_is_hard_failure(self):
        write_artifacts(self.root, result_ids=["R-1"], claim_support=["R-missing"])
        report = validate_artifacts(self.root, REQUIRED)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any(c["rule"] == "EVIDENCE-CLAIM-001" for c in report["checks"]))

    def test_clean_contract_scores_at_least_eighty_five(self):
        write_complete_artifacts(self.root)
        report = validate_artifacts(self.root, REQUIRED)
        scored = score_quality(report["checks"])
        self.assertEqual(report["status"], "PASS")
        self.assertGreaterEqual(scored["total"], 85)

    def test_check_records_include_contract_fields_and_evidence(self):
        write_complete_artifacts(self.root)
        (self.root / "artifacts" / "result-registry.json").write_text("{", encoding="utf-8")
        report = validate_artifacts(self.root, REQUIRED)
        self.assertEqual(report["status"], "FAIL")
        for check in report["checks"]:
            self.assertIn("rule", check)
            self.assertIn("severity", check)
            self.assertIn("status", check)
            self.assertIn("message", check)
            self.assertIn("path", check)
            self.assertIn("evidence", check)

    def test_invalid_registry_shapes_are_hard_failures(self):
        cases = [
            ("problem-map", []),
            ("data-audit", []),
            ("model-registry", {"models": "not a list"}),
            ("result-registry", {"results": ["not a record"]}),
            ("claim-registry", {"claims": []}),
            ("figure-registry", {"figures": None}),
            ("validation", {"validations": []}),
        ]
        for stem, replacement in cases:
            with self.subTest(stem=stem):
                write_complete_artifacts(self.root)
                write_json(self.root / "artifacts" / f"{stem}.json", replacement)
                report = validate_artifacts(self.root, REQUIRED)
                self.assertEqual(report["status"], "FAIL")
                self.assertTrue(any(c["rule"].startswith("ARTIFACT-SHAPE") for c in report["checks"]))

    def test_each_missing_required_artifact_is_a_hard_failure(self):
        for filename in REQUIRED:
            with self.subTest(filename=filename):
                write_complete_artifacts(self.root)
                (self.root / "artifacts" / filename).unlink()
                report = validate_artifacts(self.root, REQUIRED)
                self.assertEqual(report["status"], "FAIL")
                self.assertTrue(
                    any(
                        c["rule"] == "ARTIFACT-FILE-001"
                        and c["status"] == "FAIL"
                        and c["path"] == f"artifacts/{filename}"
                        for c in report["checks"]
                    )
                )

    def test_each_malformed_required_artifact_is_a_hard_failure(self):
        for filename in REQUIRED:
            with self.subTest(filename=filename):
                write_complete_artifacts(self.root)
                (self.root / "artifacts" / filename).write_text("{", encoding="utf-8")
                report = validate_artifacts(self.root, REQUIRED)
                self.assertEqual(report["status"], "FAIL")
                self.assertTrue(
                    any(
                        c["rule"] == "ARTIFACT-JSON-001"
                        and c["status"] == "FAIL"
                        and c["path"] == f"artifacts/{filename}"
                        for c in report["checks"]
                    )
                )

    def test_duplicate_and_missing_ids_are_hard_failures(self):
        artifacts = base_artifacts()
        artifacts["result-registry"]["results"].append(
            {"id": "R-1", "source": "analysis/duplicate.py", "value": 2, "unit": "unit"}
        )
        artifacts["claim-registry"]["claims"].append({"result_ids": ["R-1"], "validation_ids": ["V1"]})
        write_artifact_set(self.root, artifacts)
        report = validate_artifacts(self.root, REQUIRED)
        self.assertEqual(report["status"], "FAIL")
        failed_id_checks = [c for c in report["checks"] if c["rule"] == "ARTIFACT-ID-001" and c["status"] == "FAIL"]
        self.assertTrue(failed_id_checks)

    def test_omitted_required_support_fields_are_hard_failures(self):
        cases = [
            ("problem-map", "questions", "model_ids", "EVIDENCE-QUESTION-SUPPORT-001"),
            ("problem-map", "questions", "result_ids", "EVIDENCE-QUESTION-SUPPORT-001"),
            ("problem-map", "questions", "validation_ids", "EVIDENCE-QUESTION-SUPPORT-001"),
            ("problem-map", "questions", "claim_ids", "EVIDENCE-QUESTION-SUPPORT-001"),
            ("claim-registry", "claims", "result_ids", "EVIDENCE-CLAIM-SUPPORT-001"),
            ("claim-registry", "claims", "validation_ids", "EVIDENCE-CLAIM-SUPPORT-001"),
        ]
        for artifact, collection, field, rule in cases:
            with self.subTest(artifact=artifact, field=field):
                artifacts = base_artifacts()
                del artifacts[artifact][collection][0][field]
                write_artifact_set(self.root, artifacts)
                report = validate_artifacts(self.root, REQUIRED)
                self.assertEqual(report["status"], "FAIL")
                self.assertTrue(any(c["rule"] == rule and c["status"] == "FAIL" for c in report["checks"]))

    def test_required_question_associations_are_non_empty(self):
        for field in ("model_ids", "result_ids", "validation_ids", "claim_ids"):
            with self.subTest(field=field):
                artifacts = base_artifacts()
                artifacts["problem-map"]["questions"][0][field] = []
                write_artifact_set(self.root, artifacts)
                report = validate_artifacts(self.root, REQUIRED)
                self.assertEqual(report["status"], "FAIL")
                self.assertTrue(any(c["rule"] == "EVIDENCE-QUESTION-SUPPORT-001" for c in report["checks"]))

    def test_required_claim_support_associations_are_non_empty(self):
        for field in ("result_ids", "validation_ids"):
            with self.subTest(field=field):
                artifacts = base_artifacts()
                artifacts["claim-registry"]["claims"][0][field] = []
                write_artifact_set(self.root, artifacts)
                report = validate_artifacts(self.root, REQUIRED)
                self.assertEqual(report["status"], "FAIL")
                self.assertTrue(any(c["rule"] == "EVIDENCE-CLAIM-SUPPORT-001" for c in report["checks"]))

    def test_non_string_reference_list_members_are_hard_failures(self):
        cases = [
            ("problem-map", "questions", "model_ids", "EVIDENCE-QUESTION-SUPPORT-001"),
            ("problem-map", "questions", "result_ids", "EVIDENCE-QUESTION-SUPPORT-001"),
            ("problem-map", "questions", "validation_ids", "EVIDENCE-QUESTION-SUPPORT-001"),
            ("problem-map", "questions", "claim_ids", "EVIDENCE-QUESTION-SUPPORT-001"),
            ("claim-registry", "claims", "result_ids", "EVIDENCE-CLAIM-SUPPORT-001"),
            ("claim-registry", "claims", "validation_ids", "EVIDENCE-CLAIM-SUPPORT-001"),
        ]
        for artifact, collection, field, rule in cases:
            with self.subTest(artifact=artifact, field=field):
                artifacts = base_artifacts()
                artifacts[artifact][collection][0][field] = [123]
                write_artifact_set(self.root, artifacts)
                report = validate_artifacts(self.root, REQUIRED)
                self.assertEqual(report["status"], "FAIL")
                self.assertTrue(any(c["rule"] == rule and c["status"] == "FAIL" for c in report["checks"]))

    def test_independent_broken_cross_reference_directions_are_hard_failures(self):
        cases = [
            (
                "unknown question model",
                lambda a: a["problem-map"]["questions"][0].update({"model_ids": ["M-missing"]}),
                "EVIDENCE-QUESTION-001",
            ),
            (
                "unknown model question",
                lambda a: a["model-registry"]["models"][0].update({"question_id": "q-missing"}),
                "EVIDENCE-MODEL-001",
            ),
            (
                "unknown validation question",
                lambda a: a["validation"]["validations"][0].update({"question_id": "q-missing"}),
                "EVIDENCE-VALIDATION-001",
            ),
            (
                "unknown figure claim",
                lambda a: a["figure-registry"]["figures"][0].update({"claim_ids": ["C-missing"]}),
                "EVIDENCE-FIGURE-001",
            ),
        ]
        for name, mutate, rule in cases:
            with self.subTest(name=name):
                artifacts = base_artifacts()
                mutate(artifacts)
                write_artifact_set(self.root, artifacts)
                report = validate_artifacts(self.root, REQUIRED)
                self.assertEqual(report["status"], "FAIL")
                self.assertTrue(any(c["rule"] == rule and c["status"] == "FAIL" for c in report["checks"]))

    def test_missing_sources_figures_roles_and_validation_status_are_hard_failures(self):
        cases = [
            ("missing result source", lambda a: a["result-registry"]["results"][0].update({"source": "analysis/missing.py"}), "EVIDENCE-RESULT-SOURCE-001"),
            ("missing figure file", lambda a: a["figure-registry"]["figures"][0].update({"file": "paper/figures/missing.pdf"}), "FIGURE-FILE-001"),
            ("missing role", lambda a: a["figure-registry"]["figures"].pop(), "FIGURE-ROLE-001"),
            ("failed validation", lambda a: a["validation"]["validations"][0].update({"status": "WARN"}), "VALIDATION-STATUS-001"),
        ]
        for name, mutate, rule in cases:
            with self.subTest(name=name):
                artifacts = base_artifacts()
                mutate(artifacts)
                write_artifact_set(self.root, artifacts, create_evidence_files=name not in {"missing result source", "missing figure file"})
                report = validate_artifacts(self.root, REQUIRED)
                self.assertEqual(report["status"], "FAIL")
                self.assertTrue(any(c["rule"] == rule and c["status"] == "FAIL" for c in report["checks"]))

    def test_configurable_figure_roles_are_enforced(self):
        cfg = valid_config()
        cfg["quality"]["required_figure_roles"] = ["result", "diagnostic"]
        write_json(self.root / "mathmodel.json", cfg)
        write_complete_artifacts(self.root)
        report = validate_artifacts(self.root, REQUIRED)
        self.assertEqual(report["status"], "FAIL")
        role_check = next(c for c in report["checks"] if c["rule"] == "FIGURE-ROLE-001")
        self.assertIn("diagnostic", role_check["evidence"]["missing_roles"])

    def test_result_and_figure_paths_must_stay_inside_project(self):
        outside = self.root.parent / "outside-evidence.py"
        outside.write_text("print('outside')", encoding="utf-8")
        for artifact_name, collection, field, rule, value in [
            ("result-registry", "results", "source", "EVIDENCE-RESULT-PATH-001", str(outside)),
            ("figure-registry", "figures", "file", "FIGURE-PATH-001", "../outside-figure.pdf"),
        ]:
            with self.subTest(artifact=artifact_name):
                artifacts = base_artifacts()
                artifacts[artifact_name][collection][0][field] = value
                write_artifact_set(self.root, artifacts, create_evidence_files=False)
                report = validate_artifacts(self.root, REQUIRED)
                self.assertEqual(report["status"], "FAIL")
                self.assertTrue(any(c["rule"] == rule and c["status"] == "FAIL" for c in report["checks"]))

    def test_missing_result_source_and_figure_file_fields_are_path_failures(self):
        cases = [
            ("result-registry", "results", "source", "EVIDENCE-RESULT-PATH-001"),
            ("figure-registry", "figures", "file", "FIGURE-PATH-001"),
        ]
        for artifact_name, collection, field, rule in cases:
            with self.subTest(artifact=artifact_name):
                artifacts = base_artifacts()
                del artifacts[artifact_name][collection][0][field]
                write_artifact_set(self.root, artifacts, create_evidence_files=False)
                report = validate_artifacts(self.root, REQUIRED)
                self.assertEqual(report["status"], "FAIL")
                self.assertTrue(any(c["rule"] == rule and c["status"] == "FAIL" for c in report["checks"]))

    def test_manual_scores_require_complete_valid_input(self):
        write_complete_artifacts(self.root)
        checks = validate_artifacts(self.root, REQUIRED)["checks"]
        partial = score_quality(checks, {"body_expression": 8})
        self.assertEqual(partial["manual_review"], "PENDING")
        self.assertEqual(partial["release_status"], "PENDING_MANUAL_REVIEW")
        invalid = score_quality(checks, {"body_expression": "bad"})
        self.assertEqual(invalid["manual_review"], "INVALID")
        self.assertEqual(invalid["release_status"], "FAIL")
        self.assertTrue(invalid["manual_errors"])
        complete = score_quality(
            checks,
            {
                "problem_coverage": 10,
                "data_traceability": 10,
                "model_rigor": 20,
                "validation_robustness": 20,
                "result_claim_evidence": 15,
                "body_expression": 10,
                "figures": 10,
                "latex": 5,
            },
        )
        self.assertEqual(complete["manual_review"], "COMPLETE")
        self.assertEqual(complete["release_status"], "PASS")

    def test_manual_scores_reject_non_dict_inputs_without_crashing(self):
        for manual in (["bad"], "bad", 7, [], "", 0, False):
            with self.subTest(manual=manual):
                scored = score_quality([], manual)
                self.assertEqual(scored["manual_review"], "INVALID")
                self.assertEqual(scored["release_status"], "FAIL")
                self.assertTrue(scored["manual_errors"])

    def test_audit_cli_writes_machine_reports_and_prints_json(self):
        write_json(self.root / "mathmodel.json", valid_config())
        (self.root / "problem").mkdir()
        (self.root / "problem" / "problem.pdf").write_bytes(b"statement")
        (self.root / "data" / "raw").mkdir(parents=True)
        (self.root / "data" / "raw" / "attachment.xlsx").write_bytes(b"attachment")
        (self.root / "paper").mkdir()
        (self.root / "paper" / "main.tex").write_text("paper", encoding="utf-8")
        write_complete_artifacts(self.root)

        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["audit", str(self.root), "--json"]), 0)

        payload = json.loads(output.getvalue())
        report_path = self.root / "build" / "quality-report.json"
        summary_path = self.root / "build" / "quality-report.md"
        self.assertEqual(Path(payload["report"]), report_path)
        self.assertTrue(report_path.exists())
        self.assertTrue(summary_path.exists())
        saved = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(saved["contract"]["status"], "PASS")
        self.assertEqual(saved["quality"]["manual_review"], "PENDING")
        self.assertEqual(saved["page_metrics"]["status"], "PENDING")

    def test_failing_audit_cli_writes_report_and_returns_nonzero(self):
        write_json(self.root / "mathmodel.json", valid_config())
        (self.root / "problem").mkdir()
        (self.root / "problem" / "problem.pdf").write_bytes(b"statement")
        (self.root / "data" / "raw").mkdir(parents=True)
        (self.root / "data" / "raw" / "attachment.xlsx").write_bytes(b"attachment")
        (self.root / "paper").mkdir()
        (self.root / "paper" / "main.tex").write_text("paper", encoding="utf-8")
        write_artifacts(self.root, result_ids=["R-1"], claim_support=["R-missing"])

        output = StringIO()
        with redirect_stdout(output):
            exit_code = main(["audit", str(self.root), "--json"])

        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertEqual(payload["status"], "FAIL")
        self.assertEqual(payload["quality"], "FAIL")
        self.assertTrue((self.root / "build" / "quality-report.json").exists())


if __name__ == "__main__":
    unittest.main()
