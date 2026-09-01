import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mathmodel import main
from mmcore.latex import compile_latex, find_latex_placeholders
from mmcore.pdfmetrics import evaluate_page_gates, measure_pdf, parse_aux_pages


LABELS = (
    "mm:body-start",
    "mm:body-end",
    "mm:references-start",
    "mm:references-end",
    "mm:appendix-start",
    "mm:appendix-end",
)


def quality_defaults():
    return {
        "target_total_pages": [32, 40],
        "target_body_pages": [26, 34],
        "max_appendix_body_ratio": 0.25,
        "minimum_score": 85,
    }


def valid_config(engine="xelatex"):
    return {
        "schema_version": 1,
        "project_id": "latex-001",
        "title": "LaTeX Fixture",
        "contest": "CUMCM",
        "problem_type": "optimization",
        "inputs": {"statements": [], "attachments": []},
        "commands": {"analyze": ["python", "analysis/run.py"]},
        "paper": {"main": "paper/main.tex", "engine": engine, "jobname": "paper"},
        "quality": {**quality_defaults(), "minimum_figures": 0, "required_figure_roles": []},
    }


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def write_complete_audit_project(root, *, paper_text="\\documentclass{article}\\begin{document}Ready\\end{document}"):
    write_json(root / "mathmodel.json", valid_config())
    paper = root / "paper" / "main.tex"
    paper.parent.mkdir(parents=True, exist_ok=True)
    paper.write_text(paper_text, encoding="utf-8")
    artifacts = {
        "data-audit": {"status": "SUCCESS"},
        "problem-map": {"questions": [{"id": "Q1", "model_ids": ["M1"], "result_ids": ["R1"], "validation_ids": ["V1"], "claim_ids": ["C1"]}]},
        "model-registry": {"models": [{"id": "M1", "question_id": "Q1"}]},
        "result-registry": {"results": [{"id": "R1", "source": "analysis/result.py"}]},
        "claim-registry": {"claims": [{"id": "C1", "result_ids": ["R1"], "validation_ids": ["V1"]}]},
        "figure-registry": {"figures": [{"id": "F1", "role": "data", "file": "paper/figures/data.pdf", "claim_ids": ["C1"]}]},
        "validation": {"validations": [{"id": "V1", "question_id": "Q1", "status": "PASS"}]},
    }
    for name, value in artifacts.items():
        write_json(root / "artifacts" / f"{name}.json", value)
    result_source = root / "analysis" / "result.py"
    result_source.parent.mkdir(parents=True, exist_ok=True)
    result_source.write_text("result = 1", encoding="utf-8")
    figure = root / "paper" / "figures" / "data.pdf"
    figure.parent.mkdir(parents=True, exist_ok=True)
    figure.write_bytes(b"%PDF-1.4\n")


