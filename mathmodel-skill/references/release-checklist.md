# Release checklist

Run `inspect`, `build`, and `audit` on a clean project. Package only when the machine report is `PASS`, the quality score meets its configured minimum, manual review is `COMPLETE`, page metrics distinguish body/reference/appendix pages, and every hard gate is `PASS`.

The package command copies the current project-contained PDF and records its SHA-256, page count, source snapshot, validation report, quality report, and reproducibility summary. A pending or failed gate blocks packaging; total pages never substitute for body pages.
