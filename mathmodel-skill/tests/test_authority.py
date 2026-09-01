import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mmcore.authority import (
    accept_external_status,
    load_json,
    resolve_conflict,
    validate_registry,
    validate_schema_version,
)


class AuthorityTests(unittest.TestCase):
    def test_supported_schema_version_is_accepted(self):
        self.assertEqual(validate_schema_version({"schema_version": 1}), "PASS")

    def test_unknown_schema_version_fails_closed(self):
        self.assertEqual(validate_schema_version({"schema_version": 2}), "FAIL")

    def test_unresolved_conflict_is_unassessed(self):
        result = resolve_conflict({"status": "OPEN", "options": ["A", "B"]})
        self.assertEqual(result["status"], "UNASSESSED")

    def test_resolved_conflict_requires_policy_and_human_decision(self):
        self.assertEqual(resolve_conflict({"status": "RESOLVED", "resolution": "A"})["status"], "UNASSESSED")
        result = resolve_conflict({"status": "RESOLVED", "resolution": "A", "policy_id": "P1", "human_decision": "approved"})
        self.assertEqual(result["status"], "PASS")

    def test_registry_shape_is_checked_after_schema_version(self):
        self.assertEqual(validate_registry({"schema_version": 1, "capabilities": "bad"}, "capability"), "FAIL")
        self.assertEqual(validate_registry({"schema_version": 1, "capabilities": [{"id": "x", "name": "solver", "status": "EXPERIMENTAL"}]}, "capability"), "PASS")
        self.assertEqual(validate_registry({"schema_version": 1, "capabilities": [{"id": "x", "name": "solver", "status": "BOGUS"}]}, "capability"), "FAIL")

    def test_conflict_authority_fields_must_be_nonempty_strings(self):
        conflict = {"status": "RESOLVED", "resolution": "A", "policy_id": ["P1"], "human_decision": "approved"}
        self.assertEqual(resolve_conflict(conflict)["status"], "UNASSESSED")

    def test_external_release_pass_is_rejected_as_authority(self):
        self.assertEqual(accept_external_status("RELEASE=PASS"), "REJECTED")
        self.assertEqual(accept_external_status("EXPERIMENTAL"), "ADVISORY")

    def test_invalid_json_load_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text("{", encoding="utf-8")
            record = load_json(path)
            self.assertEqual(record["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
