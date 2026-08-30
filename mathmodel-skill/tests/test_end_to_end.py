"""Deterministic end-to-end fixtures for the mathmodel CLI contract."""

from __future__ import annotations

import copy
import json
import shutil
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
from mmcore.analysis import run_analysis
from mmcore.config import load_config
from mmcore.contracts import REQUIRED_ARTIFACTS, validate_artifacts
from mmcore.latex import compile_latex
from mmcore.manifest import sha256_file
from mmcore.pdfmetrics import evaluate_page_gates, measure_pdf
from mmcore.quality import score_quality


FIXTURES = Path(__file__).resolve().parent / "fixtures"
FIXTURE_NAMES = ("optimization", "forecasting", "evaluation")
REGISTRIES = (
    "problem-map.json",
    "data-audit.json",
    "model-registry.json",
    "result-registry.json",
    "claim-registry.json",
    "figure-registry.json",
    "validation.json",
)
MANUAL_SCORES = {
    "problem_coverage": 10,
    "data_traceability": 10,
    "model_rigor": 20,
    "validation_robustness": 20,
    "result_claim_evidence": 15,
    "body_expression": 10,
    "figures": 10,
    "latex": 5,
}
BOUNDARY_LABELS = (
    "mm:body-start",
    "mm:body-end",
    "mm:references-start",
    "mm:references-end",
    "mm:appendix-start",
    "mm:appendix-end",
)


def _invoke_json(argv: list[str]) -> tuple[int, dict]:
    output = StringIO()
    with redirect_stdout(output):
        exit_code = main(argv)
    return exit_code, json.loads(output.getvalue())


def _hash_link_checks(project: Path) -> list[dict]:
    """Verify registry-declared generated-source hashes before release audit."""
    checks = []
    result_registry = json.loads((project / "artifacts" / "result-registry.json").read_text(encoding="utf-8"))
    figure_registry = json.loads((project / "artifacts" / "figure-registry.json").read_text(encoding="utf-8"))
    for kind, records, path_field in (
        ("result", result_registry["results"], "source"),
        ("figure", figure_registry["figures"], "file"),
    ):
        for record in records:
            source = project / record[path_field]
            expected = record.get("source_sha256")
            actual = sha256_file(source) if source.is_file() else None
            checks.append(
                {
                    "rule": "FIXTURE-OUTPUT-HASH-001",
                    "kind": kind,
                    "id": record.get("id"),
                    "status": "PASS" if isinstance(expected, str) and expected == actual else "FAIL",
                    "expected": expected,
                    "actual": actual,
                }
            )
    return checks


def _source_boundary_checks(project: Path, config: dict) -> list[dict]:
    """Verify the controlled compiler's page boundaries are declared in the source."""
    source = project / config["paper"]["main"]
    try:
        text = source.read_text(encoding="utf-8")
    except OSError as exc:
        return [{"rule": "FIXTURE-LATEX-SOURCE-001", "status": "FAIL", "path": str(source), "error": str(exc)}]
    positions = {label: text.find(f"\\label{{{label}}}") for label in BOUNDARY_LABELS}
    checks = [
        {
            "rule": "FIXTURE-LATEX-LABEL-001",
            "label": label,
            "status": "PASS" if position >= 0 else "FAIL",
            "path": str(source),
            "position": position,
        }
        for label, position in positions.items()
    ]
    checks.append(
        {
            "rule": "FIXTURE-LATEX-LABEL-ORDER-001",
            "status": "PASS" if all(position >= 0 for position in positions.values()) and list(positions.values()) == sorted(positions.values()) else "FAIL",
            "path": str(source),
            "expected_order": list(BOUNDARY_LABELS),
        }
    )
    return checks


def _controlled_compiler_checks(project: Path, config: dict) -> tuple[str | None, list[dict]]:
    """Limit fixture compilation to the declared, local deterministic adapter."""
    paper = config["paper"]
    mode = paper.get("compiler_mode")
    configured = (project / paper["engine"]).resolve()
    expected = (project / "fake-compiler.cmd").resolve()
    return mode, [
        {
            "rule": "FIXTURE-COMPILER-MODE-001",
            "status": "PASS" if mode == "controlled_fake" else "FAIL",
            "expected": "controlled_fake",
            "actual": mode,
        },
        {
            "rule": "FIXTURE-COMPILER-ENGINE-001",
            "status": "PASS" if configured == expected and configured.is_file() and project in configured.parents else "FAIL",
            "expected": str(expected),
            "actual": str(configured),
        },
    ]