class LatexMetricsTests(unittest.TestCase):
    def setUp(self):
        self._tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tempdir.name)

    def tearDown(self):
        self._tempdir.cleanup()

    def write_aux(self, *, body_start=1, body_end=28, references_start=29, references_end=30, appendix_start=31, appendix_end=35):
        aux = self.root / "build" / "latex" / "paper.aux"
        aux.parent.mkdir(parents=True, exist_ok=True)
        aux.write_text(
            "\n".join(
                [
                    rf"\newlabel{{mm:body-start}}{{{{}}{{{body_start}}}}}",
                    rf"\newlabel{{mm:body-end}}{{{{}}{{{body_end}}}}}",
                    rf"\newlabel{{mm:references-start}}{{{{}}{{{references_start}}}}}",
                    rf"\newlabel{{mm:references-end}}{{{{}}{{{references_end}}}}}",
                    rf"\newlabel{{mm:appendix-start}}{{{{}}{{{appendix_start}}}}}",
                    rf"\newlabel{{mm:appendix-end}}{{{{}}{{{appendix_end}}}}}",
                ]
            ),
            encoding="utf-8",
        )
        return aux

    def successful_engine_run(self, *, log_text="", create_pdf=True, create_aux=True):
        def fake_run(command, **_kwargs):
            output_dir = Path(next(arg.split("=", 1)[1] for arg in command if arg.startswith("-output-directory=")))
            jobname = next(arg.split("=", 1)[1] for arg in command if arg.startswith("-jobname="))
            output_dir.mkdir(parents=True, exist_ok=True)
            if create_pdf:
                (output_dir / f"{jobname}.pdf").write_bytes(b"%PDF-1.4\n")
            if create_aux:
                (output_dir / f"{jobname}.aux").write_text(r"\newlabel{mm:body-start}{{}{1}}", encoding="utf-8")
            (output_dir / f"{jobname}.log").write_text(log_text, encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, stdout="engine output", stderr="")

        return fake_run

    def test_aux_parser_reads_boundary_labels(self):
        aux = self.write_aux()
        pages = parse_aux_pages(aux, LABELS)
        self.assertEqual(pages["mm:body-end"], 28)
        self.assertEqual(pages["mm:appendix-end"], 35)

    def test_aux_parser_ignores_missing_and_malformed_labels(self):
        aux = self.root / "paper.aux"
        aux.write_text(r"\newlabel{mm:body-start}{{}{one}}", encoding="utf-8")
        self.assertEqual(parse_aux_pages(aux, LABELS), {})
        self.assertEqual(parse_aux_pages(self.root / "missing.aux", LABELS), {})

    def test_measure_pdf_calculates_body_reference_and_appendix_pages(self):
        aux = self.write_aux()
        pdf = self.root / "build" / "latex" / "paper.pdf"
        pdf.write_bytes(b"%PDF-1.4\n")
        completed = subprocess.CompletedProcess(
            ["pdfinfo", str(pdf)],
            0,
            stdout="Pages:          35\nPage size:      595.276 x 841.89 pts (A4)\n",
            stderr="",
        )
        with patch("mmcore.pdfmetrics.subprocess.run", return_value=completed):
            metrics = measure_pdf(pdf, aux)
        self.assertEqual(metrics["status"], "SUCCESS")
        self.assertEqual(metrics["total_pages"], 35)
        self.assertEqual(metrics["body_pages"], 28)
        self.assertEqual(metrics["reference_pages"], 2)
        self.assertEqual(metrics["appendix_pages"], 5)
        self.assertAlmostEqual(metrics["appendix_body_ratio"], 5 / 28)

    def test_measure_pdf_returns_pending_for_unavailable_pdfinfo(self):
        aux = self.write_aux()
        pdf = self.root / "build" / "latex" / "paper.pdf"
        pdf.write_bytes(b"%PDF-1.4\n")
        with patch("mmcore.pdfmetrics.subprocess.run", side_effect=FileNotFoundError):
            metrics = measure_pdf(pdf, aux)
        self.assertEqual(metrics["status"], "PENDING")
        self.assertTrue(any(item["rule"] == "PDFINFO-001" for item in metrics["warnings"]))

    def test_measure_pdf_returns_structured_failure_for_malformed_boundaries(self):
        aux = self.root / "paper.aux"
        aux.write_text(r"\newlabel{mm:body-start}{{}{1}}", encoding="utf-8")
        pdf = self.root / "paper.pdf"
        pdf.write_bytes(b"%PDF-1.4\n")
        completed = subprocess.CompletedProcess(["pdfinfo", str(pdf)], 0, stdout="Pages: 4\n", stderr="")
        with patch("mmcore.pdfmetrics.subprocess.run", return_value=completed):
            metrics = measure_pdf(pdf, aux)
        self.assertEqual(metrics["status"], "FAILED")
        self.assertTrue(any(item["rule"] == "PDF-LABEL-001" for item in metrics["errors"]))

    def test_measure_pdf_retains_total_and_a4_evidence_when_labels_are_missing(self):
        aux = self.root / "paper.aux"
        aux.write_text(r"\newlabel{mm:body-start}{{}{1}}", encoding="utf-8")
        pdf = self.root / "paper.pdf"
        pdf.write_bytes(b"%PDF-1.4\n")
        completed = subprocess.CompletedProcess(["pdfinfo", str(pdf)], 0, stdout="Pages: 38\nPage size: 595.28 x 841.89 pts (A4)\n", stderr="")
        with patch("mmcore.pdfmetrics.subprocess.run", return_value=completed):
            metrics = measure_pdf(pdf, aux)
        self.assertEqual(metrics["status"], "FAILED")
        self.assertEqual(metrics["total_pages"], 38)
        self.assertEqual(metrics["a4_status"], "PASS")
        self.assertTrue(any(item["rule"] == "PDF-LABEL-001" for item in metrics["errors"]))

    def test_measure_pdf_rejects_invalid_label_order_and_non_a4_output(self):
        aux = self.write_aux(references_start=20)
        pdf = self.root / "build" / "latex" / "paper.pdf"
        pdf.write_bytes(b"%PDF-1.4\n")
        completed = subprocess.CompletedProcess(["pdfinfo", str(pdf)], 0, stdout="Pages: 35\nPage size: 612 x 792 pts (letter)\n", stderr="")
        with patch("mmcore.pdfmetrics.subprocess.run", return_value=completed):
            metrics = measure_pdf(pdf, aux)
        self.assertEqual(metrics["status"], "FAILED")
        self.assertEqual(metrics["total_pages"], 35)
        self.assertEqual(metrics["a4_status"], "FAIL")
        self.assertTrue(any(item["rule"] == "PDF-BOUNDARY-001" for item in metrics["errors"]))
        self.assertTrue(any(item["rule"] == "PDF-A4-001" for item in metrics["errors"]))

    def test_measure_pdf_reports_nonzero_and_malformed_pdfinfo(self):
        aux = self.write_aux()
        pdf = self.root / "build" / "latex" / "paper.pdf"
        pdf.write_bytes(b"%PDF-1.4\n")
        cases = [
            (subprocess.CompletedProcess(["pdfinfo", str(pdf)], 2, stdout="", stderr="bad pdf"), "PDFINFO-002"),
            (subprocess.CompletedProcess(["pdfinfo", str(pdf)], 0, stdout="Page size: A4\n", stderr=""), "PDFINFO-003"),
        ]
        for completed, rule in cases:
            with self.subTest(rule=rule), patch("mmcore.pdfmetrics.subprocess.run", return_value=completed):
                metrics = measure_pdf(pdf, aux)
            self.assertEqual(metrics["status"], "FAILED")
            self.assertTrue(any(item["rule"] == rule for item in metrics["errors"]))

    def test_measure_pdf_handles_undecodable_or_absent_pdfinfo_streams(self):
        aux = self.write_aux()
        pdf = self.root / "build" / "latex" / "paper.pdf"
        pdf.write_bytes(b"%PDF-1.4\n")
        byte_output = b"Pages: 35\nPage size: 595.28 x 841.89 pts (A4)\n\xff"
        cases = [
            (subprocess.CompletedProcess(["pdfinfo", str(pdf)], 0, stdout=byte_output, stderr=b"\xff"), "SUCCESS", None),
            (subprocess.CompletedProcess(["pdfinfo", str(pdf)], 0, stdout=None, stderr=None), "FAILED", "PDFINFO-003"),
        ]
        for completed, status, rule in cases:
            with self.subTest(status=status), patch("mmcore.pdfmetrics.subprocess.run", return_value=completed):
                metrics = measure_pdf(pdf, aux)
                self.assertEqual(metrics["status"], status)
                if rule:
                    self.assertTrue(any(item["rule"] == rule for item in metrics["errors"]))

    def test_measure_pdf_returns_pending_when_pdfinfo_decode_fails(self):
        aux = self.write_aux()
        pdf = self.root / "build" / "latex" / "paper.pdf"
        pdf.write_bytes(b"%PDF-1.4\n")
        decode_error = UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")
        with patch("mmcore.pdfmetrics.subprocess.run", side_effect=decode_error):
            metrics = measure_pdf(pdf, aux)
        self.assertEqual(metrics["status"], "PENDING")
        self.assertTrue(any(item["rule"] == "PDFINFO-001" for item in metrics["warnings"]))

    def test_appendix_ratio_is_hard_failure(self):
        gates = evaluate_page_gates(
            {"status": "SUCCESS", "total_pages": 40, "body_pages": 20, "appendix_pages": 10, "appendix_body_ratio": 0.5},
            quality_defaults(),
        )
        self.assertTrue(any(g["rule"] == "PAGE-APPENDIX-001" and g["severity"] == "FAIL" and g["status"] == "FAIL" for g in gates))

    def test_body_below_configured_minimum_is_hard_failure(self):
        gates = evaluate_page_gates(
            {"status": "SUCCESS", "total_pages": 32, "body_pages": 25, "appendix_pages": 2, "appendix_body_ratio": 0.08},
            quality_defaults(),
        )
        self.assertTrue(any(g["rule"] == "PAGE-BODY-001" and g["severity"] == "FAIL" and g["status"] == "FAIL" for g in gates))

    def test_total_pages_outside_target_is_warning_not_body_substitute(self):
        gates = evaluate_page_gates(
            {"status": "SUCCESS", "total_pages": 41, "body_pages": 30, "appendix_pages": 2, "appendix_body_ratio": 2 / 30},
            quality_defaults(),
        )
        self.assertTrue(any(g["rule"] == "PAGE-TOTAL-001" and g["severity"] == "WARN" and g["status"] == "WARN" for g in gates))
        self.assertFalse(any(g["rule"] == "PAGE-BODY-001" and g["status"] == "FAIL" for g in gates))

    def test_quality_score_below_profile_minimum_blocks_release(self):
        gates = evaluate_page_gates(
            {"status": "SUCCESS", "total_pages": 35, "body_pages": 28, "appendix_pages": 5, "appendix_body_ratio": 5 / 28},
            {"profile": quality_defaults(), "score": {"total": 84, "release_status": "FAIL"}},
        )
        self.assertTrue(any(g["rule"] == "QUALITY-SCORE-001" and g["status"] == "FAIL" for g in gates))

    def test_pending_page_metrics_need_manual_review(self):
        gates = evaluate_page_gates({"status": "PENDING"}, quality_defaults())
        self.assertTrue(any(g["rule"] == "PAGE-METRICS-001" and g["severity"] == "FAIL" and g["status"] == "PENDING" for g in gates))

    def test_compile_blocks_placeholders_and_out_of_project_main(self):
        main_tex = self.root / "paper" / "main.tex"
        main_tex.parent.mkdir(parents=True)
        main_tex.write_text("TODO: replace", encoding="utf-8")
        placeholder_result = compile_latex(self.root, main_tex, "unused-engine", "paper")
        self.assertEqual(placeholder_result["status"], "FAILED")
        self.assertTrue(any(item["rule"] == "LATEX-PLACEHOLDER-001" for item in placeholder_result["errors"]))
        outside = self.root.parent / "outside-main.tex"
        outside.write_text("paper", encoding="utf-8")
        try:
            path_result = compile_latex(self.root, outside, "unused-engine", "paper")
        finally:
            outside.unlink(missing_ok=True)
        self.assertEqual(path_result["status"], "FAILED")
        self.assertTrue(any(item["rule"] == "LATEX-MAIN-PATH-001" for item in path_result["errors"]))

    def test_compile_requires_pdf_and_aux_after_successful_passes(self):
        main_tex = self.root / "paper" / "main.tex"
        main_tex.parent.mkdir(parents=True)
        main_tex.write_text("ready", encoding="utf-8")
        for create_pdf, create_aux, rule, jobname in [(False, True, "LATEX-PDF-001", "missing-pdf"), (True, False, "LATEX-AUX-001", "missing-aux")]:
            with self.subTest(rule=rule), patch("mmcore.latex.subprocess.run", side_effect=self.successful_engine_run(create_pdf=create_pdf, create_aux=create_aux)):
                result = compile_latex(self.root, main_tex, "fake-engine", jobname)
            self.assertEqual(result["exit_codes"], [0, 0])
            self.assertEqual(result["status"], "FAILED")
            self.assertTrue(any(item["rule"] == rule for item in result["errors"]))

    def test_compile_log_hard_diagnostics_block_release(self):
        main_tex = self.root / "paper" / "main.tex"
        main_tex.parent.mkdir(parents=True)
        main_tex.write_text("ready", encoding="utf-8")
        cases = [
            ("LaTeX Warning: There were undefined references.", "LATEX-UNDEFINED-REF-001"),
            ("LaTeX Warning: Citation `source' on page 1 undefined.", "LATEX-UNDEFINED-CITATION-001"),
            ("! Fatal error occurred, no output PDF file produced!", "LATEX-LOG-FATAL-001"),
            (r"Overfull \hbox (3.1pt too wide) in paragraph", "LATEX-OVERFULL-002"),
        ]
        for log_text, rule in cases:
            with self.subTest(rule=rule), patch("mmcore.latex.subprocess.run", side_effect=self.successful_engine_run(log_text=log_text)):
                result = compile_latex(self.root, main_tex, "fake-engine", "paper")
            self.assertEqual(result["status"], "FAILED")
            self.assertTrue(any(item["rule"] == rule for item in result["errors"]))

    def test_compile_keeps_small_overfull_box_as_warning(self):
        main_tex = self.root / "paper" / "main.tex"
        main_tex.parent.mkdir(parents=True)
        main_tex.write_text("ready", encoding="utf-8")
        with patch("mmcore.latex.subprocess.run", side_effect=self.successful_engine_run(log_text=r"Overfull \hbox (2.0pt too wide) in paragraph")):
            result = compile_latex(self.root, main_tex, "fake-engine", "paper")
        self.assertEqual(result["status"], "SUCCESS")
        self.assertTrue(any(item["rule"] == "LATEX-OVERFULL-001" for item in result["warnings"]))

    def test_template_has_no_release_blocking_placeholders(self):
        template = Path(__file__).resolve().parents[1] / "assets" / "project-template" / "paper" / "main.tex"
        self.assertEqual(find_latex_placeholders(template), [])

    def test_audit_marks_missing_pdf_or_aux_as_needs_manual_review(self):
        write_complete_audit_project(self.root)
        output = StringIO()
        with redirect_stdout(output):
            exit_code = main(["audit", str(self.root), "--json"])
        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0, payload)
        self.assertEqual(payload["status"], "NEEDS_MANUAL_REVIEW")
        self.assertTrue(any(gate["rule"] == "PAGE-METRICS-001" and gate["status"] == "PENDING" for gate in payload["page_gates"]))

        (self.root / "build" / "latex").mkdir(parents=True)
        (self.root / "build" / "latex" / "paper.pdf").write_bytes(b"%PDF-1.4\n")
        output = StringIO()
        completed = subprocess.CompletedProcess(["pdfinfo", "paper.pdf"], 0, stdout="Pages: 35\nPage size: 595.28 x 841.89 pts (A4)\n", stderr="")
        with patch("mmcore.pdfmetrics.subprocess.run", return_value=completed), redirect_stdout(output):
            exit_code = main(["audit", str(self.root), "--json"])
        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0, payload)
        self.assertEqual(payload["status"], "NEEDS_MANUAL_REVIEW")
        self.assertEqual(payload["page_metrics"]["status"], "PENDING")

    def test_audit_rejects_placeholder_source(self):
        write_complete_audit_project(self.root, paper_text="TBD")
        output = StringIO()
        with redirect_stdout(output):
            exit_code = main(["audit", str(self.root), "--json"])
        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertEqual(payload["status"], "FAIL")
        self.assertTrue(any(gate["rule"] == "LATEX-PLACEHOLDER-001" for gate in payload["page_gates"]))

    def test_formal_audit_includes_failed_g1_gate(self):
        write_complete_audit_project(self.root)
        config = json.loads((self.root / "mathmodel.json").read_text(encoding="utf-8"))
        config["execution_mode"] = "competition_assisted"
        (self.root / "mathmodel.json").write_text(json.dumps(config), encoding="utf-8")
        (self.root / "build" / "latex").mkdir(parents=True)
        (self.root / "build" / "latex" / "paper.pdf").write_bytes(b"%PDF-1.4\n")
        self.write_aux()
        output = StringIO()
        completed = subprocess.CompletedProcess(["pdfinfo", "paper.pdf"], 0, stdout="Pages: 35\nPage size: 595.28 x 841.89 pts (A4)\n", stderr="")
        with patch("mmcore.pdfmetrics.subprocess.run", return_value=completed), redirect_stdout(output):
            exit_code = main(["audit", str(self.root), "--json"])
        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 1, payload)
        self.assertEqual(payload["g1"]["status"], "FAIL")
        self.assertTrue(any(gate["rule"] == "G1-PROBLEM-INTERPRETATION-001" and gate["status"] == "FAIL" for gate in payload["page_gates"]))

    def test_formal_audit_includes_failed_g2_and_g3_gates(self):
        write_complete_audit_project(self.root)
        config = json.loads((self.root / "mathmodel.json").read_text(encoding="utf-8"))
        config["execution_mode"] = "competition_assisted"
        (self.root / "mathmodel.json").write_text(json.dumps(config), encoding="utf-8")
        (self.root / "build" / "latex").mkdir(parents=True)
        (self.root / "build" / "latex" / "paper.pdf").write_bytes(b"%PDF-1.4\n")
        self.write_aux()
        output = StringIO()
        completed = subprocess.CompletedProcess(["pdfinfo", "paper.pdf"], 0, stdout="Pages: 35\nPage size: 595.28 x 841.89 pts (A4)\n", stderr="")
        with patch("mmcore.pdfmetrics.subprocess.run", return_value=completed), redirect_stdout(output):
            exit_code = main(["audit", str(self.root), "--json"])
        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 1, payload)
        self.assertEqual(payload["model_tournament"]["status"], "FAIL")
        self.assertTrue(any(gate["rule"] == "G2-MODEL-SEARCH-001" and gate["status"] == "FAIL" for gate in payload["page_gates"]))
        self.assertTrue(any(gate["rule"] == "G3-MODEL-SELECTION-001" and gate["status"] == "FAIL" for gate in payload["page_gates"]))
        report = json.loads((self.root / "build" / "quality-report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["model_tournament"]["status"], "FAIL")

    def test_formal_build_persists_model_tournament_report(self):
        write_complete_audit_project(self.root)
        config = json.loads((self.root / "mathmodel.json").read_text(encoding="utf-8"))
        config["execution_mode"] = "competition_assisted"
        (self.root / "mathmodel.json").write_text(json.dumps(config), encoding="utf-8")
        output = StringIO()
        with patch("mathmodel.compile_latex", return_value={"status": "FAILED", "errors": [], "pdf": "", "aux": ""}), redirect_stdout(output):
            exit_code = main(["build", str(self.root), "--json"])
        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 1, payload)
        report = json.loads((self.root / "build" / "quality-report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["model_tournament"]["status"], "FAIL")

    def test_formal_audit_persists_semantic_validation_report(self):
        write_complete_audit_project(self.root)
        config = json.loads((self.root / "mathmodel.json").read_text(encoding="utf-8"))
        config["execution_mode"] = "competition_assisted"
        (self.root / "mathmodel.json").write_text(json.dumps(config), encoding="utf-8")
        (self.root / "build" / "latex").mkdir(parents=True)
        (self.root / "build" / "latex" / "paper.pdf").write_bytes(b"%PDF-1.4\n")
        self.write_aux()
        output = StringIO()
        completed = subprocess.CompletedProcess(["pdfinfo", "paper.pdf"], 0, stdout="Pages: 35\nPage size: 595.28 x 841.89 pts (A4)\n", stderr="")
        with patch("mmcore.pdfmetrics.subprocess.run", return_value=completed), redirect_stdout(output):
            exit_code = main(["audit", str(self.root), "--json"])
        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 1, payload)
        report = json.loads((self.root / "build" / "quality-report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["semantic_validation"]["status"], "FAIL")
        self.assertTrue(any(gate["rule"] == "G4-SEMANTIC-VALIDATION-001" and gate["status"] == "FAIL" for gate in payload["page_gates"]))

    def test_formal_audit_persists_phase5_gates(self):
        write_complete_audit_project(self.root)
        config = json.loads((self.root / "mathmodel.json").read_text(encoding="utf-8"))
        config["execution_mode"] = "competition_assisted"
        (self.root / "mathmodel.json").write_text(json.dumps(config), encoding="utf-8")
        (self.root / "build" / "latex").mkdir(parents=True)
        (self.root / "build" / "latex" / "paper.pdf").write_bytes(b"%PDF-1.4\n")
        self.write_aux()
        output = StringIO()
        completed = subprocess.CompletedProcess(["pdfinfo", "paper.pdf"], 0, stdout="Pages: 35\nPage size: 595.28 x 841.89 pts (A4)\n", stderr="")
        with patch("mmcore.pdfmetrics.subprocess.run", return_value=completed), redirect_stdout(output):
            exit_code = main(["audit", str(self.root), "--json"])
        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 1, payload)
        self.assertEqual(payload["model_architecture"]["status"], "FAIL")
        self.assertEqual(payload["results_freeze"]["status"], "FAIL")
        self.assertTrue(any(gate["rule"] == "G5.5-CROSS-QUESTION-COHERENCE-001" for gate in payload["page_gates"]))
        self.assertTrue(any(gate["rule"] == "G6-HUMAN-VERIFIED-FREEZE-001" for gate in payload["page_gates"]))

    @unittest.skipUnless(os.name == "nt", "fake .cmd engine is a Windows integration test")
    def test_compile_runs_fake_engine_twice_and_preserves_logs(self):
        main_tex = self.root / "paper" / "main.tex"
        main_tex.parent.mkdir(parents=True)
        main_tex.write_text("\\documentclass{article}", encoding="utf-8")
        engine = self.root / "fake-xelatex.cmd"
        output_dir = self.root / "build" / "latex"
        engine.write_text(
            "@echo off\r\n"
            "setlocal\r\n"
            f"if not exist \"{output_dir}\" mkdir \"{output_dir}\"\r\n"
            f"> \"{output_dir}\\paper.aux\" echo \\newlabel{{mm:body-start}}{{{{}}{{1}}}}\r\n"
            f"> \"{output_dir}\\paper.pdf\" type nul\r\n"
            f"> \"{output_dir}\\paper.log\" echo Fake LaTeX log.\r\n"
            "echo fake engine pass\r\n"
            "exit /b 0\r\n",
            encoding="utf-8",
        )
        result = compile_latex(self.root, main_tex, str(engine), "paper")
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["exit_codes"], [0, 0])
        self.assertTrue(Path(result["pdf"]).is_file())
        self.assertTrue(all(Path(path).is_file() for path in result["logs"]))
        self.assertEqual(len(result["commands"]), 2)
        self.assertEqual(result["commands"][0][1:5], ["-interaction=nonstopmode", "-halt-on-error", f"-output-directory={output_dir}", "-jobname=paper"])

    def test_compile_returns_structured_failure_for_missing_engine(self):
        main_tex = self.root / "paper" / "main.tex"
        main_tex.parent.mkdir(parents=True)
        main_tex.write_text("paper", encoding="utf-8")
        result = compile_latex(self.root, main_tex, "missing-xelatex-engine", "paper")
        self.assertEqual(result["status"], "FAILED")
        self.assertTrue(any(item["rule"] == "LATEX-ENGINE-001" for item in result["errors"]))

    @unittest.skipUnless(os.name == "nt", "fake .cmd engine is a Windows integration test")
    def test_build_cli_writes_page_metrics_and_gate_report(self):
        main_tex = self.root / "paper" / "main.tex"
        main_tex.parent.mkdir(parents=True)
        main_tex.write_text("paper", encoding="utf-8")
        engine = self.root / "fake-xelatex.cmd"
        engine.write_text("@echo off\r\nexit /b 1\r\n", encoding="utf-8")
        (self.root / "mathmodel.json").write_text(json.dumps(valid_config(str(engine))), encoding="utf-8")
        output = StringIO()
        with redirect_stdout(output):
            exit_code = main(["build", str(self.root), "--json"])
        payload = json.loads(output.getvalue())
        report = json.loads((self.root / "build" / "quality-report.json").read_text(encoding="utf-8"))
        self.assertEqual(exit_code, 1)
        self.assertEqual(payload["compile"]["status"], "FAILED")
        self.assertIn("page_metrics", report)
        self.assertIn("page_gates", report)


if __name__ == "__main__":
    unittest.main()
