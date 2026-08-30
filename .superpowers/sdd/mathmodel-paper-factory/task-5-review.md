# Task 5 independent review

## Summary and verdicts

The Task 5 implementation has a good basic shape: compilation uses argument arrays and `shell=False`, writes pass-specific stdout/stderr and engine logs, parses the requested AUX labels, separates body/reference/appendix arithmetic, and exposes structured records. The focused and complete test suites both pass, and the reviewed Python files compile.

Overall verdict:

- **Spec compliance: FAIL.** Missing or pending page evidence can be treated as non-blocking by the audit exit decision, and undefined references/citations are recorded only as warnings even though the design makes them release-blocking failures. The template also ships unresolved placeholder text.
- **Task quality: FAIL.** The happy-path tests cover the principal arithmetic and fake-engine flow, but do not cover several explicit failure modes or the CLI behavior that caused the release-gate issue.

## Verification performed

- Focused suite: `python -m unittest mathmodel-skill.tests.test_latex_metrics -v` — **12 passed**.
- Complete suite: `python -m unittest discover -s mathmodel-skill/tests -v` — **53 passed, 1 skipped**. The skip is the existing Windows symlink-permission case.
- Syntax check: `python -m py_compile mathmodel-skill/scripts/mmcore/latex.py mathmodel-skill/scripts/mmcore/pdfmetrics.py mathmodel-skill/scripts/mathmodel.py` — **passed**.
- Historical PDF probe: both `traning1/paper/main.pdf` and `traning1/paper/main38.pdf` were found, but their AUX files have none of the six required boundary labels. `measure_pdf` returned structured `FAILED` results with `PDF-LABEL-001` and no body/appendix counts, so total pages were not used as a body substitute.
- Direct gate probe: `_has_hard_failure({'status': 'PASS'}, [{'severity': 'FAIL', 'status': 'PENDING'}])` returned `False`; the same probe with gate status `FAIL` returned `True`.

## Findings

### Critical — unavailable page evidence can produce a successful audit

`mathmodel-skill/scripts/mmcore/pdfmetrics.py:72-84` emits `PAGE-METRICS-001` with status `PENDING` when the PDF, AUX, labels, or `pdfinfo` result is unavailable. `mathmodel-skill/scripts/mathmodel.py:82-87` only blocks gates whose status is `FAIL`, so `audit` can return success when page metrics are pending. For example, a valid artifact contract plus no current PDF yields a non-blocking pending page gate.

**Why:** The design says a missing PDF or unparseable page boundaries is a hard release gate, and a pending visual/page audit cannot be declared final. A caller can therefore receive `audit: PASS` without proving the required PDF, body minimum, appendix ratio, or A4 status.

**Suggestion:** Make the CLI’s release decision treat required page-gate `PENDING` states as blocking (or return an explicit non-release `NEEDS_MANUAL_REVIEW` status and non-zero exit code). Keep the structured pending reason, but do not map it to a successful audit. Add an integration test for missing PDF/AUX and unavailable `pdfinfo`.

### Critical — undefined references and citations do not block the build

`mathmodel-skill/scripts/mmcore/latex.py:37-44` records undefined references, undefined citations, and overfull boxes as warnings. A successful two-pass compile at `:151-152` remains `SUCCESS` when those warnings exist, and `mathmodel-skill/scripts/mathmodel.py:173-186` does not convert them into page gates or another blocking condition.

**Why:** The specification lists undefined references and undefined citations among hard gates. A paper with broken cross-references can therefore pass the compile portion of `build`. The same implementation also does not distinguish the specified overfull-box threshold (≤2 pt warning versus >2 pt failure); it only detects the phrase and emits one warning.

**Suggestion:** Parse the relevant log diagnostics with enough detail to apply the contract: undefined references/citations should create release-blocking failures, and overfull boxes should extract the amount and classify it according to the 2 pt threshold. Preserve the warning/error records and add fake-engine tests asserting both build status and exit code.

### Important — the shipped template contains unresolved placeholder text

`mathmodel-skill/assets/project-template/paper/main.tex:11,17,21,28,36` contains phrases such as `待补充` and “将在后续任务中补充”.

