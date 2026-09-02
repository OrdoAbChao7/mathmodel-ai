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


class StagedSolveTests(unittest.TestCase):
    def test_plan_stages_skips_completed_and_orders_rest(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            from pathlib import Path
            ws = Path(td)
            (ws / "artifacts").mkdir()
            (ws / "artifacts" / "problem-map.json").write_text("{}", encoding="utf-8")
            plan = run_case.plan_stages(ws)
            names = [name for name, _p, _s in plan]
            self.assertEqual(names, ["model", "experiments", "paper", "complete"])
            # Every pending stage has a unique sentinel that does not exist yet.
            sentinels = [s for _n, _p, s in plan]
            self.assertEqual(len(set(sentinels)), len(sentinels))
            self.assertTrue(all(not s.exists() for s in sentinels))

    def test_instruction_for_unknown_stage_returns_empty(self):
        self.assertEqual(run_case.instruction_for("nonexistent"), "")

    def test_plan_stages_expands_experiments_per_question(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            from pathlib import Path
            ws = Path(td)
            (ws / "artifacts").mkdir()
            (ws / "analysis").mkdir()
            (ws / "artifacts" / "problem-map.json").write_text(
                json.dumps({"questions": [{"id": "Q1"}, {"id": "Q2"}]}), encoding="utf-8")
            (ws / "artifacts" / "model-registry.json").write_text("{}", encoding="utf-8")
            plan = run_case.plan_stages(ws)
            names = [name for name, _p, _s in plan]
            # problem-map and model-registry exist -> frame/model skipped;
            # experiments expanded to q:Q1,q:Q2; paper/complete still pending.
            self.assertEqual(names, ["q:Q1", "q:Q2", "paper", "complete"])

    def test_per_question_expansion_requires_problem_map(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            from pathlib import Path
            ws = Path(td)
            (ws / "artifacts").mkdir()
            (ws / "artifacts" / "model-registry.json").write_text("{}", encoding="utf-8")
            plan = run_case.plan_stages(ws)
            names = [name for name, _p, _s in plan]
            self.assertNotIn("q:Q1", names)
            self.assertIn("experiments", names)

    def test_log_filename_is_cross_platform(self):
        name = run_case.log_filename("solver", "q:Q1/sub")
        self.assertEqual(name, "solver-q_Q1_sub.json")
        self.assertNotIn(":", name)

    def test_stages_cover_expected_pipeline(self):
        names = [name for name, _s, _i in run_case.SOLVE_STAGES]
        self.assertEqual(names, ["frame", "model", "experiments", "paper", "complete"])
        # The final sentinel is the completion marker used by audit/judge replay.
        self.assertEqual(run_case.SOLVE_STAGES[-1][1], run_case.SOLVER_COMPLETE_MARKER)


if __name__ == "__main__":
    unittest.main()
