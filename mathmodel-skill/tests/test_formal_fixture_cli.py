import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class FormalFixtureCliTests(unittest.TestCase):
    def test_submission_fixture_passes_g9_provenance_and_hash_recomputation(self):
        root = Path(__file__).resolve().parents[2]
        command = [
            sys.executable,
            str(root / "mathmodel-skill" / "scripts" / "mathmodel.py"),
            "submission",
            str(root / "benchmarks" / "cases" / "formal-submission-fixture"),
            "--json",
        ]
        result = subprocess.run(command, cwd=root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["release_status"], "PASS")
        checks = {item["rule"]: item["status"] for item in report["checks"]}
        self.assertEqual(checks["G9-PROVENANCE-001"], "PASS")
        self.assertEqual(checks["G9-HASH-001"], "PASS")

    def test_audit_cli_consumes_max_extension_and_blocks_missing_records(self):
        root = Path(__file__).resolve().parents[2]
        source = root / "benchmarks" / "cases" / "formal-submission-fixture"
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "formal-max"
            shutil.copytree(source, project)
            command = [
                sys.executable,
                str(root / "mathmodel-skill" / "scripts" / "mathmodel.py"),
                "audit",
                str(project),
                "--mode",
                "competition-max",
                "--json",
            ]
            result = subprocess.run(command, cwd=root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["max_rigor"]["status"], "FAIL")
            max_gate = next(item for item in report["page_gates"] if item["rule"] == "G8-MAX-EXTENSIONS-001")
            self.assertEqual(max_gate["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
