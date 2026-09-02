# NEXT DEVELOPMENT PHASE

> **Status update 2026-09-03:** the Phase 10 milestone below has been **completed**. The OpenCode agent roles (`mathmodel-dev` / `mathmodel-solver` / `mathmodel-judge`), the real-case runner `benchmarks/realcase/run_case.py`, the staged solver pipeline, the private corpus split (TRAIN / VALIDATION / LOCKED HOLDOUT), and the first TRAIN-case run all exist now. The active frontier is executing the training loop described in `docs/handoff/real-case-training-protocol.md` — remaining TRAIN cases, failure registry, generalized fixes with regression tests, then VALIDATION, then the locked holdout. See `AGENTS.md` for the full current state. The text below is preserved as the historical Phase 10 plan.

## Phase 10 — OpenCode Integration + Real Agent Runner

This is the only planned next phase after the handoff baseline. Do not reimplement the Competition OS core.

## First milestone

The incoming OpenCode agent should complete these steps in order:

1. Inspect the actual repository and read `AGENTS.md`.
2. Verify the `pre-realcase-training-v1` tag and its commit SHA.
3. Detect the installed OpenCode version.
4. Read the official OpenCode configuration, agent, skill, and CLI contracts.
5. Configure the existing `mathmodel-skill` without duplicating it.
6. Create the `mathmodel-dev` agent role.
7. Create the `mathmodel-solver` agent role.
8. Create the `mathmodel-judge` agent role.
9. Build an isolated OpenCode runner around the existing local gates and evidence contracts.
10. Run exactly **one TRAIN historical case** end-to-end.

Do not start with all ten cases. Do not open the locked holdout. Do not expose oracle material to the Solver.

## Constraints for Phase 10

- Preserve the local authority chain and all existing CLI behavior.
- Reuse `mathmodel-skill/SKILL.md` and `mathmodel-skill/scripts/mmcore/`; do not create a second hidden pipeline.
- Keep Solver, Evaluator, and Judge workspaces isolated.
- Require evidence-derived evaluation rather than judging prose alone.
- Record failures using the taxonomy in `docs/handoff/real-case-training-protocol.md`.
- Any system change learned from TRAIN must become a regression test before validation cases are rerun.

## Explicitly not done in this handoff

```text
OpenCode integration NOT implemented
Agent Runner NOT implemented
real-case training NOT started
Holdout NOT opened
LLM fine-tuning NOT started
blind judge NOT implemented
failure learning engine NOT implemented
```

The exact next action is:

> Switch to OpenCode and execute Phase 10 from this file.
