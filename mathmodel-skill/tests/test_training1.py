"""Integration certification for the real traning1 optimization project."""

from __future__ import annotations

import json
import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TRAINING1 = ROOT / "traning1"
SCRIPTS = ROOT / "mathmodel-skill" / "scripts"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mathmodel import main


def invoke_json(argv: list[str]) -> tuple[int, dict]:
    """Run the real CLI and return its JSON report."""
    output = StringIO()
    with redirect_stdout(output):
        exit_code = main(argv)
    return exit_code, json.loads(output.getvalue())


class Training1IntegrationTests(unittest.TestCase):
    def test_training1_has_traceable_problem_to_pdf_chain(self):
        """A missing registry link, figure role, q3 result, or page gate must fail."""
        exit_code, report = invoke_json(["build", str(TRAINING1), "--json"])

        self.assertEqual(exit_code, 0, report)
        self.assertEqual(report["status"], "PASS", report)
        self.assertGreaterEqual(report["page_metrics"]["body_pages"], 26)
        self.assertLessEqual(report["page_metrics"]["appendix_body_ratio"], 0.25)
        self.assertFalse(
            [
                gate
                for gate in report["page_gates"]
                if gate["severity"] == "FAIL" and gate["status"] != "PASS"
            ],
            report["page_gates"],
        )

        problem_map = json.loads((TRAINING1 / "artifacts" / "problem-map.json").read_text(encoding="utf-8"))
        self.assertIn("q3", [question["id"] for question in problem_map["questions"]])

        figures = json.loads((TRAINING1 / "artifacts" / "figure-registry.json").read_text(encoding="utf-8"))
        self.assertEqual(
            {figure["role"] for figure in figures["figures"]},
            {"data", "method", "result", "validation"},
        )

        quality = json.loads(Path(report["report"]).read_text(encoding="utf-8"))
        self.assertEqual(quality["contract"]["status"], "PASS", quality)
        self.assertFalse(
            [
                check
                for check in quality["contract"]["checks"]
                if check["severity"] == "FAIL" and check["status"] == "FAIL"
            ],
            quality,
        )


if __name__ == "__main__":
    unittest.main()
