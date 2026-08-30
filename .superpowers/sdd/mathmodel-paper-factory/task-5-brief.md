# Task 5 brief — LaTeX build, PDF metrics, and body/appendix gates

## Scope

Implement only Task 5 from `docs/superpowers/plans/2026-08-30-mathmodel-paper-factory.md` in the shared workspace. Do not implement Task 6+ features.

## Files owned by this task

- Create `mathmodel-skill/scripts/mmcore/latex.py`
- Create `mathmodel-skill/scripts/mmcore/pdfmetrics.py`
- Modify `mathmodel-skill/scripts/mathmodel.py`
- Modify `mathmodel-skill/assets/project-template/paper/main.tex`
- Create `mathmodel-skill/tests/test_latex_metrics.py`

## Required interfaces

- `compile_latex(project: Path, main: Path, engine: str, jobname: str) -> dict`: run two passes with argument arrays in `build/latex`; preserve logs, PDF path, exit codes, and warnings.
- `parse_aux_pages(aux: Path, labels: tuple[str, ...]) -> dict[str, int]`: parse `\\newlabel` page numbers.
- `measure_pdf(pdf: Path, aux: Path) -> dict`: report total/body/reference/appendix page counts and appendix/body ratio; use `pdfinfo` when available and aux boundary labels for sections.
- `evaluate_page_gates(metrics: dict, quality: dict) -> list[dict]`: emit hard failures/warnings for body below configured minimum, appendix/body over configured maximum, total outside configured range, and quality/release blockers as specified.

## Acceptance requirements

1. Write RED tests first, then implementation, then GREEN verification.
2. Template contains executable labels and clear-page boundaries for body start/end, references start/end, and appendix start/end.
3. LaTeX invocation is safe: argument arrays, project-scoped cwd/output, two passes, retained logs, and no shell interpolation.
4. Missing engine, compile failure, missing PDF/AUX, malformed labels, missing boundaries, and unavailable `pdfinfo` produce controlled structured results rather than uncaught exceptions.
5. Metrics distinguish body pages from appendix pages; total pages alone must never satisfy the body gate.
6. Body minimum, total range, appendix/body ratio, and quality threshold are read from config/quality contract; use conservative `PENDING` states where external tools or source artifacts are unavailable.
7. Add tests for parser, page arithmetic, ratio hard failure, body-minimum hard failure, compile command/log behavior using a fake engine, malformed/missing inputs, and CLI/build report integration.
8. Run `python -m unittest discover -s mathmodel-skill/tests -v` and the focused Task 5 suite; preserve the known Windows symlink permission skip only.
9. Do not create or modify PDF files manually as a substitute for implementation. Do not implement analysis/figure registry work from later tasks.

## Verification notes

The real project includes `traning1/paper/main.pdf` and a current 38-page build. If tools are available, verify that reports name the selected PDF and separate body/appendix counts; if not, record the controlled pending state and exact reason.

## Reporting

Write implementation evidence and test output to `.superpowers/sdd/mathmodel-paper-factory/task-5-report.md`. No Git commit is possible in this workspace; do not claim one.
