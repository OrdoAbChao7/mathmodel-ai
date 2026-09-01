# CUMCM MathModel Paper Factory

This project provides a reproducible workflow for producing and auditing mathematical-modeling contest papers. It includes a reusable `mathmodel-skill`, deterministic CLI checks, evidence registries, solver/analysis runners, LaTeX page-balance gates, end-to-end fixtures, a competition-max benchmark, and release packaging rules.

Supported problem profiles are `forecasting`, `optimization`, `evaluation`, `mechanism`, `simulation`, `classification`, `statistics`, and `hybrid`. The classification and statistics profiles include dedicated validation requirements and writing references; unsupported types fail during configuration loading.

## Quick start

```text
python mathmodel-skill/scripts/mathmodel.py init <project> --id <id> --title <title> --type optimization
python mathmodel-skill/scripts/mathmodel.py inspect <project> --json
python mathmodel-skill/scripts/mathmodel.py build <project> --json
python mathmodel-skill/scripts/mathmodel.py audit <project> --json
python mathmodel-skill/scripts/mathmodel.py package <project> --json
python mathmodel-skill/scripts/mathmodel.py run <project> --json
# one-run formal profile/mode override (does not rewrite mathmodel.json)
python mathmodel-skill/scripts/mathmodel.py run <project> --profile cumcm --mode competition-max --json
# initialize a formal project (creates a checklist, never fake signoffs)
python mathmodel-skill/scripts/mathmodel.py init <project> --id ID --title TITLE --type hybrid --profile cumcm --mode competition-assisted
```

The same pipeline stages are available as read-only diagnostics: `frame`, `screen`, `select`, `validate`, `freeze`, `review`, `signoff`, and `compliance`. They reuse the evaluators used by `audit`; they do not create an alternate release path.

Use `mathmodel migrate PROJECT --dry-run --json` to preview v1 core-artifact migrations, or omit `--dry-run` to upgrade v1 JSON files under `artifacts/` to v2. JSONL ledgers are intentionally not rewritten; their append-only history remains intact.

The package command blocks unresolved manual review, missing evidence, failed quality/page gates, stale or missing PDFs, and absent hashes. Total PDF pages never substitute for substantive body pages.

In formal competition modes, `run` is human-checkpoint aware: it blocks before `build` until H1 and H2 are signed, before `audit` until H3 is signed, and before `package` until H4 is signed. The block is reported as `BLOCKED_HUMAN_INPUT`; research mode keeps the legacy autonomous orchestration behavior.

The `--profile cumcm` and `--mode` options are per-run overrides. They never rewrite the project configuration; accepted modes are `research-autonomous`, `competition-assisted`, and `competition-max`. The orchestrator propagates the selected mode to each child `build`, `audit`, and `package` stage, so a formal override cannot silently fall back to the on-disk research mode.

`init` and `adopt` accept the same profile/mode selection for new project metadata and create `CUMCM-WORKFLOW.md`. Existing files and existing configuration are preserved; no human-review ledger is synthesized by scaffolding.

Formal human-review records are also evidence-bound: every `reviewed_artifacts` path must be a project-relative, existing file. Absolute paths, path traversal, missing files, stale timestamps, and rejected decisions cannot satisfy a checkpoint.

AI-use records are evidence-bound in the same way: every `output_artifacts` entry must point to an existing project-local file, and `accepted`, `human_modified`, and `human_verified` must be real Boolean fields. This prevents a ledger from claiming review of an artifact that was never produced.

The deterministic regression fixtures are under `mathmodel-skill/tests/fixtures/`, and the independent `competition_max` integration fixture is under `benchmarks/cases/formal-max-fixture/`. The real `traning1` project is an integrated example: its configured build runs `solve.py`, `enhance.py`, the LaTeX compiler, page-balance gates, evidence checks, and release packaging. The repository retains a previous verified output record of 38 total pages, 32 body pages, and 3 appendix pages; rerunning that verification requires a functioning local TeX installation.

On this Windows workspace the example uses the bundled Python runtime path in `traning1/mathmodel.json`, because the system Python does not include the numerical and plotting dependencies required by `solve.py`. When moving the project to another machine, replace that interpreter path with a Python environment containing NumPy, SciPy, Matplotlib, and OpenPyXL.

## Execution and rigor modes

`execution_mode` controls whether competition gates are active: `research_autonomous` reports competition-only gates as not applicable, while `competition_assisted` and `competition_max` require the formal evidence and human-signoff chain.

`rigor` controls only model-tournament search breadth and defaults to `standard`:

- `fast`: at least one baseline and one alternative route, suitable for time-limited exploration;
- `standard`: the CUMCM profile defaults (four total candidates and three non-baseline routes);
- `max`: uses the configured profile limits and preserves the broadest configured review budget.

All three modes retain the same risk-probe, leakage, validation, reproducibility, citation, AI-ledger, and human-gate requirements. The selected mode and effective limits are recorded in the G2/G3 report for auditability.

New projects use configuration schema v2. Existing v1 configurations are accepted and normalized in memory without modifying the original file, preserving backward compatibility with historical fixtures and training projects.

Formal G8 review also requires an independent innovation assessment backed by result/validation references; using a newer algorithm alone is not treated as innovation.

`competition_max` additionally requires `artifacts/competition-max-review.json`, documenting unique structured records for at least two model scouts, four candidate routes, three typed robustness attacks, two red-team rounds, and a completed ARS review. Counts and attack coverage are derived from those records rather than trusted as free-standing integers or names. `competition_assisted` does not require this extension artifact.

Formal validation also requires `artifacts/experiment-registry.json`; its records bind runs to code, inputs, configuration, seed, environment, metrics, figures, and result artifacts, with hashes recomputed by the local evaluator.

At G9, release hash entries are independently recomputed against current project files; a forged `PASS`, stale digest, duplicate path, or unsafe path blocks submission.

G9 also binds the quality report to its current source manifest and reproducibility summary, including the current configuration hash.

The quality report exposes two complementary scorecards. `dimensions` preserves the eight-dimensional internal gate score used for release decisions and reports explicit assessment states: `ASSESSED_PASS`, `ASSESSED_FAIL`, `UNASSESSED`, or `NOT_APPLICABLE`. `official_judge_view` maps the same evidence into the four CUMCM-facing dimensions—modeling reasonableness (30), modeling creativity (20), result correctness and trust (30), and communication clarity (20). The mapping is diagnostic and does not weaken hard gates. In particular, creativity remains `UNASSESSED` until an innovation-specific, evidence-backed human assessment is recorded; algorithm names or polished prose are not treated as innovation proof.
