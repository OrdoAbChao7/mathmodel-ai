# Task 5 review-fix report

## Review findings addressed

- Required page evidence that is unavailable now produces an explicit `NEEDS_MANUAL_REVIEW` audit status instead of `PASS`. The pending gate and its structured reason remain in the report. A `build` that is not `PASS` exits nonzero.
- Undefined references, undefined citations, fatal log diagnostics, and overfull boxes greater than 2 pt now make LaTeX compilation fail. Overfull boxes at or below 2 pt remain warnings with measured-point evidence.
- The template no longer contains release-blocking placeholder phrases. `TODO`, `TBD`, `待补充`, and `将在后续任务中补充` are detected in LaTeX sources and block both compile and audit paths.
- `measure_pdf` now calls `pdfinfo` independently of AUX-boundary validation, preserving total-page and A4 evidence when labels are absent. Invalid label order, non-A4 PDFs, nonzero/malformed `pdfinfo`, missing PDF/AUX, and unavailable `pdfinfo` remain structured results.
- The compiler retains its existing project-root main-path protection; a regression test now covers an out-of-project main file.

## TDD evidence

RED command:

```powershell
python -m unittest mathmodel-skill.tests.test_latex_metrics -v
```

Initial result: failed before the implementation with:

```text
ImportError: cannot import name 'find_latex_placeholders' from 'mmcore.latex'
```

The added regression suite covers the reviewed negative paths: successful passes missing PDF/AUX, unsafe main paths, placeholder source, invalid label ordering, non-A4 output, unavailable/nonzero/malformed `pdfinfo`, missing labels with retained total/A4 evidence, fatal logs, undefined references/citations, both overfull thresholds, and missing PDF/AUX audit status.

## Focused verification

Command:

```powershell
python -m unittest mathmodel-skill.tests.test_latex_metrics -v
```

Result: `Ran 23 tests ... OK`.

## Syntax and complete verification

Command:

```powershell
python -m py_compile mathmodel-skill/scripts/mmcore/latex.py mathmodel-skill/scripts/mmcore/pdfmetrics.py mathmodel-skill/scripts/mathmodel.py
python -m unittest discover -s mathmodel-skill/tests -v
```

Result: syntax check passed; complete suite reported `Ran 64 tests ... OK (skipped=1)`.

The only skip remains the known Windows symlink-permission case (`WinError 1314`).

## Git

No commit was created. This workspace has no Git repository metadata, so a Git commit is not possible here.
