# Task 9 brief — Real `traning1` integration and certification

## Scope

Implement only Task 9 from the plan. Read plan/spec, current Skill/references, existing `traning1` solver/paper, and all current CLI contracts. Preserve the existing numerical solver and outputs; do not rewrite the model math to manufacture a pass.

## Owned files

- Modify `traning1/mathmodel.json`
- Create `traning1/analysis/run.py`
- Create `traning1/artifacts/`
- Create `traning1/build/`
- Create `traning1/quality-report/`
- Create `mathmodel-skill/tests/test_training1.py`
- Modify `traning1/paper/main38.tex` only for stable boundary labels and registry references

## Acceptance requirements

1. Follow TDD and write `task-9-report.md` with exact RED/GREEN/verification results.
2. `traning1` becomes a real optimization fixture using its existing solver/enhancer; preserve original numerical outputs and keep original `main.tex` available.
3. Adapter converts existing JSON/CSV/XLSX/numerical outputs into all seven evidence registries with stable IDs and complete question→model→result→claim→validation/figure links.
4. Chosen paper source has executable body/reference/appendix boundary labels and registry references; no fabricated page count or unsupported claims.
5. `run_fixture(TRAINING1)`/equivalent integration test executes the standard flow and verifies q3 exists, body pages >=26, appendix/body <=0.25, role-complete figures, and no hard failures.
6. If real XeLaTeX/MiKTeX is unavailable, use only the existing controlled compiler contract and record the limitation; never treat total PDF pages as body pages.
7. Render/inspect the complete PDF or available preview/contact-sheet outputs and record manual decisions for clipped equations, unreadable tables, missing figures, and appendix-only core content.
8. Run focused and complete suites; preserve known environment-only skips only.
