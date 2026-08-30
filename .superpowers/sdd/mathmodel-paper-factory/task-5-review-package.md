# Task 5 review package

This workspace is not a Git repository; review current files directly. Read `task-5-brief.md`, the plan/spec, implementation report, and inspect the owned source/tests. Do not edit source or tests. Run focused and complete tests.

Review scope:

- `mathmodel-skill/scripts/mmcore/latex.py`
- `mathmodel-skill/scripts/mmcore/pdfmetrics.py`
- `mathmodel-skill/scripts/mathmodel.py`
- `mathmodel-skill/assets/project-template/paper/main.tex`
- `mathmodel-skill/tests/test_latex_metrics.py`

Acceptance checklist: required interfaces exist; two-pass argument-array LaTeX execution is project-scoped and preserves logs; missing engine/compile failure/missing PDF/AUX/malformed labels/pdfinfo absence are structured; executable body/reference/appendix labels exist; metrics distinguish body from appendix; page and quality gates use config and hard-fail required limits; CLI/build integration reports selected PDF, page metrics and gates; tests cover parser, arithmetic, ratio/body gates, fake engine, malformed/missing inputs, and integration; no Task 6+ work slipped in. Return separate spec-compliance and task-quality verdicts and classify Critical/Important/Minor findings. Write full review to `task-5-review.md`.
