import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mmcore.config import load_config
from mmcore.scaffold import adopt_project, init_project
from mathmodel import main


class ScaffoldTests(unittest.TestCase):
    def setUp(self):
        self._tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tempdir.name)

    def tearDown(self):
        self._tempdir.cleanup()

    def test_init_creates_contract_and_required_directories(self):
        created = init_project(self.root, "demo-001", "Demo", "forecasting")
        self.assertTrue((self.root / "mathmodel.json").exists())
        self.assertTrue((self.root / "analysis" / "run.py").exists())
        self.assertTrue((self.root / "paper" / "main.tex").exists())
        self.assertGreaterEqual(len(created), 8)
        config = load_config(self.root)
        self.assertEqual(config["project_id"], "demo-001")
        self.assertEqual(config["title"], "Demo")
        self.assertEqual(config["schema_version"], 2)

    def test_init_never_overwrites_existing_file(self):
        old = self.root / "paper" / "main.tex"
        old.parent.mkdir(parents=True)
        old.write_text("user source", encoding="utf-8")
        init_project(self.root, "demo-001", "Demo", "optimization")
        self.assertEqual(old.read_text(encoding="utf-8"), "user source")

    def test_adopt_preserves_existing_paper_and_solver(self):
        solver = self.root / "solve.py"
        solver.write_text("user code", encoding="utf-8")
        paper = self.root / "main.tex"
        paper.write_text("user paper", encoding="utf-8")
        created = adopt_project(self.root)
        self.assertEqual(solver.read_text(encoding="utf-8"), "user code")
        self.assertEqual(paper.read_text(encoding="utf-8"), "user paper")
        self.assertTrue((self.root / "adoption-report.json").exists())
        self.assertIn(self.root / "adoption-report.json", created)

    def test_paper_template_has_executable_boundary_labels_and_clearpages(self):
        template = (
            Path(__file__).resolve().parents[1] / "assets" / "project-template" / "paper" / "main.tex"
        ).read_text(encoding="utf-8")
        for label in ("mm:body-start", "mm:body-end", "mm:appendix-start", "mm:appendix-end"):
            self.assertIn(rf"\label{{{label}}}", template)
        self.assertNotIn("% mm:body-start", template)
        self.assertNotIn("% mm:body-end", template)
        self.assertNotIn("% mm:appendix-start", template)
        self.assertNotIn("% mm:appendix-end", template)
        self.assertGreaterEqual(template.count(r"\clearpage"), 2)

    def test_adoption_report_categorizes_files_and_lists_framework_conflicts(self):
        files = {
            "problem/statement.pdf": "statement",
            "data/raw/attachment.xlsx": "attachment",
            "paper/submission.tex": "paper",
            "solve.py": "solver",
            "paper/main.tex": "user paper",
            "analysis/run.py": "user adapter",
        }
        for relative, content in files.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

        adopt_project(self.root)
        report = json.loads((self.root / "adoption-report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["statements"], ["problem/statement.pdf"])
        self.assertEqual(report["attachments"], ["data/raw/attachment.xlsx"])
        self.assertEqual(report["papers"], ["paper/main.tex", "paper/submission.tex"])
        self.assertEqual(report["scripts"], ["analysis/run.py", "solve.py"])
        self.assertEqual(report["conflicts"], ["analysis/run.py", "paper/main.tex"])
        self.assertEqual((self.root / "paper/main.tex").read_text(encoding="utf-8"), "user paper")
        self.assertEqual((self.root / "analysis/run.py").read_text(encoding="utf-8"), "user adapter")

    def test_adopt_does_not_replace_existing_configuration(self):
        config = self.root / "mathmodel.json"
        original = {
            "schema_version": 2, "project_id": "existing", "title": "Existing", "contest": "CUMCM",
            "problem_type": "hybrid", "execution_mode": "competition_assisted",
        }
        config.write_text(json.dumps(original), encoding="utf-8")
        adopt_project(self.root)
        self.assertEqual(json.loads(config.read_text(encoding="utf-8")), original)
        self.assertIn("H1_PROBLEM_UNDERSTANDING", (self.root / "CUMCM-WORKFLOW.md").read_text(encoding="utf-8"))

    def test_cli_dispatches_init_and_adopt(self):
        target = self.root / "project"
        self.assertEqual(
            main(["init", str(target), "--id", "cli-001", "--title", "CLI", "--type", "hybrid"]),
            0,
        )
        self.assertTrue((target / "mathmodel.json").exists())
        self.assertEqual(main(["adopt", str(target)]), 0)

    def test_init_formal_mode_writes_mode_and_human_workflow_without_fake_signoffs(self):
        target = self.root / "formal"
        self.assertEqual(
            main(["init", str(target), "--id", "formal-001", "--title", "Formal", "--type", "hybrid", "--profile", "cumcm", "--mode", "competition-assisted"]),
            0,
        )
        config = json.loads((target / "mathmodel.json").read_text(encoding="utf-8"))
        self.assertEqual(config["execution_mode"], "competition_assisted")
        workflow = (target / "CUMCM-WORKFLOW.md").read_text(encoding="utf-8")
        self.assertIn("H1_PROBLEM_UNDERSTANDING", workflow)
        self.assertIn("BLOCKED_HUMAN_INPUT", workflow)
        self.assertFalse((target / "artifacts" / "human-review-ledger.jsonl").exists())

    def test_cli_rejects_invalid_problem_type_cleanly(self):
        self.assertEqual(
            main(["init", str(self.root), "--id", "bad-001", "--title", "Bad", "--type", "unknown"]),
            2,
        )


if __name__ == "__main__":
    unittest.main()
