import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mmcore.schema import migrate_artifacts, normalize_artifact


class SchemaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "artifacts").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_v1_normalizes_in_memory_without_mutating_source(self):
        source = {"schema_version": 1, "items": []}
        normalized = normalize_artifact(source)
        self.assertEqual(normalized["schema_version"], 2)
        self.assertEqual(source["schema_version"], 1)

    def test_unknown_schema_does_not_normalize(self):
        self.assertIsNone(normalize_artifact({"schema_version": 99}))

    def test_migrate_upgrades_only_v1_json_artifacts(self):
        old = self.root / "artifacts/old.json"
        old.write_text(json.dumps({"schema_version": 1, "items": []}), encoding="utf-8")
        current = self.root / "artifacts/current.json"
        current.write_text(json.dumps({"schema_version": 2, "items": []}), encoding="utf-8")
        report = migrate_artifacts(self.root)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(json.loads(old.read_text(encoding="utf-8"))["schema_version"], 2)
        self.assertEqual(json.loads(current.read_text(encoding="utf-8"))["schema_version"], 2)

    def test_dry_run_does_not_mutate_artifact(self):
        path = self.root / "artifacts/old.json"
        path.write_text(json.dumps({"schema_version": 1}), encoding="utf-8")
        report = migrate_artifacts(self.root, dry_run=True)
        self.assertEqual(report["migrated"], ["artifacts/old.json"])
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["schema_version"], 1)


if __name__ == "__main__":
    unittest.main()
