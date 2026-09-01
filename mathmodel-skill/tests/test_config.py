import json
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

from mmcore.config import ConfigError, load_config, resolve_project_path
import mathmodel
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
        self.assertEqual(cfg["schema_version"], 2)

    def test_load_config_accepts_native_v2_contract(self):
        cfg = valid_config()
        cfg["schema_version"] = 2
        write_json(self.root / "mathmodel.json", cfg)
        self.assertEqual(load_config(self.root)["schema_version"], 2)

    def test_load_config_validates_optional_benchmark_contract(self):
        cfg = valid_config()
        cfg["benchmark"] = {
            "baseline_command": ["python", "baseline.py"],
            "candidate_command": ["python", "candidate.py"],
            "repeats": 3,
            "timeout_seconds": 120,
        }
        write_json(self.root / "mathmodel.json", cfg)
        self.assertEqual(load_config(self.root)["benchmark"]["repeats"], 3)

    def test_load_config_rejects_invalid_benchmark_contract(self):
        for benchmark in (
            {"baseline_command": [], "candidate_command": ["python", "candidate.py"]},
            {"baseline_command": ["python", "baseline.py"], "candidate_command": ["python", "candidate.py"], "repeats": 0},
            {"baseline_command": ["python", "baseline.py"], "candidate_command": ["python", "candidate.py"], "timeout_seconds": 0},
        ):
            with self.subTest(benchmark=benchmark):
                cfg = valid_config()
                cfg["benchmark"] = benchmark
                write_json(self.root / "mathmodel.json", cfg)
                with self.assertRaises(ConfigError):
                    load_config(self.root)

    def test_load_config_accepts_classification_and_statistics_profiles(self):
        for problem_type in ("classification", "statistics"):
            with self.subTest(problem_type=problem_type):
                cfg = valid_config()
                cfg["problem_type"] = problem_type
                write_json(self.root / "mathmodel.json", cfg)
                self.assertEqual(load_config(self.root)["problem_type"], problem_type)

    def test_load_config_rejects_unknown_schema_version(self):
        cfg = valid_config()
        cfg["schema_version"] = 999
        write_json(self.root / "mathmodel.json", cfg)
        with self.assertRaises(ConfigError):
            load_config(self.root)

    def test_load_config_rejects_non_integer_schema_version(self):
        cfg = valid_config()
        cfg["schema_version"] = []
        write_json(self.root / "mathmodel.json", cfg)
        with self.assertRaises(ConfigError):
            load_config(self.root)

    def test_rejects_path_escape(self):
        with self.assertRaises(ConfigError):
            resolve_project_path(self.root, "../outside.txt")

    def test_rejects_appendix_ratio_above_one(self):
        cfg = valid_config()
        cfg["quality"]["max_appendix_body_ratio"] = 1.1
        write_json(self.root / "mathmodel.json", cfg)
        with self.assertRaises(ConfigError):
            load_config(self.root)

    def test_rejects_unknown_execution_mode(self):
        cfg = valid_config()
        cfg["execution_mode"] = "invented_mode"
        write_json(self.root / "mathmodel.json", cfg)
        with self.assertRaises(ConfigError):
            load_config(self.root)

    def test_accepts_supported_rigor_modes(self):
        for rigor in ("fast", "standard", "max"):
            cfg = valid_config()
            cfg["rigor"] = rigor
            write_json(self.root / "mathmodel.json", cfg)
            self.assertEqual(load_config(self.root)["rigor"], rigor)

    def test_rejects_unknown_rigor(self):
        cfg = valid_config()
        cfg["rigor"] = "unbounded"
        write_json(self.root / "mathmodel.json", cfg)
        with self.assertRaises(ConfigError):
            load_config(self.root)

    def test_rejects_non_string_rigor(self):
        cfg = valid_config()
        cfg["rigor"] = []
        write_json(self.root / "mathmodel.json", cfg)
        with self.assertRaises(ConfigError):
            load_config(self.root)

    def test_main_help_returns_zero(self):
        self.assertEqual(main(["--help"]), 0)

    def test_run_command_routes_to_orchestrator(self):
        write_json(self.root / "mathmodel.json", valid_config())
        output = StringIO()
        with patch("mathmodel.run_pipeline", return_value={"status": "PASS"}) as orchestrator, redirect_stdout(output):
            self.assertEqual(main(["run", str(self.root), "--json"]), 0)
        orchestrator.assert_called_once()
        self.assertEqual(json.loads(output.getvalue())["status"], "PASS")

    def test_benchmark_command_routes_to_harness_and_writes_report(self):
        config = valid_config()
        config["benchmark"] = {
            "baseline_command": ["python", "baseline.py"],
            "candidate_command": ["python", "candidate.py"],
            "repeats": 2,
        }
        write_json(self.root / "mathmodel.json", config)
        output = StringIO()
        report = {"status": "PASS", "promotion": {"status": "OPTIONAL"}}
        with patch("mathmodel.load_case_registry", return_value={"schema_version": 1, "cases": []}), patch("mathmodel.run_configured_benchmark", return_value=report) as benchmark, patch("mathmodel.write_benchmark_report", return_value=str(self.root / "report.json")), redirect_stdout(output):
            self.assertEqual(main(["benchmark", str(self.root), "--json"]), 0)
        self.assertEqual(json.loads(output.getvalue())["report_path"], str(self.root / "report.json"))
        self.assertEqual(benchmark.call_args.kwargs["repeats"], 2)

    def test_submission_command_routes_to_g9_evaluator(self):
        write_json(self.root / "mathmodel.json", valid_config())
        output = StringIO()
        with patch("mathmodel.evaluate_submission", return_value={"status": "NOT_APPLICABLE"}) as evaluator, redirect_stdout(output):
            self.assertEqual(main(["submission", str(self.root), "--json"]), 0)
        evaluator.assert_called_once()
        self.assertEqual(json.loads(output.getvalue())["status"], "NOT_APPLICABLE")

    def test_stage_commands_reuse_read_only_evaluators(self):
        write_json(self.root / "mathmodel.json", valid_config())
        for command in ("frame", "screen", "select", "validate", "freeze", "review", "signoff", "compliance"):
            output = StringIO()
            with redirect_stdout(output):
                exit_code = main([command, str(self.root), "--json"])
            payload = json.loads(output.getvalue())
            self.assertEqual(payload["stage"], command)
            self.assertIn(payload["status"], {"PASS", "FAIL", "PENDING"}, payload)
            self.assertIn(exit_code, {0, 1})

    def test_migrate_command_supports_dry_run_and_explicit_upgrade(self):
        write_json(self.root / "mathmodel.json", valid_config())
        (self.root / "artifacts").mkdir()
        artifact = self.root / "artifacts/example.json"
        artifact.write_text(json.dumps({"schema_version": 1, "items": []}), encoding="utf-8")
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["migrate", str(self.root), "--dry-run", "--json"]), 0)
        self.assertEqual(json.loads(artifact.read_text(encoding="utf-8"))["schema_version"], 1)
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["migrate", str(self.root), "--json"]), 0)
        self.assertEqual(json.loads(artifact.read_text(encoding="utf-8"))["schema_version"], 2)

    def test_authority_command_reports_local_constitution(self):
        (self.root / "CONSTITUTION.md").write_text("local authority", encoding="utf-8")
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["authority", str(self.root), "--json"]), 0)
        report = json.loads(output.getvalue())
        self.assertEqual(report["constitution"], "PASS")
        self.assertEqual(report["external_authority"], "REJECTED")

    def test_authority_command_blocks_malformed_registry(self):
        (self.root / "CONSTITUTION.md").write_text("local authority", encoding="utf-8")
        artifacts = self.root / "artifacts"
        artifacts.mkdir()
        (artifacts / "capability-registry.json").write_text(json.dumps({"schema_version": 1, "capabilities": "bad"}), encoding="utf-8")
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["authority", str(self.root), "--json"]), 1)
        report = json.loads(output.getvalue())
        self.assertEqual(report["registries"]["capability_registry"], "FAIL")

    def test_run_cli_accepts_cumcm_profile_and_mode_without_rewriting_config(self):
        config = valid_config()
        write_json(self.root / "mathmodel.json", config)
        output = StringIO()
        with redirect_stdout(output):
            exit_code = main([
                "run", str(self.root), "--profile", "cumcm", "--mode", "competition-max", "--json",
            ])
        self.assertEqual(exit_code, 1)
        report = json.loads(output.getvalue())
        self.assertEqual(report["status"], "BLOCKED_HUMAN_INPUT")
        self.assertEqual(report["blocked_stage"], "build")
        self.assertEqual(json.loads((self.root / "mathmodel.json").read_text(encoding="utf-8")), config)


if __name__ == "__main__":
    unittest.main()