**Why:** The global design contract says placeholder text such as `TODO`, `TBD`, and `待补充` must not pass release. A newly initialized project starts with these strings, while Task 5’s build path does not scan the source and does not add a hard gate for them. Even if the template is intentionally skeletal, the current pipeline provides no enforcement boundary between a scaffold and a releasable paper.

**Suggestion:** Either make the template’s scaffold status explicit and ensure the audit/build contract always rejects these tokens before release, or replace them with non-placeholder instructional comments that cannot be mistaken for paper content. Add a test covering the release behavior.

### Important — several explicit failure paths are untested

`mathmodel-skill/tests/test_latex_metrics.py` covers the normal AUX arithmetic, missing/malformed parser input, one missing-engine case, one nonzero fake-engine case, and two gate failures. It does not cover missing PDF/AUX after two successful engine passes, invalid boundary ordering, non-A4 output, `pdfinfo` nonzero/malformed output, fatal log diagnostics, overfull threshold classification, undefined citations as a release blocker, unsafe/out-of-project main paths, or the audit result when metrics are pending.

**Why:** These are not merely theoretical branches: the pending-gate behavior above is a direct consequence of an untested integration boundary, and the hard-gate requirements specifically call out missing PDF/AUX, malformed labels, and unavailable external tools.

**Suggestion:** Add table-driven negative tests for every structured error/pending state, plus CLI assertions for status and exit code. Keep the Windows fake-engine test, but also add platform-independent subprocess mocks so the core failure matrix runs everywhere.

### Minor — `measure_pdf` stops before collecting available total-page evidence when labels are missing

`mathmodel-skill/scripts/mmcore/pdfmetrics.py:85-96` validates all AUX labels and returns before invoking `pdfinfo`. Consequently, a real PDF with missing labels reports `total_pages: null` even when `pdfinfo` is installed and could provide a reliable total-page count.

**Why:** It is correct not to use total pages as a body gate, but retaining the independently available total-page and A4 evidence would make the controlled failure report more useful and would substantiate the historical verification requirement.

**Suggestion:** Run `pdfinfo` independently of boundary validation, retain total/A4 fields, then add the missing-label error and leave body/reference/appendix metrics unavailable.

## Acceptance requirements

| Requirement | Direct assessment |
|---|---|
| Required compiler/parser/metrics/gate interfaces | **Addressed.** All four interfaces exist with the requested basic return shapes. |
| Two-pass argument-array, project-scoped LaTeX execution | **Addressed.** Uses `subprocess.run` with an argument list, `cwd=root`, output under `build/latex`, and `shell=False`. |
| Retained logs, PDF path, exit codes, warnings | **Addressed.** Pass stdout/stderr and engine logs are retained; result includes paths and exit codes. |
| Structured missing engine, compile failure, missing PDF/AUX, malformed labels, and missing `pdfinfo` handling | **Partially addressed.** Results are structured, but missing/pending evidence is not reliably release-blocking; missing PDF/AUX after a successful fake compile is not directly tested. |
| Executable body/reference/appendix labels and clear-page boundaries | **Addressed.** The template contains all six labels and clear-page boundaries. |
| Body metrics distinct from appendix metrics | **Addressed with caveat.** Arithmetic is implemented and does not use total pages as body pages; labels must be present. |
| Configured body/total/ratio and quality gates | **Partially addressed.** Config values are read and body/ratio hard failures work, but pending metrics and log hard gates can bypass release decisions. |
| CLI/build report names selected PDF and reports metrics/gates | **Addressed.** JSON/Markdown quality reports include compile result, selected PDF path, page metrics, and page gates. Historical missing-label cases correctly remain controlled failures. |
| Focused and complete verification | **Addressed.** 12 focused tests and 53 complete tests pass; one known Windows symlink skip remains. |
| Tests cover the stated parser, arithmetic, ratio/body gates, fake engine, malformed/missing inputs, and integration | **Partially addressed.** The listed happy paths exist, but the explicit negative and release-decision cases above are missing. |
| No Task 6+ work slipped in | **Addressed.** Reviewed changes stay within the Task 5 ownership list; no later registry/figure-analysis implementation was observed in these files. |

## Recommended next steps

First make pending/missing page evidence and LaTeX hard diagnostics block release, then add the missing negative/integration tests. Finally resolve or enforce the template placeholders and improve `measure_pdf` so available total/A4 evidence is retained alongside boundary failures.
