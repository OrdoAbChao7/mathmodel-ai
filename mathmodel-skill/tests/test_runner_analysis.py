import json
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mathmodel import main
from mmcore.analysis import collect_outputs, run_analysis
from mmcore.runner import run_solver


def valid_config(solver, analysis):
    return {
        "schema_version": 1,
        "project_id": "runner-001",
        "title": "Runner fixture",
        "contest": "CUMCM",
        "problem_type": "optimization",
        "inputs": {"statements": [], "attachments": []},
        "commands": {"solver": solver, "analyze": analysis},
        "paper": {"main": "paper/main.tex", "engine": "xelatex", "jobname": "paper"},
        "quality": {
            "target_total_pages": [1, 2],
            "target_body_pages": [1, 2],
            "max_appendix_body_ratio": 1,
            "minimum_score": 0,
            "minimum_figures": 0,
            "required_figure_roles": [],
        },
    }


class RunnerAnalysisTests(unittest.TestCase):
    def setUp(self):
        self._tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tempdir.name)
        self.run_dir = self.root / ".mathmodel" / "runs" / "run-001"
        self.run_dir.mkdir(parents=True)

    def tearDown(self):
        self._tempdir.cleanup()

    def write_script(self, name, source):
        path = self.root / name
        path.write_text(source, encoding="utf-8")
        return path

    def test_solver_runs_argument_array_in_project_and_records_logs(self):
        self.write_script(
            "solver.py",
            "import os, pathlib, sys\n"
            "assert sys.argv[1] == 'two words'\n"
            "pathlib.Path('solver-cwd.txt').write_text(os.getcwd(), encoding='utf-8')\n"
            "print('solver complete')\n",
        )

        result = run_solver(self.root, [sys.executable, "solver.py", "two words"], self.run_dir)

        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["command"], [sys.executable, "solver.py", "two words"])
        self.assertEqual((self.root / "solver-cwd.txt").read_text(encoding="utf-8"), str(self.root.resolve()))
        self.assertEqual(Path(result["stdout_path"]).read_text(encoding="utf-8"), "solver complete\n")
        self.assertEqual(Path(result["stderr_path"]).read_text(encoding="utf-8"), "")
        self.assertIn("config_sha256", result["reproducibility"])
        self.assertIn("solver.py", result["reproducibility"]["code_hashes"])

    def test_solver_returns_structured_failure_for_missing_command(self):
        result = run_solver(self.root, ["definitely-not-an-installed-solver"], self.run_dir)

        self.assertEqual(result["status"], "FAILED")
        self.assertIsNone(result["exit_code"])
        self.assertTrue(any(error["rule"] == "RUNNER-COMMAND-001" for error in result["errors"]))
        self.assertTrue(Path(result["stderr_path"]).is_file())

    def test_solver_rejects_malformed_and_escaping_commands_without_execution(self):
        malformed = run_solver(self.root, "python solver.py", self.run_dir)
        escaped = run_solver(self.root, [sys.executable, "../outside.py"], self.run_dir)

        self.assertEqual(malformed["status"], "FAILED")
        self.assertTrue(any(error["rule"] == "RUNNER-COMMAND-002" for error in malformed["errors"]))
        self.assertEqual(escaped["status"], "FAILED")
        self.assertTrue(any(error["rule"] == "RUNNER-PATH-001" for error in escaped["errors"]))

    def test_solver_rejects_relative_executable_path_escape_before_execution(self):
        outside = self.root.parent / "outside-executable.py"
        outside.write_text("raise AssertionError('outside executable must not run')\n", encoding="utf-8")
        try:
            result = run_solver(self.root, ["../outside-executable.py"], self.run_dir)
        finally:
            outside.unlink(missing_ok=True)

        self.assertEqual(result["status"], "FAILED")
        self.assertTrue(any(error["rule"] == "RUNNER-PATH-001" for error in result["errors"]))
        self.assertIsNone(result["exit_code"])

    def test_solver_rejects_symlink_resolved_and_option_value_path_escapes(self):
        self.write_script("safe.py", "print('safe')\n")
        outside = self.root.parent / "outside.py"
        outside.write_text("raise AssertionError('outside script must not run')\n", encoding="utf-8")
        linked = self.root / "linked.py"
        try:
            linked.symlink_to(outside)
        except (OSError, NotImplementedError):
            with patch("mmcore.runner._resolve_existing_path", return_value=outside):
                result = run_solver(self.root, [sys.executable, "safe.py", "--config=linked.py"], self.run_dir)
        else:
            result = run_solver(self.root, [sys.executable, "safe.py", "--config=linked.py"], self.run_dir)
        finally:
            outside.unlink(missing_ok=True)

        self.assertEqual(result["status"], "FAILED")
        self.assertTrue(any(error["rule"] == "RUNNER-PATH-001" for error in result["errors"]))
        self.assertNotIn("safe\n", result["stdout"])

    def test_solver_timeout_preserves_captured_diagnostics(self):
        self.write_script("slow.py", "import time\nprint('starting', flush=True)\ntime.sleep(10)\n")

        with patch("mmcore.runner.DEFAULT_TIMEOUT_SECONDS", 0.05):
            result = run_solver(self.root, [sys.executable, "slow.py"], self.run_dir)

        self.assertEqual(result["status"], "FAILED")
        self.assertTrue(result["timed_out"])
        self.assertTrue(any(error["rule"] == "RUNNER-TIMEOUT-001" for error in result["errors"]))
        self.assertIn("starting", Path(result["stdout_path"]).read_text(encoding="utf-8"))

    def test_analysis_collects_hash_addressed_project_contained_outputs(self):
        self.write_script(
            "analysis.py",
            "import os, pathlib\n"
            "out = pathlib.Path(os.environ['MM_RUN_DIR']) / 'outputs'\n"
            "out.mkdir(parents=True, exist_ok=True)\n"
            "(out / 'result.json').write_text('{\\\"value\\\": 7}', encoding='utf-8')\n"
            "print('analysis complete')\n",
        )

        result = run_analysis(self.root, [sys.executable, "analysis.py"], self.run_dir)
        inventory = collect_outputs(self.run_dir)

        self.assertEqual(result["status"], "SUCCESS")
        item = next(entry for entry in inventory["files"] if entry["path"] == "outputs/result.json")
        self.assertEqual(item["size"], len('{"value": 7}'))
        self.assertEqual(len(item["sha256"]), 64)
        self.assertEqual(item["provenance"]["run_id"], "run-001")
        self.assertNotIn("../", "\n".join(entry["path"] for entry in inventory["files"]))

    def test_solver_attaches_complete_inventory_and_generated_outputs(self):
        self.write_script(
            "solver.py",
            "import os\nfrom pathlib import Path\n"
            "Path(os.environ['MM_RUN_DIR'], 'solver-result.json').write_text('{\\\"ok\\\": true}', encoding='utf-8')\n",
        )

        result = run_solver(self.root, [sys.executable, "solver.py"], self.run_dir)

        inventory = result["output_inventory"]
        self.assertEqual(inventory["status"], "SUCCESS")
        self.assertTrue(any(item["path"] == "solver-result.json" and item["kind"] == "generated_output" for item in inventory["generated_files"]))
        self.assertTrue(any(item["path"] == "solver.stdout.log" and item["kind"] == "framework_log" for item in inventory["files"]))

    def test_analysis_failure_retains_stdout_and_stderr(self):
        self.write_script("fail.py", "import sys\nprint('before fail')\nprint('intentional failure', file=sys.stderr)\nsys.exit(7)\n")

        result = run_analysis(self.root, [sys.executable, "fail.py"], self.run_dir)

        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["exit_code"], 7)
        self.assertIn("before fail", result["stdout"])
        self.assertIn("intentional failure", result["stderr"])
        self.assertTrue(Path(result["stdout_path"]).is_file())
        self.assertTrue(Path(result["stderr_path"]).is_file())

    def test_build_runs_solver_then_analysis_and_writes_append_only_evidence(self):
        self.write_script(
            "solver.py",
            "import os\nfrom pathlib import Path\n"
            "Path('order.txt').write_text('solver\\n', encoding='utf-8')\n"
            "Path(os.environ['MM_RUN_DIR'], 'solver-output.json').write_text('{\\\"solver\\\": 1}', encoding='utf-8')\n",
        )
        self.write_script(
            "analysis.py",
            "import os\nfrom pathlib import Path\n"
            "path = Path('order.txt')\n"
            "assert path.read_text(encoding='utf-8') == 'solver\\n'\n"
            "path.write_text('solver\\nanalysis\\n', encoding='utf-8')\n"
            "Path(os.environ['MM_RUN_DIR'], 'analysis-output.json').write_text('{\\\"analysis\\\": 1}', encoding='utf-8')\n",
        )
        (self.root / "paper").mkdir()
        (self.root / "paper" / "main.tex").write_text("paper", encoding="utf-8")
        cfg = valid_config([sys.executable, "solver.py"], [sys.executable, "analysis.py"])
        (self.root / "mathmodel.json").write_text(json.dumps(cfg), encoding="utf-8")
        output = StringIO()
        compile_result = {"status": "FAILED", "pdf": str(self.root / "missing.pdf"), "aux": str(self.root / "missing.aux"), "errors": []}
        with patch("mathmodel.compile_latex", return_value=compile_result), patch("mathmodel.measure_pdf", return_value={"status": "PENDING"}), redirect_stdout(output):
            exit_code = main(["build", str(self.root), "--json"])

        payload = json.loads(output.getvalue())
        manifests = list((self.root / ".mathmodel" / "runs").glob("*/manifest.json"))
        report = json.loads((self.root / "build" / "build-report.json").read_text(encoding="utf-8"))
        self.assertEqual(exit_code, 1)
        self.assertEqual((self.root / "order.txt").read_text(encoding="utf-8"), "solver\nanalysis\n")
        self.assertEqual(len(manifests), 1)
        stages = json.loads(manifests[0].read_text(encoding="utf-8"))["stages"]
        self.assertEqual(stages["solver"]["status"], "SUCCESS")
        self.assertEqual(stages["analysis"]["status"], "SUCCESS")
        solver_generated = next(item for item in stages["solver"]["output_inventory"]["generated_files"] if item["path"] == "solver-output.json")
        analysis_generated = next(item for item in stages["analysis"]["output_inventory"]["generated_files"] if item["path"] == "analysis-output.json")
        for item in (solver_generated, analysis_generated):
            self.assertEqual(len(item["sha256"]), 64)
            self.assertEqual(item["kind"], "generated_output")
            self.assertEqual(item["provenance"]["run_id"], manifests[0].parent.name)
        executions = json.loads(manifests[0].read_text(encoding="utf-8"))["executions"]
        solver_execution = next(entry for entry in executions if entry["stage"] == "solver")
        self.assertTrue(solver_execution["input_hashes"])
        self.assertEqual(solver_execution["config_sha256"], solver_execution["reproducibility"]["config_sha256"])
        self.assertIn("output_inventory", solver_execution)
        self.assertEqual(report["run"]["manifest"], str(manifests[0]))
        self.assertEqual(payload["solver"]["status"], "SUCCESS")
        self.assertEqual(payload["analysis"]["status"], "SUCCESS")

    def test_build_skips_analysis_after_solver_failure(self):
        self.write_script("solver.py", "import sys\nsys.exit(4)\n")
        self.write_script("analysis.py", "from pathlib import Path\nPath('analysis-ran.txt').write_text('no', encoding='utf-8')\n")
        (self.root / "paper").mkdir()
        (self.root / "paper" / "main.tex").write_text("paper", encoding="utf-8")
        cfg = valid_config([sys.executable, "solver.py"], [sys.executable, "analysis.py"])
        (self.root / "mathmodel.json").write_text(json.dumps(cfg), encoding="utf-8")
        output = StringIO()
        compile_result = {"status": "FAILED", "pdf": str(self.root / "missing.pdf"), "aux": str(self.root / "missing.aux"), "errors": []}
        with patch("mathmodel.compile_latex", return_value=compile_result) as compile_mock, patch("mathmodel.measure_pdf", return_value={"status": "PENDING"}), redirect_stdout(output):
            exit_code = main(["build", str(self.root), "--json"])

        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertEqual(payload["solver"]["status"], "FAILED")
        self.assertEqual(payload["analysis"]["status"], "SKIPPED")
        self.assertFalse((self.root / "analysis-ran.txt").exists())
        compile_mock.assert_not_called()
        manifest = next((self.root / ".mathmodel" / "runs").glob("*/manifest.json"))
        stages = json.loads(manifest.read_text(encoding="utf-8"))["stages"]
        for stage in ("compile", "page-metrics", "validate-artifacts", "quality"):
            self.assertEqual(stages[stage]["status"], "SKIPPED")

    def test_build_skips_compilation_after_analysis_failure(self):
        self.write_script("solver.py", "print('solver')\n")
        self.write_script("analysis.py", "import sys\nsys.exit(9)\n")
        (self.root / "paper").mkdir()
        (self.root / "paper" / "main.tex").write_text("paper", encoding="utf-8")
        (self.root / "mathmodel.json").write_text(json.dumps(valid_config([sys.executable, "solver.py"], [sys.executable, "analysis.py"])), encoding="utf-8")
        output = StringIO()
        with patch("mathmodel.compile_latex") as compile_mock, redirect_stdout(output):
            exit_code = main(["build", str(self.root), "--json"])

        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertEqual(payload["analysis"]["status"], "FAILED")
        self.assertEqual(payload["compile"]["status"], "SKIPPED")
        compile_mock.assert_not_called()

    def test_build_reports_malformed_cli_configuration_as_structured_failure(self):
        cfg = valid_config([sys.executable, "solver.py"], [sys.executable, "analysis.py"])
        cfg["commands"]["analyze"] = "python analysis.py"
        (self.root / "mathmodel.json").write_text(json.dumps(cfg), encoding="utf-8")
        output = StringIO()
        with redirect_stdout(output):
            exit_code = main(["build", str(self.root), "--json"])

        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 2)
        self.assertEqual(payload["status"], "FAIL")
        self.assertEqual(payload["errors"][0]["rule"], "BUILD-CONFIG-001")

    def test_run_directories_are_append_only_across_builds(self):
        self.write_script("solver.py", "print('solver')\n")
        self.write_script("analysis.py", "print('analysis')\n")
        (self.root / "paper").mkdir()
        (self.root / "paper" / "main.tex").write_text("paper", encoding="utf-8")
        (self.root / "mathmodel.json").write_text(json.dumps(valid_config([sys.executable, "solver.py"], [sys.executable, "analysis.py"])), encoding="utf-8")
        compile_result = {"status": "FAILED", "pdf": str(self.root / "missing.pdf"), "aux": str(self.root / "missing.aux"), "errors": []}
        with patch("mathmodel.compile_latex", return_value=compile_result), patch("mathmodel.measure_pdf", return_value={"status": "PENDING"}), redirect_stdout(StringIO()):
            main(["build", str(self.root), "--json"])
        first = next((self.root / ".mathmodel" / "runs").glob("*/manifest.json"))
        first_contents = first.read_text(encoding="utf-8")
        time.sleep(0.01)
        with patch("mathmodel.compile_latex", return_value=compile_result), patch("mathmodel.measure_pdf", return_value={"status": "PENDING"}), redirect_stdout(StringIO()):
            main(["build", str(self.root), "--json"])

        manifests = list((self.root / ".mathmodel" / "runs").glob("*/manifest.json"))
        self.assertEqual(len(manifests), 2)
        self.assertEqual(first.read_text(encoding="utf-8"), first_contents)


if __name__ == "__main__":
    unittest.main()
