"""Asset-level contract tests for the reusable mathmodel coordination skill."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
REPOSITORY = SKILL.parent
CLI = SKILL / "scripts" / "mathmodel.py"
FIX_REPORT = REPOSITORY / ".superpowers" / "sdd" / "mathmodel-paper-factory" / "task-7-fix-report.md"
FIX2_REPORT = REPOSITORY / ".superpowers" / "sdd" / "mathmodel-paper-factory" / "task-7-fix2-report.md"
FIX3_REPORT = REPOSITORY / ".superpowers" / "sdd" / "mathmodel-paper-factory" / "task-7-fix3-report.md"
EXPECTED_REFERENCES = {
    "references/workflow.md",
    "references/evidence-contracts.md",
    "references/paper-architecture.md",
    "references/model-validation.md",
    "references/quality-gates.md",
    "references/figure-system.md",
    "references/forecasting.md",
    "references/optimization.md",
    "references/evaluation.md",
    "references/classification.md",
    "references/statistics.md",
    "references/simulation.md",
    "references/mechanism.md",
    "references/hybrid.md",
    "references/latex-template.md",
    "references/modeling-methods.md",
    "references/modeling-paper.md",
    "references/quality-checklist.md",
    "references/research-and-citation.md",
}
REFERENCE_CONTENT = {
    "references/workflow.md": ("inspect", "build", "audit"),
    "references/evidence-contracts.md": ("result-registry.json", "validation.json"),
    "references/paper-architecture.md": ("mm:body-start", "mm:appendix-end"),
    "references/model-validation.md": ("Forecasting", "Optimization", "Evaluation"),
    "references/quality-gates.md": ("release blockers", "manual review"),
    "references/figure-system.md": ("data understanding", "validation"),
    "references/forecasting.md": ("rolling-origin", "MAE"),
    "references/optimization.md": ("optimality gap", "best feasible solution found"),
    "references/evaluation.md": ("normalization", "ranking"),
    "references/classification.md": ("stratified split", "leakage"),
    "references/statistics.md": ("estimand", "uncertainty"),
    "references/simulation.md": ("replication", "convergence"),
    "references/mechanism.md": ("Dimensional", "boundary"),
    "references/hybrid.md": ("dependency graph", "uncertainty"),
    "references/latex-template.md": ("XeLaTeX", "\\label"),
    "references/modeling-methods.md": ("simplest model", "random seed"),
    "references/modeling-paper.md": ("abstract", "validation"),
    "references/quality-checklist.md": ("traceable", "overfull"),
    "references/research-and-citation.md": ("primary sources", "DOI"),
}


def frontmatter(text: str) -> str:
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise AssertionError("SKILL.md must contain YAML front matter")
    return parts[1]


def referenced_files(text: str) -> set[str]:
    return {
        target
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)
        if target.startswith(("references/", "agents/"))
    }


def parse_interface_metadata(text: str) -> dict[str, str]:
    """Parse the constrained, string-only local OpenAI interface shape."""
    lines = [line for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    if not lines or lines[0] != "interface:":
        raise AssertionError("openai.yaml must start with an interface mapping")
    result: dict[str, str] = {}
    for line in lines[1:]:
        match = re.fullmatch(r'  ([a-z_]+): "([^"\\]*(?:\\.[^"\\]*)*)"', line)
        if match is None:
            raise AssertionError(f"unsupported interface YAML line: {line}")
        key, value = match.groups()
        if key in result:
            raise AssertionError(f"duplicate interface key: {key}")
        result[key] = bytes(value, "utf-8").decode("unicode_escape")
    return result


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def create_minimal_pdf(path: Path, pages: int) -> None:
    """Write a valid blank A4 PDF that pdfinfo can measure without external libraries."""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        (f"<< /Type /Pages /Kids [{' '.join(f'{number} 0 R' for number in range(3, 3 + pages))}] /Count {pages} >>").encode(),
    ]
    objects.extend(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595.276 841.89] >>" for _ in range(pages))
    body = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, content in enumerate(objects, start=1):
        offsets.append(len(body))
        body.extend(f"{number} 0 obj\n".encode())
        body.extend(content)
        body.extend(b"\nendobj\n")
    xref = len(body)
    body.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    body.extend(b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:]))
    body.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)


def config(project_id: str, problem_type: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "project_id": project_id,
        "title": project_id,
        "contest": "CUMCM",
        "problem_type": problem_type,
        "inputs": {"statements": [], "attachments": []},
        "commands": {"analyze": []},
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


def prepare_fixture_cli_replay(root: Path, *, prefix: str, problem_type: str, unsupported_claim: bool) -> None:
    """Prepare registries for direct CLI coverage; do not treat this as prompt-to-agent production."""
    question_id = f"Q-{prefix}-1"
    model_id = f"M-{prefix}-1"
    result_id = f"R-{prefix}-1"
    validation_id = f"V-{prefix}-1"
    claim_id = f"C-{prefix}-1"
    claimed_results = [f"R-{prefix}-MISSING"] if unsupported_claim else [result_id]
    write_json(root / "mathmodel.json", config(f"{prefix.lower()}-forward-001", problem_type))
    (root / "paper").mkdir(parents=True, exist_ok=True)
    (root / "paper" / "main.tex").write_text("\\documentclass{article}\\begin{document}Ready\\end{document}", encoding="utf-8")
    artifacts = {
        "problem-map": {"questions": [{"id": question_id, "model_ids": [model_id], "result_ids": [result_id], "validation_ids": [validation_id], "claim_ids": [claim_id]}]},
        "data-audit": {"status": "SUCCESS", "files": []},
        "model-registry": {"models": [{"id": model_id, "question_id": question_id}]},
        "result-registry": {"results": [{"id": result_id, "source": f"analysis/{result_id}.py", "value": 1, "unit": "unit"}]},
        "claim-registry": {"claims": [{"id": claim_id, "result_ids": claimed_results, "validation_ids": [validation_id]}]},
        "figure-registry": {"figures": [
            {"id": f"F-{prefix}-DATA", "role": "data", "file": "paper/figures/data.pdf", "claim_ids": [claim_id]},
            {"id": f"F-{prefix}-METHOD", "role": "method", "file": "paper/figures/method.pdf", "claim_ids": [claim_id]},
            {"id": f"F-{prefix}-RESULT", "role": "result", "file": "paper/figures/result.pdf", "claim_ids": [claim_id]},
            {"id": f"F-{prefix}-VALIDATION", "role": "validation", "file": "paper/figures/validation.pdf", "claim_ids": [claim_id]},
        ]},
        "validation": {"validations": [{"id": validation_id, "status": "PASS", "question_id": question_id}]},
    }
    for name, value in artifacts.items():
        write_json(root / "artifacts" / f"{name}.json", value)
    (root / "analysis").mkdir(exist_ok=True)
    (root / "analysis" / f"{result_id}.py").write_text("result = 1\n", encoding="utf-8")
    for figure in artifacts["figure-registry"]["figures"]:
        path = root / figure["file"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"%PDF-1.4\n")


def run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *arguments],
        check=False,
        capture_output=True,
        encoding="utf-8",
    )


def load_replay_registries(root: Path) -> dict[str, dict[str, object]]:
    names = (
        "problem-map",
        "data-audit",
        "model-registry",
        "result-registry",
        "claim-registry",
        "figure-registry",
        "validation",
    )
    return {
        name: json.loads((root / "artifacts" / f"{name}.json").read_text(encoding="utf-8"))
        for name in names
    }


class SkillAssetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = (SKILL / "SKILL.md").read_text(encoding="utf-8")

    def test_skill_description_is_searchable_and_uses_trigger_form(self) -> None:
        metadata = frontmatter(self.text)
        self.assertRegex(metadata, r"(?m)^description: Use when")
        for trigger in (
            "CUMCM",
            "paper",
            "modeling",
            "LaTeX",
            "data",
            "reproducibility",
            "page-balance",
            "quality-audit",
            "compile",
        ):
            self.assertIn(trigger, metadata, trigger)

    def test_skill_routes_all_supported_cli_subcommands(self) -> None:
        help_result = subprocess.run(
            [sys.executable, str(CLI), "--help"],
            check=False,
            capture_output=True,
            encoding="utf-8",
        )
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        for command in ("init", "adopt", "inspect", "build", "audit"):
            self.assertRegex(help_result.stdout, rf"\b{command}\b")
        for route in (
            "mathmodel.py init TARGET --id ID --title TITLE --type TYPE",
            "mathmodel.py adopt PROJECT",
            "mathmodel.py inspect PROJECT --json",
            "mathmodel.py build PROJECT --json",
            "mathmodel.py audit PROJECT --json",
        ):
            self.assertIn(route, self.text)

    def test_skill_enforces_evidence_page_boundaries_and_manual_release_gate(self) -> None:
        self.assertIn("result-registry", self.text)
        self.assertIn("evidence", self.text.casefold())
        for label in ("mm:body-start", "mm:body-end", "mm:appendix-start", "mm:appendix-end"):
            self.assertIn(label, self.text)
        self.assertIn("total, body, reference, and appendix page counts", self.text)
        self.assertIn("appendix/body ratio", self.text)
        self.assertRegex(self.text, r"reject an unsupported conclusion", re.IGNORECASE)
        self.assertRegex(self.text, r"before asserting accuracy, optimality, robustness, improvement, or significance")
        self.assertRegex(self.text, r"Reject a release when the body misses its configured target")
        self.assertRegex(self.text, r"both CLI evidence and manual review are complete")
        self.assertRegex(self.text, r"leave the release blocked")

    def test_all_declared_coordination_references_are_linked_and_exist(self) -> None:
        references = referenced_files(self.text)
        self.assertEqual(references, EXPECTED_REFERENCES)
        for relative in EXPECTED_REFERENCES:
            self.assertTrue((SKILL / relative).is_file(), relative)
            content = (SKILL / relative).read_text(encoding="utf-8")
            for required in REFERENCE_CONTENT[relative]:
                self.assertIn(required, content, relative)

    def test_openai_metadata_parses_to_supported_semantic_interface(self) -> None:
        metadata = parse_interface_metadata((SKILL / "agents" / "openai.yaml").read_text(encoding="utf-8"))
        self.assertEqual(set(metadata), {"display_name", "short_description", "default_prompt"})
        self.assertEqual(metadata["display_name"], "MathModel Paper Factory")
        self.assertGreaterEqual(len(metadata["short_description"]), 25)
        self.assertLessEqual(len(metadata["short_description"]), 64)
        self.assertTrue(metadata["default_prompt"].startswith("Use $mathmodel-skill "))
        self.assertIn("CUMCM paper", metadata["default_prompt"])

    def test_fix_report_records_reproducible_nonproduction_forward_tests(self) -> None:
        report = FIX_REPORT.read_text(encoding="utf-8")
        self.assertIn("No production project or fixture was modified", report)
        for marker in ("Optimization forward test", "Forecasting forward test", "Page-balance forward test"):
            self.assertIn(marker, report)
        for command in (
            "mathmodel.py init --help",
            "mathmodel.py inspect --help",
            "mathmodel.py audit --help",
        ):
            self.assertIn(command, report)
        for evidence in ("Q-OPT-1", "R-OPT-1", "V-OPT-1", "R-FOR-1", "V-FOR-1", "PAGE-BODY-001"):
            self.assertIn(evidence, report)

    def test_optimization_replay_audits_generated_registries_and_blocks_unsupported_claim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "optimization"
            initialized = run_cli("init", str(root), "--id", "opt-forward-001", "--title", "Optimization", "--type", "optimization")
            inspected = run_cli("inspect", str(root), "--json")
            self.assertEqual(initialized.returncode, 0, initialized.stderr)
            self.assertEqual(inspected.returncode, 0, inspected.stderr)
            prepare_fixture_cli_replay(root, prefix="OPT", problem_type="optimization", unsupported_claim=True)
            audited = run_cli("audit", str(root), "--json")

            payload = json.loads(audited.stdout)
            report = json.loads((root / "build" / "quality-report.json").read_text(encoding="utf-8"))
            registries = load_replay_registries(root)
            question = registries["problem-map"]["questions"][0]
            model = registries["model-registry"]["models"][0]
            result = registries["result-registry"]["results"][0]
            claim = registries["claim-registry"]["claims"][0]
            validation = registries["validation"]["validations"][0]
            self.assertEqual(audited.returncode, 1)
            self.assertEqual(payload["status"], "FAIL")
            self.assertEqual(report["contract"]["status"], "FAIL")
            self.assertTrue(any(check["rule"] == "EVIDENCE-CLAIM-001" and check["status"] == "FAIL" for check in report["contract"]["checks"]))
            self.assertEqual(question, {"id": "Q-OPT-1", "model_ids": ["M-OPT-1"], "result_ids": ["R-OPT-1"], "validation_ids": ["V-OPT-1"], "claim_ids": ["C-OPT-1"]})
            self.assertEqual(model, {"id": "M-OPT-1", "question_id": "Q-OPT-1"})
            self.assertEqual(result["id"], "R-OPT-1")
            self.assertEqual(result["source"], "analysis/R-OPT-1.py")
            self.assertEqual(claim, {"id": "C-OPT-1", "result_ids": ["R-OPT-MISSING"], "validation_ids": ["V-OPT-1"]})
            self.assertEqual(validation, {"id": "V-OPT-1", "status": "PASS", "question_id": "Q-OPT-1"})
            self.assertTrue(all(figure["claim_ids"] == ["C-OPT-1"] for figure in registries["figure-registry"]["figures"]))

    def test_forecasting_replay_audits_generated_registries_and_blocks_unsupported_claim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "forecasting"
            initialized = run_cli("init", str(root), "--id", "for-forward-001", "--title", "Forecasting", "--type", "forecasting")
            inspected = run_cli("inspect", str(root), "--json")
            self.assertEqual(initialized.returncode, 0, initialized.stderr)
            self.assertEqual(inspected.returncode, 0, inspected.stderr)
            prepare_fixture_cli_replay(root, prefix="FOR", problem_type="forecasting", unsupported_claim=True)
            audited = run_cli("audit", str(root), "--json")

            payload = json.loads(audited.stdout)
            report = json.loads((root / "build" / "quality-report.json").read_text(encoding="utf-8"))
            registries = load_replay_registries(root)
            question = registries["problem-map"]["questions"][0]
            model = registries["model-registry"]["models"][0]
            result = registries["result-registry"]["results"][0]
            claim = registries["claim-registry"]["claims"][0]
            validation = registries["validation"]["validations"][0]
            self.assertEqual(audited.returncode, 1)
            self.assertEqual(payload["status"], "FAIL")
            self.assertTrue(any(check["rule"] == "EVIDENCE-CLAIM-001" and check["status"] == "FAIL" for check in report["contract"]["checks"]))
            self.assertEqual(question, {"id": "Q-FOR-1", "model_ids": ["M-FOR-1"], "result_ids": ["R-FOR-1"], "validation_ids": ["V-FOR-1"], "claim_ids": ["C-FOR-1"]})
            self.assertEqual(model, {"id": "M-FOR-1", "question_id": "Q-FOR-1"})
            self.assertEqual(result["id"], "R-FOR-1")
            self.assertEqual(result["source"], "analysis/R-FOR-1.py")
            self.assertEqual(claim, {"id": "C-FOR-1", "result_ids": ["R-FOR-MISSING"], "validation_ids": ["V-FOR-1"]})
            self.assertEqual(validation, {"id": "V-FOR-1", "status": "PASS", "question_id": "Q-FOR-1"})
            self.assertTrue(all(figure["claim_ids"] == ["C-FOR-1"] for figure in registries["figure-registry"]["figures"]))

    def test_page_balance_replay_reports_body_and_appendix_hard_gates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "page-balance"
            initialized = run_cli("init", str(root), "--id", "page-forward-001", "--title", "Page balance", "--type", "optimization")
            inspected = run_cli("inspect", str(root), "--json")
            self.assertEqual(initialized.returncode, 0, initialized.stderr)
            self.assertEqual(inspected.returncode, 0, inspected.stderr)
            prepare_fixture_cli_replay(root, prefix="PAGE", problem_type="optimization", unsupported_claim=False)
            built = run_cli("build", str(root), "--json")
            build_payload = json.loads(built.stdout)
            self.assertIn(built.returncode, (0, 1))
            self.assertIn(build_payload["compile"]["status"], ("SUCCESS", "FAILED"))
            self.assertIn(build_payload["page_metrics"]["status"], ("SUCCESS", "FAILED", "PENDING"))
            create_minimal_pdf(root / "build" / "latex" / "paper.pdf", pages=32)
            (root / "build" / "latex" / "paper.aux").write_text(
                "\n".join((
                    r"\newlabel{mm:body-start}{{}{1}}",
                    r"\newlabel{mm:body-end}{{}{20}}",
                    r"\newlabel{mm:references-start}{{}{21}}",
                    r"\newlabel{mm:references-end}{{}{22}}",
                    r"\newlabel{mm:appendix-start}{{}{23}}",
                    r"\newlabel{mm:appendix-end}{{}{32}}",
                )),
                encoding="utf-8",
            )
            audited = run_cli("audit", str(root), "--json")

            payload = json.loads(audited.stdout)
            report = json.loads((root / "build" / "quality-report.json").read_text(encoding="utf-8"))
            registries = load_replay_registries(root)
            question = registries["problem-map"]["questions"][0]
            model = registries["model-registry"]["models"][0]
            result = registries["result-registry"]["results"][0]
            claim = registries["claim-registry"]["claims"][0]
            validation = registries["validation"]["validations"][0]
            gates = {gate["rule"]: gate for gate in report["page_gates"]}
            self.assertEqual(audited.returncode, 1)
            self.assertEqual(payload["status"], "FAIL")
            self.assertEqual(report["page_metrics"]["total_pages"], 32)
            self.assertEqual(report["page_metrics"]["body_pages"], 20)
            self.assertEqual(report["page_metrics"]["appendix_pages"], 10)
            self.assertEqual(report["page_metrics"]["appendix_body_ratio"], 0.5)
            self.assertEqual(gates["PAGE-BODY-001"]["status"], "FAIL")
            self.assertEqual(gates["PAGE-APPENDIX-001"]["status"], "FAIL")
            self.assertEqual(question, {"id": "Q-PAGE-1", "model_ids": ["M-PAGE-1"], "result_ids": ["R-PAGE-1"], "validation_ids": ["V-PAGE-1"], "claim_ids": ["C-PAGE-1"]})
            self.assertEqual(model, {"id": "M-PAGE-1", "question_id": "Q-PAGE-1"})
            self.assertEqual(result["id"], "R-PAGE-1")
            self.assertEqual(result["source"], "analysis/R-PAGE-1.py")
            self.assertEqual(claim, {"id": "C-PAGE-1", "result_ids": ["R-PAGE-1"], "validation_ids": ["V-PAGE-1"]})
            self.assertEqual(validation, {"id": "V-PAGE-1", "status": "PASS", "question_id": "Q-PAGE-1"})
            self.assertTrue(all(figure["claim_ids"] == ["C-PAGE-1"] for figure in registries["figure-registry"]["figures"]))

    def test_fix2_report_distinguishes_executed_replays_from_cli_route_syntax(self) -> None:
        report = FIX2_REPORT.read_text(encoding="utf-8")
        self.assertIn("CLI route syntax baseline", report)
        self.assertIn("Executed prepared-fixture CLI replays", report)
        self.assertIn("do not execute a prompt through an agent", report)
        for evidence in ("EVIDENCE-CLAIM-001", '"body_pages": 20', '"appendix_body_ratio": 0.5'):
            self.assertIn(evidence, report)

    def test_fix3_report_names_prepared_fixture_cli_coverage_boundary(self) -> None:
        report = FIX3_REPORT.read_text(encoding="utf-8")
        self.assertIn("prepared-fixture CLI replay harness", report)
        self.assertIn("does not execute a prompt through an agent", report)
        self.assertIn("not prompt-to-agent registry production", report)


if __name__ == "__main__":
    unittest.main()