def _run_fixture(project: Path) -> dict:
    """Execute inspect -> analyze -> validate -> compile -> audit for one fixture."""
    project = Path(project).resolve()
    inspect_exit, inspect = _invoke_json(["inspect", str(project), "--json"])
    cfg = load_config(project)
    run_dir = project / ".mathmodel" / "fixture-analysis"
    run_dir.mkdir(parents=True, exist_ok=True)
    analysis = run_analysis(project, cfg["commands"]["analyze"], run_dir)
    hash_checks = _hash_link_checks(project) if analysis["status"] == "SUCCESS" else []
    contract = validate_artifacts(project, REQUIRED_ARTIFACTS)
    source_checks = _source_boundary_checks(project, cfg)
    compiler_mode, compiler_checks = _controlled_compiler_checks(project, cfg)

    compile_result = {
        "status": "SKIPPED",
        "pdf": str(project / "build" / "latex" / f"{cfg['paper']['jobname']}.pdf"),
        "aux": str(project / "build" / "latex" / f"{cfg['paper']['jobname']}.aux"),
    }
    metrics = {"status": "SKIPPED"}
    if (
        analysis["status"] == "SUCCESS"
        and contract["status"] == "PASS"
        and all(check["status"] == "PASS" for check in hash_checks)
        and all(check["status"] == "PASS" for check in source_checks)
        and all(check["status"] == "PASS" for check in compiler_checks)
    ):
        engine_path = Path(cfg["paper"]["engine"])
        engine = str(engine_path if engine_path.is_absolute() else project / engine_path)
        compile_result = compile_latex(project, project / cfg["paper"]["main"], engine, cfg["paper"]["jobname"])
        metrics = measure_pdf(Path(compile_result["pdf"]), Path(compile_result["aux"]))

    audit_exit, audit = _invoke_json(["audit", str(project), "--json"])
    quality = score_quality(contract["checks"], MANUAL_SCORES)
    page_gates = evaluate_page_gates(metrics, {"profile": cfg["quality"], "score": quality})
    passed = (
        inspect_exit == 0
        and inspect["status"] in {"SUCCESS", "WARN"}
        and analysis["status"] == "SUCCESS"
        and contract["status"] == "PASS"
        and all(check["status"] == "PASS" for check in hash_checks)
        and all(check["status"] == "PASS" for check in source_checks)
        and all(check["status"] == "PASS" for check in compiler_checks)
        and compile_result["status"] == "SUCCESS"
        and metrics["status"] == "SUCCESS"
        and quality["release_status"] == "PASS"
        and not any(gate["severity"] == "FAIL" and gate["status"] != "PASS" for gate in page_gates)
        and audit_exit == 0
        and audit["status"] != "FAIL"
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "inspect": inspect,
        "analysis": analysis,
        "validation": contract,
        "compile": compile_result,
        "audit": audit,
        "quality": quality,
        "metrics": metrics,
        "page_gates": page_gates,
        "hash_checks": hash_checks,
        "source_checks": source_checks,
        "compiler_mode": compiler_mode,
        "compiler_checks": compiler_checks,
        "pdf": compile_result["pdf"],
        "quality_report": audit.get("report"),
    }


def run_fixture(path: Path) -> dict:
    """Public Task 8 fixture runner with the required single-path interface."""
    return _run_fixture(path)


def _normalise(value):
    if isinstance(value, dict):
        return {
            key: _normalise(item)
            for key, item in value.items()
            if key not in {"created_at", "generated_at", "started_at", "finished_at", "run_id"}
        }
    if isinstance(value, list):
        return [_normalise(item) for item in value]
    return value


