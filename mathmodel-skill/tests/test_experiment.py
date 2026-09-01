import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mmcore.experiment import evaluate_experiment_provenance


class ExperimentProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "artifacts").mkdir()
        (self.root / "analysis").mkdir()
        (self.root / "data").mkdir()
        (self.root / "analysis/model.py").write_text("print('model')", encoding="utf-8")
        (self.root / "data/input.csv").write_text("x,y\n1,2\n", encoding="utf-8")
        (self.root / "analysis/metrics.json").write_text('{"rmse": 1}', encoding="utf-8")
        (self.root / "mathmodel.json").write_text('{"schema_version":2}', encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def digest(self, relative):
        return hashlib.sha256((self.root / relative).read_bytes()).hexdigest()

    def valid(self):
        return {"schema_version": 1, "generated_by": "local_runner", "experiments": [{
            "id": "EXP-001", "run_id": "run-001", "question_id": "Q1", "model_id": "M1",
            "code_hashes": {"analysis/model.py": self.digest("analysis/model.py")},
            "input_hashes": {"data/input.csv": self.digest("data/input.csv")},
            "config_hash": self.digest("mathmodel.json"), "seed": 7,
            "environment": {"python_version": "3.13", "platform": "Windows"},
            "started_at": "2026-09-01T00:00:00+00:00", "ended_at": "2026-09-01T00:01:00+00:00",
            "metrics": ["analysis/metrics.json"], "figures": [], "result_artifacts": ["analysis/metrics.json"],
        }]}

    def write(self, value):
        (self.root / "artifacts/experiment-registry.json").write_text(json.dumps(value), encoding="utf-8")

    def test_valid_provenance_passes(self):
        self.write(self.valid())
        self.assertEqual(evaluate_experiment_provenance(self.root)["status"], "PASS")

    def test_missing_registry_fails(self):
        report = evaluate_experiment_provenance(self.root)
        self.assertEqual(report["status"], "FAIL")

    def test_tampered_code_hash_fails(self):
        data = self.valid()
        data["experiments"][0]["code_hashes"]["analysis/model.py"] = "0" * 64
        self.write(data)
        report = evaluate_experiment_provenance(self.root)
        self.assertTrue(any(item["rule"] == "G4-EXPERIMENT-HASH-001" and item["status"] == "FAIL" for item in report["checks"]))


if __name__ == "__main__":
    unittest.main()
