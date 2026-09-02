# Phase 10 Progress

Source of truth for resuming the Phase 10 mission (`REAL-CASE-TRAINING-MISSION.md`). Update after every meaningful step.

## Completed

- [x] Mission fixed in `REAL-CASE-TRAINING-MISSION.md` (goal, stop condition, human checkpoints HC-1..HC-4).
- [x] Step 2: tag `pre-realcase-training-v1` verified → `e95ab2823f82e9a5460eb4815ab8abab26a2d6a7` (matches `current-state.md`).
- [x] Baseline tests: `Ran 326 tests ... OK (skipped=1)` at session start.
- [x] Step 3: OpenCode detected — v1.18.25 at `D:\Dev\.opencode\bin\opencode.exe`; global config `~/.config/opencode/opencode.json` defines provider `bai` (GLM 5.3 Flash); no project config existed.
- [x] Step 4: OpenCode contracts read (config schema, agent files, skills, permissions; skill: customize-opencode).
- [x] Step 5: `mathmodel-skill` registered via `opencode.json` `skills.paths: ["mathmodel-skill"]` — existing `mathmodel-skill/SKILL.md` reused, not duplicated. Note: `mathmodel-skill/vendor/` contains reference repos (award material) — Solver isolation prompt explicitly forbids it.
- [x] Steps 6–8: agent roles created — `.opencode/agent/mathmodel-dev.md` (primary), `mathmodel-solver.md` (subagent, isolation rules embedded), `mathmodel-judge.md` (subagent, read-only, JSON report contract).
- [x] Private case corpus curated: 7 cases under `benchmarks-private/cases/case-01..07` (see each `case.json`). Only self-contained cases kept.

## In progress

- [x] HC-1 passed: split manifest confirmed 2026-09-02 (4 TRAIN: case-02/03/04/05, 2 VALIDATION: case-06/07, 1 LOCKED HOLDOUT: case-01); splits written into each case.json.
- [x] HC-2 passed: agent roles approved.
- [x] Step 9: runner implemented at `benchmarks/realcase/run_case.py` (public code; workspace init / solve / audit / judge / failure-registry stages; guards: split-confirmed check, UNASSIGNED check, workspace-exists check; `--stage` selective rerun; `--resume-solve`). Regression tests: `benchmarks/realcase/test_run_case.py` (11 tests, OK).
- [x] Step 10 first loop (run 20260901T193906Z-wut-2026-07, case wut-2026-07):
  - solve: solver session ended on output-token limit (`reason: length`) after planning artifacts (problem-map, model-registry, data-audit, mathmodel.json) but before implementation/paper. Exit 0 with no completion marker.
  - audit: CLI ran; quality FAIL 11/85 (incomplete candidate) — deterministic evidence recorded in `eval/audit.json`.
  - judge: JSON report produced (overall 2.5/10; evidence-binding violations listed; tags ORCHESTRATION/EVIDENCE/WRITING/TIME) in `eval/judge_report.json`.
  - registry: `benchmarks-private/failure-registry/20260901T193906Z-wut-2026-07.json` with real tags.
  - generalized fixes (each locked by regression tests): parse opencode flat `{"type":"text"}` events; fenced-JSON extraction; project marker is `mathmodel.json`; solver continuation loop (`SOLVE-COMPLETE.txt` marker + session-continue up to 2x); judge scoping (`task: deny`, `external_directory: deny`, disable external skill scans via env); audit exits nonzero on gate FAIL but report presence is the orchestration success criterion.
- [ ] Step 10 rerun in flight: `--resume-solve` background run (runner PID in `%TEMP%\opencode\runner5.pid`, workspace `benchmark-workspaces/20260901T193906Z-wut-2026-07`). API incidents hit during the session: transient 401 auth-service timeout, then provider 429 rate-limit / empty responses (probe: 5/8 empty, 3/8 429); API recovered (verified by direct probes). Next session: check runner5 outcome, then run audit + judge + registry for the resumed solve.

## Environment notes

- Python 3.13.7; pypdf/python-docx/openpyxl/xlrd installed ad hoc this session.
- Windows PowerShell 5.1: `git rev-parse tag^{commit}` must be quoted (`"tag^{commit}"`), otherwise the shell mangles the argument.
- Unit tests must not be truncated with `Select-Object -Last` — capture to a file and grep for `^OK|^FAILED`.
- `docs/handoff/REAL-CASE-TRAINING-MISSION.md` was empty at handoff; the agent wrote it with user consent on 2026-09-02.
- Provider `bai` (api.b.ai) is rate-limited: expect intermittent 429/empty responses and rare 401 auth-timeouts; probe before blaming the runner.
- Solver runs must be backgrounded (`Start-Process`) — the interactive shell kills long commands.

## Corpus summary (private)

| case | id | title | attachments | trainable |
|---|---|---|---|---|
| case-01 | cumcm-2025-a | 2025 A 烟幕干扰弹 | none needed (self-contained) | yes |
| case-02 | wut-2026-07 | 微构体导电介质仿真 | A题附件 附件.xlsx | yes |
| case-03 | wut-2026-08 | VLSI布图规划 | B题附件 n100/200/300 | yes |
| case-04 | wut-2026-09 | 算电协同调度 | C题附件 7 files | yes |
| case-05 | wut-2026-10 | 机器人多源定位融合 | 第10题附件 5 files | yes |
| case-06 | wut-2026-11 | 方形材料切割优化 | 第11题附件 3 files | yes |
| case-07 | wut-2026-12 | 流感A血液筛查判别 | 第12题附件 2 files | yes |
