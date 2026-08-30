# Task 7 brief — Reusable mathmodel-skill coordination assets

## Scope

Implement only Task 7 from `docs/superpowers/plans/2026-08-30-mathmodel-paper-factory.md`. Read the plan/spec, current `mathmodel-skill/SKILL.md`, `skill-creator/SKILL.md`, `writing-skills/SKILL.md`, and the local OpenAI interface reference before editing. Do not implement Task 8+ orchestration fixtures.

## Owned files

- Modify `mathmodel-skill/SKILL.md` (keep under 500 lines)
- Create `mathmodel-skill/agents/openai.yaml`
- Create references: `workflow.md`, `evidence-contracts.md`, `paper-architecture.md`, `model-validation.md`, `quality-gates.md`, `figure-system.md`, `forecasting.md`, `optimization.md`, `evaluation.md`
- Create `mathmodel-skill/tests/test_skill_assets.py`

## Acceptance requirements

1. Follow TDD: failing asset tests first, then concise imperative Skill and references; write `task-7-report.md` with exact commands/results.
2. Skill front matter uses searchable `description: Use when...` trigger form and covers CUMCM paper creation/revision, modeling, LaTeX, data, reproducibility, page balance, and quality audit.
3. Skill routes deterministic checks through `scripts/mathmodel.py`, requires evidence before claims, requires body/appendix metrics, and describes manual-review boundaries.
4. All referenced files exist, references are concise and problem-type routed; include evidence contracts, paper architecture, validation, gates, figures, forecasting, optimization, and evaluation guidance.
5. `agents/openai.yaml` is valid and uses the local interface reference; do not invent unsupported metadata.
6. Run `quick_validate.py mathmodel-skill`, focused asset tests, and complete tests. Preserve only known environment-only skips.
7. Forward-test with fresh realistic prompts covering optimization, forecasting, and body/appendix imbalance repair. Record whether the Skill invokes CLI, creates registries, and rejects unsupported claims; do not modify production during forward tests.
