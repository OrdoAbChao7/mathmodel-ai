# Task 7 Report — Reusable mathmodel-skill coordination assets

## Scope

Changed only the Task 7 coordination assets:

- `mathmodel-skill/SKILL.md`
- `mathmodel-skill/agents/openai.yaml`
- nine Task 7 files under `mathmodel-skill/references/`
- `mathmodel-skill/tests/test_skill_assets.py`

No Task 8+ fixtures, CLI code, templates, or training project files changed. No Git commit was made.

## TDD record

Added `test_skill_assets.py` before changing the Skill assets. The first focused run was intentionally red:

```powershell
python -m unittest mathmodel-skill.tests.test_skill_assets -v
```

Result: `Ran 4 tests`; `FAILED (failures=3, errors=1)`. The failures identified missing Task 7 reference links, absent `agents/openai.yaml`, incomplete searchable trigger vocabulary, and no explicit CLI/evidence route.

Added the minimal Skill, metadata, and routed references. The next focused run was red only because `compiling` did not contain the literal searchable token `compile`:

```text
FAILED (failures=1)
```

Changed the description to include `compile`, then reran:

```powershell
python -m unittest mathmodel-skill.tests.test_skill_assets -v
```

Result: `Ran 4 tests in 0.001s`; `OK`.

## Asset decisions

- Kept `SKILL.md` imperative and below 500 lines.
- Used a `description: Use when...` trigger containing CUMCM, paper, modeling, LaTeX, data, reproducibility, page-balance, quality-audit, and compile terms.
- Routed deterministic state checks through `scripts/mathmodel.py` and retained the actual available CLI commands: `init`, `adopt`, `inspect`, `build`, and `audit`.
- Required stable registry IDs, traceable result/claim/figure links, current run evidence, separate body/reference/appendix/total metrics, and a manual-review boundary.
- Used only supported local OpenAI interface fields: `display_name`, `short_description`, and `default_prompt`.

## Validation commands and results

```powershell
python D:/Dev/.codex/skills/.system/skill-creator/scripts/quick_validate.py mathmodel-skill
```

Result: `Skill is valid!`

```powershell
python -m unittest mathmodel-skill.tests.test_skill_assets -v
```

Result: `Ran 4 tests in 0.001s`; `OK`.

```powershell
python -m unittest discover -s mathmodel-skill/tests -v
```

Result: `Ran 84 tests in 2.284s`; `OK (skipped=1)`.

The sole skip is the pre-existing environment-only Windows symlink test: `WinError 1314` reports that the current user lacks the symlink privilege. No other tests skipped or failed.

## Forward tests (no production modification)

Performed three fresh prompt walkthroughs from the completed Skill instructions rather than dispatching agents, as Task 7 explicitly prohibits subagents. No production project, fixture, or source asset was created or changed during these walkthroughs.

| Prompt | CLI route selected | Registry action | Unsupported claim outcome |
|---|---|---|---|
| “Create a CUMCM optimization project for emergency allocation. The genetic algorithm produced the best score, so call it globally optimal.” | `init` → `inspect` → `build` → `audit` | Require problem map, model/result/claim/figure/validation records before prose results | Reject “globally optimal” without a solver proof or bound/gap; require feasibility, constraint violation, baseline, and perturbation evidence |
| “Forecast next month’s hospital demand from the spreadsheet and write that the model is highly accurate.” | `init` or `adopt` → `inspect` → `build` → `audit` | Require data audit plus time-split result and validation IDs | Reject the accuracy claim until time-ordered holdout or rolling evidence, baseline comparison, and MAE/RMSE or justified metric exist |
| “The PDF has 32 pages, but only 20 are body and 10 are appendix. Treat it as ready and pad the body if needed.” | `audit` after the current build; rerun `build` after substantive repair | Preserve page metrics and link new evidence/figures only when added | Reject total pages as a body substitute and reject padding; require body/appendix metrics, then add evidence-backed derivation, comparison, validation, or interpretation to the body |

Each walkthrough selected the CLI, required the relevant registries, and blocked the unsupported conclusion or release request. The Skill also keeps visual, academic, and submission-readiness judgment inside mandatory manual review after machine checks pass.
