# MathModel-AI agent handoff

Incoming developer agent: **Codex**. This file is the entry point; read it fully before changing anything.

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

## Current stage (updated 2026-09-03)

The Competition OS core (Phases 0–8) is implemented and verified. Phase 10 — OpenCode Integration + Real Agent Runner — is implemented, and real-case empirical training has started.

What exists now:

- **OpenCode agent roles** in `.opencode/agent/`:
  - `mathmodel-dev` — primary agent for developing this repository itself; NOT for solving cases.
  - `mathmodel-solver` — solves one CUMCM case in an isolated workspace; use ONLY inside `benchmark-workspaces/<run-id>/`.
  - `mathmodel-judge` — blind judge; read-only; returns a JSON quality/failure report.
- **Real-case runner** `benchmarks/realcase/run_case.py`:
  ```text
  init workspace → staged SOLVE (opencode run --agent mathmodel-solver)
                → deterministic audit (local CLI)
                → blind JUDGE  (opencode run --agent mathmodel-judge)
                → private failure-registry entry
  ```
  Flags: `--case` (directory name or `case_id`), `--solve-timeout`, `--judge-timeout`, `--skip-solve`, `--stage {audit,judge,registry}`, `--resume-solve`, `--monolithic`.
- **Staged solver sessions** — a failure-driven generalized fix with regression tests. The solve is split into `frame → model → experiments → paper → complete`; the experiments stage expands into per-question stages from `artifacts/problem-map.json`; progress is tracked by sentinel files; unfinished stages continue the same session with bounded retries; timeouts are recorded as exit 124. `--monolithic` keeps the legacy single-session solver for comparison runs.
- **Immutable baseline tag** `pre-realcase-training-v1` (see `docs/handoff/current-state.md`).
- **Private corpus** `benchmarks-private/` (gitignored): historical cases with `problem/` and evaluator-only `oracle/` material, plus a frozen stratified TRAIN / VALIDATION / LOCKED HOLDOUT split confirmed by a human checkpoint. Isolated run workspaces and private failure-registry entries live under `benchmark-workspaces/` (gitignored). The first TRAIN case has been run end-to-end.

Current frontier: **execute the training loop** in `docs/handoff/real-case-training-protocol.md` — run the remaining TRAIN cases with the staged solver, classify every failure with the taxonomy, turn each generalized fix into a regression test before reruns, then run VALIDATION cases, then the locked holdout.

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
- `mathmodel-skill/SKILL.md` — the reusable modeling/paper workflow used by the Solver.
- `mathmodel-skill/scripts/mathmodel.py` — the CLI entry point.
- `mathmodel-skill/scripts/mmcore/` — local evaluators and orchestration implementation.
- `benchmarks/realcase/run_case.py` — the OpenCode-driven real-case runner (contains no private case data).
- `.opencode/agent/*.md` — the dev/solver/judge agent definitions.
- `docs/handoff/current-state.md` — factual architecture and phase audit (pre-training checkpoint record).
- `docs/handoff/baseline-verification.md` — latest reproducible verification record.
- `docs/handoff/real-case-training-protocol.md` — private-corpus layout, isolation rules, training loop, failure taxonomy.
- `docs/handoff/NEXT.md` — next actions for the incoming agent (top banner marks completed milestones).

## Important boundary

`mathmodel run` is an orchestration and evidence command, not an LLM modeling brain. `mmcore/orchestration/orchestrator.py` coordinates `build`, `audit`, `package`, resume behavior, time budgets, and human checkpoints. Reading the problem, choosing and explaining models, writing analysis code, running experiments, interpreting results, and drafting the paper are performed by the `mathmodel-solver` agent following `mathmodel-skill/SKILL.md`, driven non-interactively by `benchmarks/realcase/run_case.py`.

## Non-negotiables

- Never let an external provider set `PASS`, select the final model, freeze evidence, or release.
- Never let the Writer invent numerical results or alter frozen results.
- Never bypass validation, falsification, stale propagation, or human H1–H4 checkpoints in formal mode.
- Never let the benchmark solver read an oracle or score itself.
- Never expose reference papers, known solutions, judge notes, award metadata, or failure analysis to a solver before candidate freeze.
- Keep private cases under `benchmarks-private/`; keep isolated workspaces under `benchmark-workspaces/`.
- Do not commit private case data, credentials, generated PDFs, or local runtime state; never copy private case content into `mathmodel-skill/`, `tests/`, or public `benchmarks/cases/`.
- Once the split manifest is frozen and results have been viewed, never change the split to improve a score; if a holdout is opened and the system changes, reclassify that case.

## Verification commands

From the repository root:

```text
python -m unittest discover -s mathmodel-skill/tests -p "test_*.py"
python -m unittest discover -s benchmarks/realcase -p "test_*.py"
python benchmarks/run_fixture_benchmark.py
python mathmodel-skill/scripts/mathmodel.py capability . --json
python mathmodel-skill/scripts/mathmodel.py submission benchmarks/cases/formal-submission-fixture --json
```

The local fixture is synthetic evidence, not a competition score. The `traning1` build may be blocked by the machine's MiKTeX installation; classify that as an environment blocker only after checking the solver and analysis stages.

Real-case runs use the private corpus locally, e.g. `python benchmarks/realcase/run_case.py <case-name>`. Do not open the locked holdout as part of routine training.

## Next steps for this handoff

1. Run all verification commands above; everything must pass before any change.
2. Read `docs/handoff/real-case-training-protocol.md` and the private split manifest (under `benchmarks-private/`).
3. Continue the TRAIN loop with the staged solver: one case at a time, registry every failure, land generalized fixes + regression tests in public code while keeping case-specific observations private.
4. Do not start VALIDATION or the locked holdout until TRAIN results stabilize, and consult the human owner before opening the holdout.
