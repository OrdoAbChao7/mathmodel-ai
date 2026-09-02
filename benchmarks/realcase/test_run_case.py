"""Regression tests for the real-case runner (Phase 10 training loop).

These lock the generalized fixes learned from run 20260901T193906Z-wut-2026-07:
- opencode JSON event parsing must handle {"type":"text",...} shape;
- JSON report extraction must tolerate markdown fences and pick the report object;
- project detection must use mathmodel.json (the actual CLI contract).
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_case  # noqa: E402


class ParseAgentTextTests(unittest.TestCase):
    def test_flat_text_events(self):
        log = "\n".join([
            json.dumps({"type": "text", "part": {"type": "text", "text": "hello"}}),
            json.dumps({"type": "step_finish", "part": {"reason": "stop"}}),
            json.dumps({"type": "text", "part": {"type": "text", "text": "world"}}),
        ])
        self.assertEqual(run_case.parse_agent_text(log), "hello\nworld")

    def test_message_part_updated_shape(self):
        log = json.dumps({"type": "message.part.updated",
                          "part": {"type": "text", "text": "via-updated"}})
        self.assertEqual(run_case.parse_agent_text(log), "via-updated")

    def test_ignores_non_json_lines_and_empty_text(self):
        log = "\n".join(["not json", json.dumps({"type": "text", "part": {"type": "text", "text": "  "}})])
        self.assertEqual(run_case.parse_agent_text(log), "")


class ExtractJsonTests(unittest.TestCase):
    def test_fenced_json_report(self):
        text = '```json\n{"scores": {"a": 1}, "overall": 0.5}\n```'
        self.assertEqual(run_case._extract_json(text)["overall"], 0.5)

    def test_picks_scores_object_from_multiple(self):
        text = '{"note": "first"} then {"scores": {"x": 2}, "overall": 1.0}'
        self.assertEqual(run_case._extract_json(text)["overall"], 1.0)

    def test_plain_json(self):
        self.assertIsNone(run_case._extract_json("no json here"))


class FindProjectDirTests(unittest.TestCase):
    def test_detects_mathmodel_json_at_root(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "mathmodel.json").write_text("{}", encoding="utf-8")
            self.assertEqual(run_case.find_project_dir(root), root)

    def test_detects_mathmodel_json_one_level_down(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            child = root / "project"
            child.mkdir()
            (child / "mathmodel.json").write_text("{}", encoding="utf-8")
            self.assertEqual(run_case.find_project_dir(root), child)

    def test_returns_none_when_absent(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertIsNone(run_case.find_project_dir(Path(td)))


class LastSessionIdTests(unittest.TestCase):
    def test_returns_last_session_id(self):
        log = "\n".join([
            json.dumps({"type": "text", "sessionID": "ses_a", "part": {"sessionID": "ses_a"}}),
            json.dumps({"type": "step_finish", "sessionID": "ses_b", "part": {"sessionID": "ses_b"}}),
        ])
        self.assertEqual(run_case.last_session_id(log), "ses_b")

    def test_none_when_absent(self):
        self.assertIsNone(run_case.last_session_id("garbage"))


if __name__ == "__main__":
    unittest.main()
