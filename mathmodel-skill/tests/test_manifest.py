import json
import hashlib
import os
import sys
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mathmodel import main
from mmcore.manifest import (
    inventory_project,
    new_run,
    recognized_path_decision,
    sha256_file,
    update_stage,
)


def valid_config():
    return {
        "schema_version": 1,
        "project_id": "training-001",
        "title": "待求解题目",
        "contest": "CUMCM",
        "problem_type": "optimization",
        "inputs": {
            "statements": ["problem/problem.pdf", "problem/missing.pdf"],
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


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self._tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tempdir.name)

    def tearDown(self):
        self._tempdir.cleanup()

    def test_sha256_is_stable(self):
        path = self.root / "data.txt"
        path.write_bytes(b"abc")
        self.assertEqual(
            sha256_file(path),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        )

    def test_inventory_uses_relative_posix_paths_and_warns_for_missing_inputs(self):
        (self.root / "problem").mkdir()
        (self.root / "problem" / "problem.pdf").write_bytes(b"statement")
        (self.root / "data" / "raw").mkdir(parents=True)
        (self.root / "data" / "raw" / "attachment.xlsx").write_bytes(b"attachment")
        (self.root / "solve.py").write_text("print('ok')", encoding="utf-8")

        inventory = inventory_project(self.root, valid_config())

        paths = {item["path"]: item for item in inventory["files"]}
        self.assertIn("problem/problem.pdf", paths)
        self.assertIn("data/raw/attachment.xlsx", paths)
        self.assertIn("solve.py", paths)
        self.assertEqual(paths["problem/problem.pdf"]["type"], "statement")
        self.assertEqual(paths["problem/missing.pdf"]["exists"], False)
        self.assertEqual(paths["problem/missing.pdf"]["status"], "WARN")
        self.assertIn("sha256", paths["data/raw/attachment.xlsx"])

    def test_run_manifest_records_input_hash_and_stages(self):
        inventory = {"files": [{"path": "data.txt", "sha256": "abc", "exists": True}]}
        manifest_path, manifest = new_run(self.root, "inspect", valid_config(), inventory)
        update_stage(manifest_path, "inventory", "RUNNING", output="artifacts/data-audit.json", warning="first warning")
        update_stage(manifest_path, "inventory", "SUCCESS", output="artifacts/second.json", warning="second warning", error="evidence note")
        saved = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(saved["stages"]["inventory"]["status"], "SUCCESS")
        self.assertIn("input_hashes", saved)
        self.assertEqual(saved["stages"]["inventory"]["outputs"], ["artifacts/data-audit.json", "artifacts/second.json"])
        self.assertEqual(saved["stages"]["inventory"]["warnings"], ["first warning", "second warning"])
        self.assertEqual(saved["stages"]["inventory"]["errors"], ["evidence note"])
        self.assertEqual(set(saved["stages"]["inventory"]), {
            "status", "started_at", "finished_at", "exit_code", "outputs", "warnings", "errors", "output_inventory"
        })
        self.assertEqual(saved["stages"]["inventory"]["output_inventory"], [])

    def test_new_run_creates_distinct_append_only_run_directories(self):
        inventory = {"files": []}
        first_path, _ = new_run(self.root, "inspect", valid_config(), inventory)
        first_before = first_path.read_text(encoding="utf-8")
        second_path, _ = new_run(self.root, "inspect", valid_config(), inventory)
        self.assertNotEqual(first_path.parent, second_path.parent)
        self.assertTrue(first_path.exists())
        self.assertTrue(second_path.exists())
        self.assertEqual(first_path.read_text(encoding="utf-8"), first_before)

    def test_run_id_is_utc_timestamp_plus_corresponding_config_hash(self):
        inventory = {"files": [{"path": "data.txt", "sha256": "abc", "exists": True}]}
        manifest_path, manifest = new_run(self.root, "inspect", valid_config(), inventory)
        self.assertRegex(manifest["run_id"], r"^\d{8}T\d{6}Z-[0-9a-f]{12}$")
        run_timestamp, run_hash = manifest["run_id"].split("-")
        created_at = datetime.fromisoformat(manifest["created_at"])
        self.assertEqual(created_at.strftime("%Y%m%dT%H%M%SZ"), run_timestamp)
        expected = hashlib.sha256(json.dumps({"config": valid_config(), "input_hashes": {"data.txt": "abc"}}, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]
        self.assertEqual(run_hash, expected)
        self.assertEqual(manifest_path.parent.name, manifest["run_id"])

    def test_manifest_records_complete_provenance_and_inventory_fields(self):
        cfg = valid_config()
        cfg["inputs"]["statements"] = ["problem/../problem/problem.pdf", "problem/missing.pdf"]
        (self.root / "mathmodel.json").write_text(json.dumps(cfg), encoding="utf-8")
        (self.root / "problem").mkdir()
        statement = self.root / "problem" / "problem.pdf"
        statement.write_bytes(b"statement")
        (self.root / "data" / "raw").mkdir(parents=True)
        attachment = self.root / "data" / "raw" / "attachment.xlsx"
        attachment.write_bytes(b"attachment")
        (self.root / "paper").mkdir()
        (self.root / "paper" / "main.tex").write_text("paper", encoding="utf-8")
        inventory = inventory_project(self.root, cfg)
        manifest_path, manifest = new_run(self.root, "inspect", cfg, inventory)
        files = {item["path"]: item for item in inventory["files"]}
        self.assertEqual(set(files), {"data/raw/attachment.xlsx", "mathmodel.json", "paper/main.tex", "problem/missing.pdf", "problem/problem.pdf"})
        for path, item in files.items():
            self.assertIn("type", item)
            self.assertIn("size", item)
            self.assertIn("modified_at", item)
            self.assertIn("exists", item)
            self.assertIn("status", item)
            if item["exists"]:
                self.assertEqual(item["sha256"], hashlib.sha256((self.root / Path(path)).read_bytes()).hexdigest())
        self.assertFalse(files["problem/missing.pdf"]["exists"])
        self.assertEqual(files["problem/missing.pdf"]["status"], "WARN")
        self.assertEqual(manifest["command"], "inspect")
        self.assertEqual(manifest["config"], cfg)
        self.assertTrue(manifest["python_version"])
        self.assertTrue(manifest["python_executable"])
        self.assertEqual(manifest["input_hashes"], {path: item["sha256"] for path, item in files.items() if item["exists"]})
        self.assertTrue(manifest_path.exists())

    def test_inspect_writes_audit_and_manifest_and_prints_json(self):
        (self.root / "mathmodel.json").write_text(json.dumps(valid_config()), encoding="utf-8")
        (self.root / "problem").mkdir()
        (self.root / "problem" / "problem.pdf").write_bytes(b"statement")
        (self.root / "data" / "raw").mkdir(parents=True)
        (self.root / "data" / "raw" / "attachment.xlsx").write_bytes(b"attachment")
        (self.root / "paper").mkdir()
        (self.root / "paper" / "main.tex").write_text("paper", encoding="utf-8")

        from contextlib import redirect_stdout
        from io import StringIO
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["inspect", str(self.root), "--json"]), 0)
        result = json.loads(output.getvalue())
        audit_path = self.root / "artifacts" / "data-audit.json"
        self.assertEqual(Path(result["audit"]), audit_path)
        self.assertEqual(result["status"], "WARN")
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        self.assertEqual(audit["project"], str(self.root.resolve()))
        self.assertIn("files", audit)
        self.assertIn("problem/missing.pdf", {item["path"] for item in audit["files"]})
        manifests = list((self.root / ".mathmodel" / "runs").glob("*/manifest.json"))
        self.assertEqual(len(manifests), 1)
        saved = json.loads(manifests[0].read_text(encoding="utf-8"))
        self.assertEqual(Path(result["manifest"]), manifests[0])
        self.assertEqual(saved["command"], "inspect")
        self.assertEqual(saved["inventory"], audit)
        self.assertEqual(saved["stages"]["inventory"]["outputs"], ["artifacts/data-audit.json"])

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks are unavailable on this platform")
    def test_out_of_root_recognized_symlink_is_warned_or_skipped(self):
        outside = Path(tempfile.mkdtemp()) / "outside.py"
        outside.write_text("print('outside')", encoding="utf-8")
        linked = self.root / "linked.py"
        try:
            linked.symlink_to(outside)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink creation unavailable: {exc}")
        inventory = inventory_project(self.root, {"inputs": {}, "paper": {}})
        self.assertNotIn("linked.py", {item["path"] for item in inventory["files"]})
        self.assertTrue(inventory["warnings"])

    def test_out_of_root_recognized_candidate_is_warned_and_skipped_without_symlink(self):
        outside = self.root.parent / "outside.py"
        relative, warning = recognized_path_decision(self.root, outside)
        self.assertIsNone(relative)
        self.assertIn("out-of-root", warning)
        with patch("mmcore.manifest._recognized_paths", return_value={outside}):
            inventory = inventory_project(self.root, {"inputs": {}, "paper": {}})
        self.assertNotIn("outside.py", {item["path"] for item in inventory["files"]})
        self.assertEqual(len(inventory["warnings"]), 1)
        self.assertIn("out-of-root", inventory["warnings"][0])


if __name__ == "__main__":
    unittest.main()
