# Phase 8 — Time Controller & Unified Orchestrator

## Goal

Coordinate the existing gated pipeline with a profile-driven contest timeline, explicit stopping decisions, bounded retries, resumable state, and bounded parallel execution.

## Contracts

`mmcore.orchestration.time_budget` parses `contest_start`, `contest_deadline`, milestone deadlines, submission buffer, and exploration threshold. It emits `STOP_MODEL_SEARCH` only when the selected model beats baseline, validation passes, no critical finding is open, and the configured exploration threshold is reached.

`mmcore.orchestration.orchestrator` exposes `mathmodel run`. It executes only the fixed build→audit→package stages, persists `.mathmodel/orchestration-state.json`, skips completed stages only with `--resume`, and retries each stage at most the configured bounded count. Independent tasks use a bounded worker pool.

The orchestrator never weakens G0–G8, never treats malformed state as success, and blocks when the submission buffer is exhausted.

## Human checkpoint sequencing

Formal modes also enforce the CUMCM human-governance sequence at orchestration boundaries. Before `build`, H1 (problem understanding) and H2 (method selection) must have current approved records; before `audit`, H3 (result verification) must be approved; before `package`, H4 (final submission) must be approved. A missing, stale, malformed, or rejected record returns `BLOCKED_HUMAN_INPUT` with the blocked stage and required gates, and no runner is invoked for that stage. Research mode remains not applicable and keeps the existing autonomous behavior.

The CLI accepts `mathmodel run PROJECT --profile cumcm --mode competition-max --json` as a per-run override. The mode name is normalized to the internal `execution_mode` value and the on-disk `mathmodel.json` remains unchanged.
