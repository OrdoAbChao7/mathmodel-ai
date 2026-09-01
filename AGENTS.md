# MathModel-AI agent handoff

## Mission

This repository is not an `LLM -> paper` shortcut. Its target is:

```text
agent reasoning
→ structured artifacts
→ deterministic verification
→ evidence-bound paper
→ independent review
```

The project is MathModel-AI v2: a human-governed CUMCM Competition OS. The core protects modeling reasonableness, creativity, result correctness/trust, and paper clarity while preserving human ownership of consequential decisions.

## Current stage

The Competition OS core is substantially implemented. The current development frontier is **REAL-CASE EMPIRICAL TRAINING**. Do not redesign the core or start Phase 10 work in this handoff commit; the next phase is specified in `docs/handoff/NEXT.md`.

## Authority chain

```text
official rules
>
mathmodel-skill/CONSTITUTION.md
>
deterministic local CLI and contracts
>
local orchestration
>
profiles
>
external adapters
>
external prose
```

External providers are advisory only. They cannot select a model, freeze results, set a gate to PASS, or release a package.

## Canonical files

- `mathmodel-skill/CONSTITUTION.md` — non-negotiable authority and safety principles.
- `mathmodel-skill/SKILL.md` — the reusable modeling/paper workflow.
- `mathmodel-skill/scripts/mathmodel.py` — the CLI entry point.
- `mathmodel-skill/scripts/mmcore/` — local evaluators and orchestration implementation.
- `docs/handoff/current-state.md` — factual architecture and phase audit.
- `docs/handoff/baseline-verification.md` — latest reproducible verification record.
- `docs/handoff/NEXT.md` — the only planned next phase for the incoming agent.

## Important boundary

`mathmodel run` is an orchestration and evidence command, not an LLM modeling brain. `mmcore/orchestration/orchestrator.py` coordinates `build`, `audit`, `package`, resume behavior, time budgets, and human checkpoints. Reading the problem, choosing and explaining models, writing analysis code, running experiments, interpreting results, and drafting the paper are performed by an external coding agent using `mathmodel-skill/SKILL.md`.

## Non-negotiables

- Never let an external provider set `PASS`, select the final model, freeze evidence, or release.
- Never let the Writer invent numerical results or alter frozen results.
- Never bypass validation, falsification, stale propagation, or human H1–H4 checkpoints in formal mode.
- Never let the benchmark solver read an oracle or score itself.
- Never expose reference papers, known solutions, judge notes, award metadata, or failure analysis to a solver before candidate freeze.
- Keep private cases under `benchmarks-private/`; keep isolated workspaces under `benchmark-workspaces/`.
- Do not commit private case data, credentials, generated PDFs, or local runtime state.

## Verification commands

From the repository root:

```text
python -m unittest discover -s mathmodel-skill/tests -p "test_*.py"
python benchmarks/run_fixture_benchmark.py
python mathmodel-skill/scripts/mathmodel.py capability . --json
python mathmodel-skill/scripts/mathmodel.py submission benchmarks/cases/formal-submission-fixture --json
```

The local fixture is synthetic evidence, not a competition score. The `traning1` build may be blocked by the machine's MiKTeX installation; classify that as an environment blocker only after checking the solver and analysis stages.

## Next planned phase

```text
Phase 10: OpenCode Integration + Agent Runner
```

Read `docs/handoff/NEXT.md` first. Do not implement an OpenCode runner in this handoff task.
