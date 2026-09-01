import json
import tempfile
import unittest
from pathlib import Path
import sys

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mmcore.submission import evaluate_submission


class SubmissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "paper").mkdir()
        (self.root / "paper" / "main.tex").write_text(r"\documentclass{article}\input{refs.tex}\begin{document}AI usage disclosure.\cite{ref-one}\end{document}", encoding="utf-8")
        (self.root / "paper" / "refs.tex").write_text(r"\begin{thebibliography}{9}\bibitem{ref-one}Public source.\end{thebibliography}", encoding="utf-8")
        (self.root / "build").mkdir()
        (self.root / "build" / "paper.pdf").write_bytes(b"%PDF-1.7 fixture")
        (self.root / "artifacts").mkdir()
        (self.root / "artifacts" / "submission-manifest.json").write_text(json.dumps({"supporting_materials": ["solve.py"], "source_programs": ["solve.py"]}), encoding="utf-8")
        (self.root / "solve.py").write_text("print('fixture')", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def config(self, mode="competition_assisted"):
        return {"execution_mode": mode, "paper": {"main": "paper/main.tex"}, "commands": {"solver": ["python", "solve.py"]}}

    def report(self):
        return {
            "status": "PASS",
            "compile": {"status": "SUCCESS", "pdf": str(self.root / "build" / "paper.pdf")},
            "page_metrics": {"status": "SUCCESS", "total_pages": 38},
            "page_gates": [{"rule": "PAGE-TOTAL-001", "status": "PASS"}],
            "quality": {"release_status": "PASS"},
            "compliance": {"status": "PASS"},
            "g1": {"status": "PASS"},
            "model_tournament": {"g2": {"status": "PASS"}, "g3": {"status": "PASS"}},
            "semantic_validation": {"g4": {"status": "PASS"}, "g5": {"status": "PASS"}},
            "model_architecture": {"status": "PASS"},
            "results_freeze": {"status": "PASS"},
            "writer_package": {"status": "PASS"},
            "review_registry": {"status": "PASS", "open_critical": []},
            "hash_checks": [{"status": "PASS"}],
        }

    def test_formal_submission_passes_only_with_complete_evidence(self):
        (self.root / "artifacts" / "ai-usage-ledger.jsonl").write_text("{}\n", encoding="utf-8")
        result = evaluate_submission(self.root, self.config(), self.report())
        self.assertEqual(result["status"], "PASS", result)
        self.assertTrue(all(item["status"] == "PASS" for item in result["checks"]))

    def test_missing_gate_blocks_submission(self):
        report = self.report()
        report["review_registry"] = {"status": "FAIL"}
        result = evaluate_submission(self.root, self.config(), report)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any(item["rule"] == "G9-GATE-001" for item in result["checks"]))

    def test_identity_in_source_blocks_submission(self):
        (self.root / "paper" / "main.tex").write_text("姓名：张三\\begin{document}AI usage disclosure.\\end{document}", encoding="utf-8")
        result = evaluate_submission(self.root, self.config(), self.report())
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any(item["rule"] == "G9-ANONYMITY-001" for item in result["checks"]))

    def test_research_mode_is_not_applicable(self):
        result = evaluate_submission(self.root, self.config("research_autonomous"), self.report())
        self.assertEqual(result["status"], "NOT_APPLICABLE")


if __name__ == "__main__":
    unittest.main()
