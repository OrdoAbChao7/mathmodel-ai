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

from mmcore.config import ConfigError, load_config, resolve_project_path
from mathmodel import main


def valid_config():
    return {
        "schema_version": 1,
        "project_id": "training-001",
        "title": "待求解题目",
        "contest": "CUMCM",
        "problem_type": "optimization",
        "inputs": {
            "statements": ["problem/problem.pdf"],
            "attachments": ["data/raw/attachment.xlsx"],
        },
        "commands": {"analyze": ["python", "analysis/run.py"]},
        "paper": {"main": "paper/main.tex", "engine": "xelatex", "jobname": "paper"},
        "quality": {
            "target_total_pages": [32, 40],
            "target_body_pages": [26, 34],
            "max_appendix_body_ratio": 0.25,
            "minimum_score": 85,
            "minimum_figures": 8,
            "required_figure_roles": ["data", "method", "result", "validation"],
        },
    }


def write_json(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self._tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tempdir.name)

    def tearDown(self):
        self._tempdir.cleanup()

    def test_load_config_accepts_minimal_valid_contract(self):
        write_json(self.root / "mathmodel.json", valid_config())
        cfg = load_config(self.root)
        self.assertEqual(cfg["problem_type"], "optimization")

    def test_rejects_path_escape(self):
        with self.assertRaises(ConfigError):
            resolve_project_path(self.root, "../outside.txt")

    def test_rejects_appendix_ratio_above_one(self):
        cfg = valid_config()
        cfg["quality"]["max_appendix_body_ratio"] = 1.1
        write_json(self.root / "mathmodel.json", cfg)
        with self.assertRaises(ConfigError):
            load_config(self.root)

    def test_main_help_returns_zero(self):
        self.assertEqual(main(["--help"]), 0)

    def test_authority_command_reports_local_constitution(self):
        (self.root / "CONSTITUTION.md").write_text("local authority", encoding="utf-8")
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["authority", str(self.root), "--json"]), 0)
        report = json.loads(output.getvalue())
        self.assertEqual(report["constitution"], "PASS")
        self.assertEqual(report["external_authority"], "REJECTED")


if __name__ == "__main__":
    unittest.main()
