# Quality Gates

Run `build PROJECT --json` to generate evidence and `audit PROJECT --json` to assess the current artifacts. Treat the following as release blockers: invalid configuration or escaped paths, missing inputs, failed analysis, invalid JSON, broken IDs, untraceable results, unsupported claims, failed validation, unresolved LaTeX references, missing PDF boundaries, body-page shortfall, excessive appendix/body ratio, release-blocking placeholders, or incomplete manual review.

Require no hard failures and the configured score threshold. Interpret soft score dimensions as problem coverage, data traceability, model rigor, validation, result/claim evidence, body expression, figures, and LaTeX quality; do not let a score compensate for a hard failure.

Inspect the current quality report rather than quoting an earlier one. Repair the cited rule, file, or registry path, then rerun the relevant CLI command. Preserve WARN items for manual review, including overfull content, low-resolution figures, unreadable black-and-white figures, unused citations, excessive whitespace, and section imbalance.
