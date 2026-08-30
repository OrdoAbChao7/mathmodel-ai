# Task 7 Fix 3 Report — Prepared-fixture CLI replay boundary

## Scope

Strengthen the temporary replay tests to load registry JSON and assert representative IDs and cross-links directly. Name the harness `prepare_fixture_cli_replay` to state its purpose precisely: prepare deterministic registry inputs for direct CLI audit coverage.

## Evidence boundary

The prepared-fixture CLI replay harness invokes `init`, `inspect`, `audit`, and, in the page scenario, `build` in a temporary directory. It does not execute a prompt through an agent and is not prompt-to-agent registry production. No agent execution harness is available for this Task 7 turn, and agent dispatch is explicitly prohibited. These tests certify CLI handling of prepared evidence contracts and page metrics, not autonomous Skill behavior.

## Direct registry assertions

Each replay now loads all seven JSON files:

```text
problem-map.json, data-audit.json, model-registry.json,
result-registry.json, claim-registry.json, figure-registry.json,
validation.json
```

Optimization asserts the prepared chain `Q-OPT-1 → M-OPT-1`, `R-OPT-1`, `V-OPT-1`, and `C-OPT-1 → R-OPT-MISSING/V-OPT-1`; all figures link to `C-OPT-1`. Forecasting makes the corresponding `Q-FOR-1`, `M-FOR-1`, `R-FOR-1`, `C-FOR-1 → R-FOR-MISSING/V-FOR-1`, and `V-FOR-1` assertions. Page balance asserts the valid chain `Q-PAGE-1 → M-PAGE-1`, `R-PAGE-1`, `C-PAGE-1 → R-PAGE-1/V-PAGE-1`, and `V-PAGE-1`; all page figures link to `C-PAGE-1`.

The two intentionally missing result IDs are what cause the actual `audit --json` reports to contain failed `EVIDENCE-CLAIM-001`. The valid page chain allows the test to isolate page failures: `PAGE-BODY-001` and `PAGE-APPENDIX-001` are asserted from generated `quality-report.json`.

## Optional build coverage

The page prepared fixture also invokes `build PROJECT --json` before replacing its output with the controlled 32-page A4 PDF and `.aux` used for the page-gate audit. On this host, the minimal prepared fixture returns a structured compile failure; the test records that the CLI emits `compile.status` and `page_metrics.status` rather than claiming a successful paper build. This optional invocation adds route coverage only and is not evidence of a complete model, paper, or agent workflow.

## TDD and validation

Added the direct registry assertions and the Fix 3 report-contract test first. The focused suite was red only because this report did not yet exist. After adding the report and precision wording, rerun the package validator, focused assets, and the full suite.
