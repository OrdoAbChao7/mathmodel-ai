# Phase 13 Goal — Real-Case Training

Continue improving MathModel-AI through real historical modeling cases.

Before working, read:

- AGENTS.md
- docs/handoff/real-case-training-protocol.md
- mathmodel-skill/CONSTITUTION.md
- mathmodel-skill/SKILL.md
- benchmarks/realcase/run_case.py

Then inspect the ACTUAL local repository, benchmarks-private/, benchmark-workspaces/, failure registry, recent commits, and existing runs.

Do not rely on previous chat history.

## Goal

Execute this loop continuously:

TRAIN case
→ staged solve
→ deterministic audit
→ blind judge
→ failure registry
→ cross-run failure analysis
→ choose ONE generalized high-value failure
→ smallest generalized fix
→ regression test
→ fresh rerun
→ before/after comparison
→ PROMOTE / REVERT
→ next TRAIN task

The objective is better generalization on unseen mathematical-modeling problems, NOT memorizing TRAIN cases.

## Rules

Use the staged solver by default:

frame
→ model
→ per-question experiments
→ paper
→ complete
→ audit
→ judge
→ registry

Resume recoverable incomplete runs instead of restarting them.

Never expose Solver to oracle, reference solutions, previous solutions, judge reports, failure analyses, or Holdout information.

Never hard-code case IDs, known answers, winning-paper methods, or case-specific solution text.

Separate failures into:
- infrastructure;
- workflow;
- modeling;
- paper/communication.

Infrastructure failures are not modeling-training evidence.

Prefer fixes that are:
high-severity + repeated + generalizable + competition-relevant.

Put fixes in the correct layer:
- modeling knowledge → references/method cards;
- forgotten procedure → SKILL / solver workflow;
- mechanically preventable error → mmcore + tests;
- model-selection weakness → model tournament / risk probe;
- validation weakness → semantic validation / falsification;
- unsupported writing → claim/paper review;
- time/context failure → staged runner / stopping policy.

Every public behavior change derived from TRAIN must have regression protection.

After each meaningful change run relevant tests plus:

python -m unittest discover -s mathmodel-skill/tests -p "test_*.py"
python -m unittest discover -s benchmarks/realcase -p "test_*.py"
python benchmarks/run_fixture_benchmark.py

Then rerun affected TRAIN cases from fresh isolated workspaces.

Compare completion, audit failures, critical failures, judge findings, reproducibility, runtime, retries, and stability.

Do not optimize only for one overall judge score.

## Cross-case learning

Do not perfect one case indefinitely.

Once at least 3 different TRAIN cases have valid audit + judge evidence, pause and cluster failures across cases.

Use repeated systemic failures to decide the next capability improvement.

## Validation / Holdout

Do not open VALIDATION after every change.

Use VALIDATION only after several TRAIN-derived fixes form a stable frozen candidate.

Do NOT open LOCKED HOLDOUT without explicit human authorization.

Never change the frozen TRAIN/VALIDATION/HOLDOUT split based on observed results.

## Autonomous continuation

A completed subtask is NOT mission completion.

After every verified milestone:

inspect state
→ choose highest-value safe unfinished TRAIN task
→ execute
→ verify
→ record evidence
→ continue

Continue autonomously until genuinely blocked.

Stop only for:
- Holdout authorization;
- ambiguous oracle/data provenance;
- unavailable credentials/quota;
- destructive irreversible action;
- repeated unsafe failures;
- no remaining authorized TRAIN work.

If blocked, record exact HEAD, current case/run, completed work, evidence, blocker, and recommended next action.

## Immediate instruction

Inspect the actual local state first.

Resume an incomplete recoverable TRAIN run if one exists.

Otherwise continue the next unfinished TRAIN case.

Do not redesign the Competition OS.

Do not restart Phase 10.

Do not open Holdout.

Keep advancing the empirical training loop.