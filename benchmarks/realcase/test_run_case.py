"""Regression tests for the real-case runner (Phase 10 training loop).

These lock the generalized fixes learned from run 20260901T193906Z-wut-2026-07:
- opencode JSON event parsing must handle {"type":"text",...} shape;
- JSON report extraction must tolerate markdown fences and pick the report object;
- project detection must use mathmodel.json (the actual CLI contract).
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
import unittest.mock
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


class SentinelExistsTests(unittest.TestCase):
    def test_per_question_sentinel_detected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            results = ws / "analysis" / "results"
            results.mkdir(parents=True)
            (results / "Q1.json").write_text("{}", encoding="utf-8")
            self.assertTrue(run_case._sentinel_exists(ws, "q:Q1"))
            self.assertFalse(run_case._sentinel_exists(ws, "q:Q2"))

    def test_per_question_sentinel_requires_id(self):
        self.assertFalse(run_case._sentinel_exists(Path("."), "q:"))

    def test_plain_stage_sentinel_detected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            (ws / "analysis").mkdir()
            (ws / "analysis" / "results.json").write_text("{}", encoding="utf-8")
            self.assertTrue(run_case._sentinel_exists(ws, "experiments"))
            self.assertFalse(run_case._sentinel_exists(ws, "frame"))


class StageSolveDeliveryTests(unittest.TestCase):
    """stage_solve must deliver end-to-end instead of aborting at the first
    failed stage, and must recognize per-question sentinels (observed waste:
    two 0-byte retry sessions for a question whose result file already existed,
    then paper/complete skipped entirely -> untouched template paper judged)."""

    SENTINELS = {
        "frame": "artifacts/problem-map.json",
        "model": "artifacts/model-registry.json",
        "experiments": "analysis/results.json",
        "paper": "paper/main.tex",
        "complete": run_case.SOLVER_COMPLETE_MARKER,
    }

    def _run_stage_solve(self, *, fail_stages: set[str], precreate_map: bool):
        calls: list[tuple[str, str]] = []

        def stage_from_log(log_path: Path) -> str:
            name = log_path.name[len("solver-"):-len(".json")]
            base = name.split("-retry")[0].replace("_", ":")
            return base

        def fake_run_opencode(agent, cwd, prompt, log_path, timeout, fmt="json", session_id=None):
            stage = stage_from_log(log_path)
            calls.append((stage, prompt))
            if stage not in fail_stages:
                if stage.startswith("q:"):
                    sentinel = cwd / "analysis" / "results" / f"{stage[2:]}.json"
                else:
                    sentinel = cwd / self.SENTINELS[stage]
                sentinel.parent.mkdir(parents=True, exist_ok=True)
                sentinel.write_text("{}", encoding="utf-8")
            return 0, json.dumps({"type": "text", "sessionID": "ses_x",
                                  "part": {"type": "text", "text": "ok"}})

        ws = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, ws, ignore_errors=True)
        (ws / "solver").mkdir()
        (ws / "logs").mkdir()
        solver_ws = ws / "solver"
        if precreate_map:
            (solver_ws / "artifacts").mkdir()
            (solver_ws / "artifacts" / "problem-map.json").write_text(
                json.dumps({"questions": [{"id": "Q1"}, {"id": "Q2"}]}), encoding="utf-8")
            (solver_ws / "artifacts" / "model-registry.json").write_text("{}", encoding="utf-8")
        with unittest.mock.patch.object(run_case, "run_opencode", fake_run_opencode):
            result = run_case.stage_solve(ws, {"case_id": "t"}, timeout_s=1500)
        return result, calls

    def test_failed_question_does_not_abort_delivery(self):
        result, calls = self._run_stage_solve(fail_stages={"q:Q2"}, precreate_map=True)
        ran = [stage for stage, _ in calls]
        # paper and complete must still run after the q:Q2 failure
        self.assertIn("paper", ran)
        self.assertIn("complete", ran)
        # q:Q2 failed: one initial session + max_continues retries, no more
        self.assertEqual(ran.count("q:Q2"), 3)
        # delivery flavor only appears after a failure, and names the failed stage
        prompts = dict(calls)
        self.assertIn("DELIVERY PASS", prompts["paper"])
        self.assertIn("q:Q2", prompts["paper"])
        self.assertNotIn("DELIVERY PASS", prompts["q:Q1"])
        self.assertFalse(result.ok)
        self.assertIn("failed=q:Q2", result.detail)
        self.assertIn("stages_done=3/4", result.detail)

    def test_full_expanded_pipeline_counts_as_ok(self):
        result, calls = self._run_stage_solve(fail_stages=set(), precreate_map=True)
        self.assertTrue(result.ok)
        self.assertIn("stages_done=4/4", result.detail)
        self.assertIn("failed=none", result.detail)
        self.assertNotIn("DELIVERY PASS", dict(calls)["paper"])

    def test_frame_failure_still_runs_remaining_stages(self):
        result, calls = self._run_stage_solve(fail_stages={"frame"}, precreate_map=False)
        ran = [stage for stage, _ in calls]
        self.assertIn("model", ran)
        self.assertIn("complete", ran)
        self.assertFalse(result.ok)
        self.assertIn("failed=frame", result.detail)
        # after model succeeds, later stages deliver with the frame failure named
        prompts = dict(calls)
        self.assertIn("DELIVERY PASS", prompts["paper"])
        self.assertIn("frame", prompts["paper"])


if __name__ == "__main__":
    unittest.main()
