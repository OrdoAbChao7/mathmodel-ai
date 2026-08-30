# Task 5 fix re-review

## Summary

The fix closes the prior Task 5 Critical and Important findings in the covered paths. Pending page evidence is no longer represented as a releasable `PASS`; source placeholders are checked; undefined references/citations, fatal log diagnostics, and overfull boxes above 2 pt block compilation; the 2 pt boundary is classified correctly; negative cases and CLI integration are covered; and `measure_pdf` retains independently available total-page/A4 evidence when labels are missing.

One remaining Important issue was found outside the mocked test matrix: `measure_pdf` can raise an uncaught exception when `pdfinfo` output cannot be decoded using the Windows locale. The required historical probe reproduced this in the current environment, so the implementation is not yet fully release-safe for real PDF audits.

## Verification performed

- Focused suite: `python -m unittest mathmodel-skill.tests.test_latex_metrics -v` — **23 passed**.
- Syntax check: `python -m py_compile mathmodel-skill/scripts/mmcore/latex.py mathmodel-skill/scripts/mmcore/pdfmetrics.py mathmodel-skill/scripts/mathmodel.py` — **passed**.
- Complete suite: `python -m unittest discover -s mathmodel-skill/tests -v` — **64 passed, 1 skipped**.
- The sole skip remains the known Windows symlink-permission case (`WinError 1314`).
- Historical PDF probe against `traning1/paper/main.pdf` and `main38.pdf` did not return a controlled result: the subprocess reader raised `UnicodeDecodeError` under the system GBK locale, then `measure_pdf` raised `TypeError` because `completed.stdout` was `None`.

No source or test files were edited during this review. Only this review file was written.

## Previous finding verification

| Previous finding | Result | Evidence |
|---|---|---|
| Missing/pending page evidence could yield a successful audit | **Closed in status semantics** | `evaluate_page_gates()` emits a hard `PAGE-METRICS-001` gate with `PENDING`; `_release_status()` returns `NEEDS_MANUAL_REVIEW`; `build` returns non-zero for any status other than `PASS`. Focused CLI tests cover missing PDF/AUX and missing labels. |
| Undefined references/citations did not block compilation | **Closed** | `_scan_log()` records both diagnostics in `errors`; successful two-pass compilation is `FAILED` when errors exist. Focused tests assert the failure. |
| Overfull-box threshold was not applied | **Closed** | `_OVERFULL_RE` records measured points; `> 2` pt is an error and `<= 2` pt is a warning. Focused tests cover 3.1 pt and 2.0 pt. |
| Template placeholders could pass | **Closed for the specified tokens** | `find_latex_placeholders()` scans `TODO`, `TBD`, `待补充`, and `将在后续任务中补充`; compile and audit source gates reject matches. The template test passes. |
| Explicit negative paths and CLI integration were untested | **Closed** | The focused suite now covers missing PDF/AUX, unsafe main paths, placeholders, invalid label order, non-A4 output, nonzero/malformed/unavailable `pdfinfo`, fatal/undefined log diagnostics, both overfull thresholds, pending audit state, and build report integration. |
| Total/A4 evidence was discarded when labels were absent | **Closed** | `measure_pdf()` runs `pdfinfo` before AUX boundary validation and the regression test confirms total pages and A4 status survive a missing-label failure. |

## Remaining findings

### Important — real `pdfinfo` decoding can crash `measure_pdf`

`mathmodel-skill/scripts/mmcore/pdfmetrics.py:96` invokes `subprocess.run(..., text=True)` without an explicit encoding or decode-error policy. On the current Windows environment, the historical probe produced a `UnicodeDecodeError` in the subprocess reader. Because the exception occurs in the text-mode reader thread, the returned `CompletedProcess.stdout` was `None`; `pdfmetrics.py:105` then raised `TypeError` while applying `_PAGES_RE.search()`.

**Why:** The Task 5 contract requires unavailable, malformed, and tool-failure cases to produce controlled structured results. A real audit of the supplied historical PDFs currently crashes instead of returning `PENDING`/`FAILED` with a diagnostic, and the CLI can therefore fail without writing its intended quality result.

**Suggestion:** Invoke `pdfinfo` with a deterministic encoding and `errors="replace"` (or capture bytes and decode explicitly), normalize `stdout`/`stderr` to strings before regex/error handling, and add an integration regression with undecodable or absent subprocess output. The existing mocked tests only provide valid Unicode strings, so they do not exercise this platform boundary.

### Minor — placeholder enforcement is token-list based

The template no longer contains the exact release-blocking tokens tested by the implementation, but it still contains instructional scaffold prose such as “应根据题目材料” and “按实际来源补充”. This is not a remaining failure against the fix report’s explicit token list, but it means the detector does not generally prove that all placeholder-like prose has been removed.

**Suggestion:** If the broader design requirement “no placeholder text” is intended literally, define a documented allowlist/denylist for scaffold instructions or make scaffold-only text comments that cannot be compiled as paper content. Otherwise retain the current narrow contract and document it.

## Verdicts

### Spec-compliance verdict: FAIL

The required interfaces, release gates, placeholder checks, threshold behavior, evidence retention, and regression coverage are present. However, the live historical PDF verification exposes an uncaught `UnicodeDecodeError`/`TypeError` path in `measure_pdf`, violating the structured-failure requirement for PDF-tool interaction and preventing reliable audit behavior on this Windows environment.

### Task-quality verdict: FAIL

The implementation is readable and the focused/complete suites are green, with strong negative-case coverage. The unmocked `pdfinfo` boundary is still unsafe, and the test suite does not cover locale/decoding failure or `None` subprocess streams. The known symlink skip is environment-only and is not itself a task-quality defect.

## Disposition

- **Critical:** none.
- **Important:** one — make `pdfinfo` subprocess decoding and malformed/absent output fully controlled.
- **Minor:** one — clarify or broaden placeholder enforcement if the design intends to reject instructional scaffold prose.
- **Environment-only:** one known Windows symlink-permission skip (`WinError 1314`).

The prior release-gate findings are closed, but Task 5 fix3 should not be approved as fully complete until the Important `pdfinfo` decoding path is handled and covered by a regression test.