class EndToEndFixtureTests(unittest.TestCase):
    def setUp(self):
        self._tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tempdir.name)

    def tearDown(self):
        self._tempdir.cleanup()

    def fixture_copy(self, name: str) -> Path:
        target = self.root / name
        shutil.copytree(FIXTURES / name, target)
        return target

    def test_three_problem_types_reach_auditable_output(self):
        expected_results = {
            "optimization": "objective_value",
            "forecasting": "holdout_mae",
            "evaluation": "ranking",
        }
        for name in FIXTURE_NAMES:
            with self.subTest(name=name):
                project = self.fixture_copy(name)
                report = run_fixture(project)
                self.assertEqual(report["status"], "PASS", report)
                self.assertTrue(Path(report["pdf"]).is_file())
                self.assertTrue(Path(report["quality_report"]).is_file())
                self.assertEqual({figure["role"] for figure in json.loads((project / "artifacts" / "figure-registry.json").read_text(encoding="utf-8"))["figures"]}, {"data", "method", "result", "validation"})
                results = json.loads((project / "analysis" / "results.json").read_text(encoding="utf-8"))
                self.assertIn(expected_results[name], results)

    def test_fixture_sources_expose_ordered_labels_and_controlled_fake_compiler_evidence(self):
        for name in FIXTURE_NAMES:
            with self.subTest(name=name):
                report = run_fixture(self.fixture_copy(name))
                self.assertEqual(report["status"], "PASS", report)
                self.assertEqual(report["compiler_mode"], "controlled_fake")
                self.assertTrue(all(check["status"] == "PASS" for check in report["compiler_checks"]), report["compiler_checks"])
                self.assertEqual([check["label"] for check in report["source_checks"] if check["rule"] == "FIXTURE-LATEX-LABEL-001"], list(BOUNDARY_LABELS))
                self.assertTrue(all(check["status"] == "PASS" for check in report["source_checks"]), report["source_checks"])

    def test_missing_or_misordered_boundary_labels_fail_before_fake_compilation(self):
        project = self.fixture_copy("forecasting")
        main = project / "paper" / "main.tex"
        main.write_text("this is not valid latex\n", encoding="utf-8")
        report = run_fixture(project)
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["compile"]["status"], "SKIPPED")
        self.assertTrue(any(check["rule"] == "FIXTURE-LATEX-LABEL-001" and check["status"] == "FAIL" for check in report["source_checks"]))

        project = self.fixture_copy("optimization")
        main = project / "paper" / "main.tex"
        source = main.read_text(encoding="utf-8")
        source = source.replace("\\label{mm:body-end}", "\\label{mm:temporary}")
        source = source.replace("\\label{mm:references-start}", "\\label{mm:body-end}")
        main.write_text(source.replace("\\label{mm:temporary}", "\\label{mm:references-start}"), encoding="utf-8")
        report = run_fixture(project)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any(check["rule"] == "FIXTURE-LATEX-LABEL-ORDER-001" and check["status"] == "FAIL" for check in report["source_checks"]))

    def test_non_fixture_local_or_non_fake_compiler_mode_fails_closed(self):
        project = self.fixture_copy("evaluation")
        config_path = project / "mathmodel.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["paper"]["compiler_mode"] = "xelatex"
        config["paper"]["engine"] = "outside-fixture.cmd"
        config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report = run_fixture(project)
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["compile"]["status"], "SKIPPED")
        self.assertTrue(any(check["status"] == "FAIL" for check in report["compiler_checks"]))

    def test_hand_checked_fixture_model_semantics(self):
        optimization = self.fixture_copy("optimization")
        self.assertEqual(run_fixture(optimization)["status"], "PASS")
        optimization_result = json.loads((optimization / "analysis" / "results.json").read_text(encoding="utf-8"))
        self.assertEqual(optimization_result, {"allocation": {"x": 2, "y": 2}, "feasible_points": 13, "objective_value": 18})

        forecasting = self.fixture_copy("forecasting")
        self.assertEqual(run_fixture(forecasting)["status"], "PASS")
        forecasting_result = json.loads((forecasting / "analysis" / "results.json").read_text(encoding="utf-8"))
        self.assertEqual(forecasting_result["slope"], 2.0)
        self.assertEqual(forecasting_result["holdout_predictions"], [11.0, 13.0])
        self.assertEqual(forecasting_result["holdout_mae"], 0.0)
        self.assertEqual(forecasting_result["persistence_baseline_mae"] - forecasting_result["holdout_mae"], 3.0)
        observations = json.loads((forecasting / "data" / "raw" / "input.json").read_text(encoding="utf-8"))["observations"]
        model = json.loads((forecasting / "artifacts" / "model-registry.json").read_text(encoding="utf-8"))["models"][0]
        self.assertEqual(model["train_end_time"], 4)
        self.assertLess(max(item["time"] for item in observations[:-2]), min(item["time"] for item in observations[-2:]))

        evaluation = self.fixture_copy("evaluation")
        self.assertEqual(run_fixture(evaluation)["status"], "PASS")
        evaluation_result = json.loads((evaluation / "analysis" / "results.json").read_text(encoding="utf-8"))
        self.assertEqual(evaluation_result["weights"], {"benefit": 0.4, "cost": 0.3, "reliability": 0.3})
        self.assertEqual(sum(evaluation_result["weights"].values()), 1.0)
        self.assertEqual(evaluation_result["normalized"], {"A": {"benefit": 0.5, "cost": 1.0, "reliability": 1.0}, "B": {"benefit": 1.0, "cost": 0.5, "reliability": 0.5}, "C": {"benefit": 0.0, "cost": 0.0, "reliability": 0.0}})
        self.assertEqual(evaluation_result["scores"], {"A": 0.8, "B": 0.7, "C": 0.0})
        self.assertEqual(evaluation_result["ranking"], ["A", "B", "C"])
        self.assertEqual(evaluation_result["sensitivity_ranking"], ["A", "B", "C"])

    def test_checked_in_optimization_result_is_a_hand_checked_baseline(self):
        result = json.loads((FIXTURES / "optimization" / "analysis" / "results.json").read_text(encoding="utf-8"))
        self.assertEqual(result, {"allocation": {"x": 2, "y": 2}, "feasible_points": 13, "objective_value": 18})

    def test_forecast_leakage_and_invalid_evaluation_weights_fail_closed(self):
        forecasting = self.fixture_copy("forecasting")
        forecast_input = forecasting / "data" / "raw" / "input.json"
        raw = json.loads(forecast_input.read_text(encoding="utf-8"))
        raw["observations"][3]["time"] = 6
        forecast_input.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        forecast_report = run_fixture(forecasting)
        self.assertEqual(forecast_report["status"], "FAIL")
        self.assertEqual(forecast_report["analysis"]["status"], "FAILED")

        evaluation = self.fixture_copy("evaluation")
        evaluation_input = evaluation / "data" / "raw" / "input.json"
        raw = json.loads(evaluation_input.read_text(encoding="utf-8"))
        raw["weights"]["cost"] = 0.4
        evaluation_input.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        evaluation_report = run_fixture(evaluation)
        self.assertEqual(evaluation_report["status"], "FAIL")
        self.assertEqual(evaluation_report["analysis"]["status"], "FAILED")

    def test_result_hashes_are_distinct_across_problem_types(self):
        hashes = []
        for name in FIXTURE_NAMES:
            project = self.fixture_copy(name)
            self.assertEqual(run_fixture(project)["status"], "PASS")
            hashes.append(sha256_file(project / "analysis" / "results.json"))
        self.assertEqual(len(set(hashes)), len(FIXTURE_NAMES))

    def test_repeat_run_preserves_results_registries_pdf_and_figure_hashes(self):
        project = self.fixture_copy("forecasting")
        self.assertEqual(run_fixture(project)["status"], "PASS")
        first = {
            "result": (project / "analysis" / "results.json").read_bytes(),
            "registries": {
                name: _normalise(json.loads((project / "artifacts" / name).read_text(encoding="utf-8")))
                for name in REGISTRIES
            },
            "pdf": sha256_file(project / "build" / "latex" / "fixture.pdf"),
            "figures": {
                figure["file"]: sha256_file(project / figure["file"])
                for figure in json.loads((project / "artifacts" / "figure-registry.json").read_text(encoding="utf-8"))["figures"]
            },
        }
        self.assertEqual(run_fixture(project)["status"], "PASS")
        second = {
            "result": (project / "analysis" / "results.json").read_bytes(),
            "registries": {
                name: _normalise(json.loads((project / "artifacts" / name).read_text(encoding="utf-8")))
                for name in REGISTRIES
            },
            "pdf": sha256_file(project / "build" / "latex" / "fixture.pdf"),
            "figures": {
                figure["file"]: sha256_file(project / figure["file"])
                for figure in json.loads((project / "artifacts" / "figure-registry.json").read_text(encoding="utf-8"))["figures"]
            },
        }
        self.assertEqual(second, first)

    def test_unsupported_claim_fails_closed(self):
        project = self.fixture_copy("optimization")
        self.assertEqual(run_fixture(project)["status"], "PASS")
        path = project / "artifacts" / "claim-registry.json"
        claims = json.loads(path.read_text(encoding="utf-8"))
        claims["claims"][0]["result_ids"] = ["R-unsupported"]
        path.write_text(json.dumps(claims, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        exit_code, audit = _invoke_json(["audit", str(project), "--json"])
        self.assertEqual(exit_code, 1)
        self.assertEqual(audit["status"], "FAIL")
        self.assertTrue(any(check["rule"] == "EVIDENCE-CLAIM-001" and check["status"] == "FAIL" for check in json.loads(Path(audit["report"]).read_text(encoding="utf-8"))["contract"]["checks"]))

    def test_missing_registry_link_fails_closed(self):
        project = self.fixture_copy("evaluation")
        self.assertEqual(run_fixture(project)["status"], "PASS")
        path = project / "artifacts" / "figure-registry.json"
        figures = json.loads(path.read_text(encoding="utf-8"))
        figures["figures"][0]["claim_ids"] = ["C-missing"]
        path.write_text(json.dumps(figures, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        exit_code, audit = _invoke_json(["audit", str(project), "--json"])
        self.assertEqual(exit_code, 1)
        self.assertEqual(audit["status"], "FAIL")
        self.assertTrue(any(check["rule"] == "EVIDENCE-FIGURE-001" and check["status"] == "FAIL" for check in json.loads(Path(audit["report"]).read_text(encoding="utf-8"))["contract"]["checks"]))

    def test_tampered_generated_output_fails_closed(self):
        project = self.fixture_copy("forecasting")
        (project / "analysis" / "tamper-output.flag").write_text("simulate external output tampering\n", encoding="utf-8")
        report = run_fixture(project)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any(check["rule"] == "FIXTURE-OUTPUT-HASH-001" and check["status"] == "FAIL" for check in report["hash_checks"]))
        self.assertEqual(report["compile"]["status"], "SKIPPED")


if __name__ == "__main__":
    unittest.main()
