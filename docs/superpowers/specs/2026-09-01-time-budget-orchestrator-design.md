# Phase 8 — Time Controller & Unified Orchestrator

## Goal

Coordinate the existing gated pipeline with a profile-driven contest timeline, explicit stopping decisions, bounded retries, resumable state, and bounded parallel execution.

## Contracts

`mmcore.orchestration.time_budget` parses `contest_start`, `contest_deadline`, milestone deadlines, submission buffer, and exploration threshold. It emits `STOP_MODEL_SEARCH` only when the selected model beats baseline, validation passes, no critical finding is open, and the configured exploration threshold is reached.

`mmcore.orchestration.orchestrator` exposes `mathmodel run`. It executes only the fixed build→audit→package stages, persists `.mathmodel/orchestration-state.json`, skips completed stages only with `--resume`, and retries each stage at most the configured bounded count. Independent tasks use a bounded worker pool.

The orchestrator never weakens G0–G8, never treats malformed state as success, and blocks when the submission buffer is exhausted.
