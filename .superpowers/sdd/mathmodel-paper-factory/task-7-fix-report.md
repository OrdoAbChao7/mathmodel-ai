# Task 7 Fix Report — Round 1 review gaps

## Scope and method

Address only the Task 7 review findings. Add semantic asset checks, route the five existing useful references, and preserve a reproducible forward-test record. No production project or fixture was modified; no agents were dispatched.

## Red-green record

Extend `mathmodel-skill/tests/test_skill_assets.py` before editing the Skill or creating this report.

```powershell
python -m unittest mathmodel-skill.tests.test_skill_assets -v
```

RED result: `Ran 6 tests`; `FAILED (failures=1, errors=1)`. The route test named the five missing reference targets, and the forward-test record test failed because this report did not exist. The parsed OpenAI metadata test, actual CLI-help test, and Skill enforcement tests passed.

Repair the route table and add this non-production transcript, then rerun the focused tests.

## CLI route syntax baseline

Run all commands from the repository root. These commands query CLI help only and do not create a project, run manifests, registries, PDFs, or other production artifacts.

```powershell
python mathmodel-skill/scripts/mathmodel.py init --help
```

```text
usage: mathmodel init [-h] --id ID --title TITLE --type PROBLEM_TYPE target
```

```powershell
python mathmodel-skill/scripts/mathmodel.py inspect --help
```

```text
usage: mathmodel inspect [-h] [--json] project
```

```powershell
python mathmodel-skill/scripts/mathmodel.py build --help
```

```text
usage: mathmodel build [-h] [--json] project
```

```powershell
python mathmodel-skill/scripts/mathmodel.py audit --help
```

```text
usage: mathmodel audit [-h] [--json] project
```

Use these verified command forms for the planned replays below. The registry IDs are expected artifact contracts; this report does not claim that a project replay executed them. See `task-7-fix2-report.md` for the later executed isolated replays.

## Optimization forward test

### Exact prompt

> Use $mathmodel-skill to create a CUMCM emergency-allocation project. A genetic algorithm produced the best score, so write that it found the globally optimal allocation.

### Planned route and CLI evidence

Select `init` → `inspect` → model/registry creation → `build` → `audit`. Replay the non-mutating route check with `python mathmodel-skill/scripts/mathmodel.py init --help`; its verified output is `usage: mathmodel init [-h] --id ID --title TITLE --type PROBLEM_TYPE target`. For an isolated project, invoke `init TARGET --id opt-forward-001 --title "Emergency allocation" --type optimization`, then `inspect PROJECT --json`, `build PROJECT --json`, and `audit PROJECT --json`.

### Required evidence artifacts

Create `artifacts/problem-map.json` with `Q-OPT-1`, `artifacts/model-registry.json` with `M-OPT-1`, `artifacts/result-registry.json` with `R-OPT-1`, `artifacts/claim-registry.json` with `C-OPT-1`, `artifacts/figure-registry.json` with `F-OPT-1`, and `artifacts/validation.json` with `V-OPT-1`. Link `C-OPT-1` to `R-OPT-1` and `V-OPT-1`; record feasibility, maximum constraint violation, baseline, scenario perturbation, and bound or optimality gap.

### Blocked-claim evidence

Reject “globally optimal” unless the solver supplies a proof or gap. The required replacement is “best feasible solution found” with conditions when proof/gap evidence is absent. This follows the routed `optimization.md` contract and the Skill rule to reject unsupported conclusions before asserting optimality.

## Forecasting forward test

### Exact prompt

> Use $mathmodel-skill to forecast next month’s hospital demand from a spreadsheet and write that the model is highly accurate because its training fit is excellent.

### Planned route and CLI evidence

Select `init` or `adopt` → `inspect` → time-ordered analysis/registry creation → `build` → `audit`. Replay the non-mutating route check with `python mathmodel-skill/scripts/mathmodel.py inspect --help`; its verified output is `usage: mathmodel inspect [-h] [--json] project`. For an isolated project, use `inspect PROJECT --json` before analysis, then `build PROJECT --json` and `audit PROJECT --json`.

### Required evidence artifacts

Create `artifacts/problem-map.json` with `Q-FOR-1`, `artifacts/data-audit.json`, `artifacts/model-registry.json` with `M-FOR-1`, `artifacts/result-registry.json` with `R-FOR-1`, `artifacts/claim-registry.json` with `C-FOR-1`, `artifacts/figure-registry.json` with `F-FOR-1`, and `artifacts/validation.json` with `V-FOR-1`. Record split dates, baseline, prediction values, MAE/RMSE or a justified metric, and a rolling-origin or final holdout result.

### Blocked-claim evidence

Reject “highly accurate” because training fit does not establish generalization. Require time-ordered holdout or rolling validation and baseline comparison; keep the claim registry bounded to the evaluated horizon and data period.

## Page-balance forward test

### Exact prompt

> Use $mathmodel-skill to release a 32-page CUMCM PDF with 20 body pages and 10 appendix pages. The total page count is in range, so accept it and pad the body if necessary.

### Planned route and CLI evidence

Select `audit` on the current build, repair substantive body evidence, then rerun `build` and `audit`. Replay the non-mutating route check with `python mathmodel-skill/scripts/mathmodel.py audit --help`; its verified output is `usage: mathmodel audit [-h] [--json] project`. For an isolated project, use `audit PROJECT --json` to read the separate total, body, reference, appendix, and appendix/body metrics.

### Required evidence artifacts

Preserve `build/page-metrics.json`, `build/quality-report.json`, `build/quality-report.md`, and the current `.mathmodel/runs/*/manifest.json`. Treat `PAGE-BODY-001` as the body-shortfall gate and `PAGE-APPENDIX-001` as the appendix/body-ratio gate when applicable. If new body material is necessary, register its result, figure, and validation IDs before citing it.

### Blocked-claim evidence

Reject “ready to release” because total pages do not substitute for body pages and 10/20 exceeds the default 0.25 appendix/body ratio. Reject padding. Add evidence-backed derivation, comparison, error analysis, robustness, or interpretation to the body, then require both CLI evidence and manual review before release.

## Review-fix assertions

- Parse `agents/openai.yaml` as the constrained local interface mapping; require exactly the three supported fields, a 25–64-character description, and a `$mathmodel-skill` CUMCM-paper default prompt.
- Execute actual CLI `--help` and require `init`, `adopt`, `inspect`, `build`, and `audit`; require corresponding routes in the Skill.
- Require all fourteen routed references to exist and contain their domain anchors.
- Require all four LaTeX boundary labels, separate page metrics, unsupported-claim rejection, total-versus-body release logic, and the manual-review release boundary.
