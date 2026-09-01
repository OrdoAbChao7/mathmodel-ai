import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mmcore.orchestration.time_budget import evaluate_budget, stopping_decision
from mmcore.orchestration.orchestrator import run_pipeline, run_parallel


class OrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.now = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)

    def tearDown(self):
        self.tmp.cleanup()

    def config(self):
        return {"orchestration": {"contest_start": "2026-09-01T08:00:00+00:00", "contest_deadline": "2026-09-01T12:00:00+00:00", "submission_buffer_seconds": 900, "exploration_threshold_seconds": 1800, "max_retries": 2, "milestones": {"problem_lock_deadline": "2026-09-01T09:00:00+00:00", "model_selection_deadline": "2026-09-01T10:30:00+00:00"}}}

    def test_budget_reports_remaining_and_milestones(self):
        report = evaluate_budget(self.config(), self.now)
        self.assertEqual(report["status"], "ACTIVE")
        self.assertEqual(report["remaining_seconds"], 7200)
        self.assertEqual(report["milestones"]["problem_lock_deadline"], "PASSED")

    def test_budget_fails_closed_for_invalid_timeline(self):
        config = self.config()
        config["orchestration"]["contest_deadline"] = "not-a-time"
        report = evaluate_budget(config, self.now)
        self.assertEqual(report["status"], "FAIL")

    def test_stopping_policy_requires_all_evidence(self):
        budget = evaluate_budget(self.config(), self.now)
        evidence = {"selected_beats_baseline": True, "validation_passed": True, "open_critical": 0}
        self.assertEqual(stopping_decision(evidence, budget)["action"], "CONTINUE_MODEL_SEARCH")
        late = evaluate_budget(self.config(), self.now.replace(hour=11, minute=40))
        self.assertEqual(stopping_decision(evidence, late)["action"], "STOP_MODEL_SEARCH")
        evidence["open_critical"] = 1
        self.assertEqual(stopping_decision(evidence, late)["action"], "CONTINUE_MODEL_SEARCH")

    def test_stopping_policy_rejects_boolean_budget_values(self):
        evidence = {"selected_beats_baseline": True, "validation_passed": True, "open_critical": 0}
        budget = {"status": "ACTIVE", "remaining_seconds": True, "exploration_threshold_seconds": True}
        self.assertEqual(stopping_decision(evidence, budget)["action"], "CONTINUE_MODEL_SEARCH")

    def test_pipeline_retries_with_bounded_attempts(self):
        calls = []
        def runner(stage):
            calls.append(stage)
            return {"status": "FAIL" if len(calls) < 3 else "PASS", "stage": stage}
        result = run_pipeline(self.root, {"orchestration": {"max_retries": 2}}, runner=runner, now=self.now)
        self.assertEqual(result["status"], "PASS", result)
        self.assertEqual(len(calls), 5)

    def test_pipeline_resume_skips_completed_stage(self):
        calls = []
        def runner(stage):
            calls.append(stage)
            return {"status": "PASS", "stage": stage}
        config = {"orchestration": {"max_retries": 0}}
        first = run_pipeline(self.root, config, runner=runner, now=self.now)
        self.assertEqual(first["status"], "PASS")
        calls.clear()
        second = run_pipeline(self.root, config, runner=runner, now=self.now, resume=True)
        self.assertEqual(second["status"], "PASS")
        self.assertEqual(calls, [])

    def test_resume_rejects_forged_state_without_evidence(self):
        path = self.root / ".mathmodel" / "orchestration-state.json"
        path.parent.mkdir()
        path.write_text(json.dumps({"schema_version": 1, "stages": {"build": {"status": "PASS"}, "audit": {"status": "PASS"}, "package": {"status": "PASS"}}, "attempts": []}), encoding="utf-8")
        result = run_pipeline(self.root, {"orchestration": {}}, runner=lambda stage: {"status": "PASS"}, now=self.now, resume=True)
        self.assertEqual(result["status"], "FAIL")

    def test_pipeline_rejects_stage_subset(self):
        result = run_pipeline(self.root, {"orchestration": {"stages": ["package"]}}, runner=lambda stage: {"status": "PASS"}, now=self.now)
        self.assertEqual(result["status"], "FAIL")

    def test_pipeline_rechecks_expiration_after_stage(self):
        config = {"orchestration": {"contest_start": "2026-09-01T08:00:00+00:00", "contest_deadline": "2026-09-01T10:00:01+00:00", "submission_buffer_seconds": 0}}
        ticks = iter([self.now, self.now + timedelta(seconds=2)])
        result = run_pipeline(self.root, config, runner=lambda stage: {"status": "PASS"}, now=self.now, clock=lambda: next(ticks))
        self.assertEqual(result["status"], "BLOCKED_TIME_BUDGET")

    def test_malformed_state_returns_structured_failure(self):
        path = self.root / ".mathmodel" / "orchestration-state.json"
        path.parent.mkdir()
        path.write_text(json.dumps({"schema_version": 1, "stages": [], "attempts": "bad"}), encoding="utf-8")
        result = run_pipeline(self.root, {"orchestration": {}}, runner=lambda stage: {"status": "PASS"}, now=self.now, resume=True)
        self.assertEqual(result["status"], "FAIL")

    def test_parallel_rejects_malformed_task_tuple(self):
        result = run_parallel([("a",)], max_workers=2)
        self.assertEqual(result["status"], "FAIL")

    def test_parallel_scheduler_returns_each_result(self):
        result = run_parallel([("a", lambda: 1), ("b", lambda: 2)], max_workers=2)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["results"], {"a": 1, "b": 2})


if __name__ == "__main__":
    unittest.main()
