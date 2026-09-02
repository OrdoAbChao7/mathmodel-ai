# Real-Case Training Mission (Phase 10)

This file is the autonomous-execution mission for the incoming agent. It was written by the agent on 2026-09-02 with explicit user consent ("目标达到之前都不要停止" — do not stop until the goal is reached).

## Goal

Complete the Phase 10 first milestone defined in `docs/handoff/NEXT.md`, then run exactly one TRAIN case end-to-end through the full training loop:

```text
real problem → isolated solver workspace → complete generated project/paper
→ deterministic evaluation → blind judge → failure registry
→ generalized fix → regression test → rerun train
```

## Stop condition

The mission is complete when ALL of the following exist on disk and are internally consistent:

1. `pre-realcase-training-v1` tag verified.
2. OpenCode integration configured (skill registered, three agent roles `mathmodel-dev` / `mathmodel-solver` / `mathmodel-judge` defined).
3. A versioned private split manifest for the 7 available private cases (assigned BEFORE any results are generated).
4. One TRAIN case executed end-to-end producing: solver workspace artifacts + deterministic evaluation report + blind judge report + failure registry entry (taxonomy from `real-case-training-protocol.md`) + a generalized fix with a passing regression test, then a rerun.
5. All existing local gates still pass: `python -m unittest discover -s mathmodel-skill/tests -p "test_*.py"` and fixture benchmark.
6. A progress/state file (`docs/handoff/phase10-progress.md`) recording every stopping point, so any interruption resumes losslessly.

## Rules of engagement

- Continue autonomously through non-consequential decisions; stop only at human-owned checkpoints (split confirmation, H1–H4, holdout opening).
- Never let external providers set PASS, freeze results, or select the final model.
- Keep Solver, Evaluator, and Judge workspaces isolated; no oracle material in Solver paths.
- No holdout opening. No LLM fine-tuning. The corpus has 7 cases: 4 TRAIN / 2 VALIDATION / 1 LOCKED HOLDOUT.
- If context/session ends, the progress file is the source of truth; the next session continues from it, not from chat history.

## Human checkpoints (agent must stop and ask)

- HC-1: Confirm the split manifest (one-time, before first TRAIN run).
- HC-2: Review of the three agent role definitions before first solver run.
- HC-3: After first TRAIN loop completes: accept failure-learning fix or revert.
- HC-4: Any decision to rerun validation/holdout (out of scope for this mission).
