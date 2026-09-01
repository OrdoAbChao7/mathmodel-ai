"""Release packaging gates and deterministic bundle tests."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
TESTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

from mmcore.package import package
from test_end_to_end import FIXTURES, run_fixture


class ReleaseAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "fixture"
        shutil.copytree(FIXTURES / "forecasting", self.root)
        self.report = run_fixture(self.root)
        for name in ("source-manifest.json", "validation-report.json", "reproducibility.json"):
            (self.root / "build" / name).write_text("{}\n", encoding="utf-8")
        self.report.update({
            "source_manifest": "build/source-manifest.json",
            "validation_report": "build/validation-report.json",
            "reproducibility_summary": "build/reproducibility.json",
            "hash_checks": self.report.get("hash_checks", []),
        })

    def tearDown(self):
        self.tmp.cleanup()

    def test_package_refuses_body_shortfall(self):
        report = dict(self.report)
        report["page_metrics"] = {**report["metrics"], "body_pages": 10}
        report["page_gates"] = [{"rule": "PAGE-BODY-001", "severity": "FAIL", "status": "FAIL", "message": "body shortfall"}]
        result = package(self.root, report)
        self.assertEqual(result["status"], "BLOCKED")

    def test_package_refuses_appendix_ratio_and_pending_manual(self):
        report = dict(self.report)
        report["page_gates"] = [{"rule": "PAGE-APPENDIX-001", "severity": "FAIL", "status": "FAIL", "message": "ratio"}]
        report["quality"] = {**report["quality"], "manual_review": "PENDING"}
        result = package(self.root, report)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any(check["rule"] == "PACKAGE-MANUAL-001" for check in result["checks"]))

    def test_package_refuses_missing_pdf_or_quality_fail(self):
        report = dict(self.report)
        report["compile"] = {**report["compile"], "pdf": "build/latex/not-current.pdf"}
        report["pdf"] = "build/latex/not-current.pdf"
        report["quality"] = {**report["quality"], "release_status": "FAIL"}
        result = package(self.root, report)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any(check["rule"] == "PACKAGE-PDF-001" for check in result["checks"]))

    def test_package_refuses_failed_cumcm_compliance(self):
        report = dict(self.report)
        report["compliance"] = {"status": "FAIL", "mode": "competition_assisted"}
        result = package(self.root, report)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any(check["rule"] == "PACKAGE-COMPLIANCE-001" for check in result["checks"]))

    def test_formal_package_refuses_missing_cumcm_compliance(self):
        report = dict(self.report)
        report.pop("compliance", None)
        (self.root / "mathmodel.json").write_text(
            json.dumps({**json.loads((self.root / "mathmodel.json").read_text(encoding="utf-8")), "execution_mode": "competition_assisted"}),
            encoding="utf-8",
        )
        result = package(self.root, report)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any(check["rule"] == "PACKAGE-COMPLIANCE-001" for check in result["checks"]))

    def test_formal_package_refuses_missing_g1(self):
        report = dict(self.report)
        report.pop("compliance", None)
        report.pop("g1", None)
        config = json.loads((self.root / "mathmodel.json").read_text(encoding="utf-8"))
        config["execution_mode"] = "competition_assisted"
        (self.root / "mathmodel.json").write_text(json.dumps(config), encoding="utf-8")
        result = package(self.root, report)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any(check["rule"] == "PACKAGE-INTERPRETATION-001" for check in result["checks"]))

    def test_clean_package_has_unique_page_hash_name_and_manifest(self):
        result = package(self.root, self.report)
        self.assertEqual(result["status"], "PASS", result)
        pdf = Path(result["pdf"])
        self.assertRegex(pdf.name, r"-3p-[0-9a-f]{8}\.pdf$")
        manifest = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))
        self.assertRegex(manifest["pdf"]["sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(manifest["status"], "PASS")
        self.assertIn("source_snapshot", manifest)
        self.assertIn("reproducibility", manifest)

    def test_package_uses_page_metrics_pdf_when_audit_report_has_no_compile_block(self):
        report = dict(self.report)
        report.pop("compile", None)
        report.pop("pdf", None)
        report["page_metrics"] = {**report["metrics"], "pdf": self.report["compile"]["pdf"]}
        result = package(self.root, report)
        self.assertEqual(result["status"], "PASS", result)


if __name__ == "__main__":
    unittest.main()
