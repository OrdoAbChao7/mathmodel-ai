---
name: mathmodel-skill
description: Use when creating, revising, modeling, or handling compile and quality-audit requests for CUMCM mathematical-modeling papers; working with contest data, reproducibility, LaTeX, or page-balance (正文/附录) evidence.
---

# MathModel-AI v2 — CUMCM Competition OS

Coordinate CUMCM paper work through traceable project artifacts. Treat the CLI as the source of deterministic checks and reserve mathematical judgment for documented human review.

For formal CUMCM work, use `competition_assisted` or `competition_max`; do not treat unattended generation followed by submission as the default workflow. The system is an evidence-and-governance pipeline, not a free-form paper generator.

## Start from the project state

1. Preserve original statements and raw attachments; inspect them without rewriting them.
2. Initialize a new project with `python mathmodel-skill/scripts/mathmodel.py init TARGET --id ID --title TITLE --type TYPE`, or adopt an existing one with `python mathmodel-skill/scripts/mathmodel.py adopt PROJECT`.
3. Inspect inputs before modeling: `python mathmodel-skill/scripts/mathmodel.py inspect PROJECT --json`.
4. Read [workflow.md](references/workflow.md), then read only the problem-type and delivery references required below.
5. Build a problem map before drafting equations, code, tables, or conclusions.

## Formal competition sequence

Run the stages in this order and stop at the human checkpoints:

```text
inspect → interpretation tournament → H1
→ model tournament/risk probe → H2
→ experiments → machine validation/falsification
→ cross-question coherence → H3
→ freeze → evidence-bound paper → independent reviews
→ H4 → submission → package
```

Use `mathmodel run PROJECT --profile cumcm --mode competition-max` only as an orchestrator for these governed stages. In formal modes it must block before build until H1/H2, before audit until H3, and before package until H4. A missing ledger, unresolved interpretation conflict, stale freeze, unsupported claim, open critical finding, or failed G9 check is a blocker—not a prose issue to explain away.

The four signoffs are substantive decisions: H1 locks objectives, constraints, outputs, and dependencies; H2 selects one justified route after baseline/diversity/risk comparison; H3 verifies numbers, figures, conclusions, and limitations against frozen evidence; H4 approves the final PDF, supporting materials, citations, anonymity, and AI-use detail. Never synthesize a signoff merely to make a gate pass.

## Use the CLI for deterministic evidence

Run the following commands from the repository root. Preserve their JSON output, generated reports, logs, and run manifests as evidence.

```powershell
python mathmodel-skill/scripts/mathmodel.py build PROJECT --json
python mathmodel-skill/scripts/mathmodel.py audit PROJECT --json
```

For a focused, read-only view of one stage, use `frame`, `screen`, `select`, `validate`, `freeze`, `review`, `signoff`, or `compliance` with the same `PROJECT --json` form. These commands reuse the audit evaluators and cannot independently release a submission.

Do not replace these checks with a prose assertion or a visual impression. Read the current `build/quality-report.json`, `build/quality-report.md`, page metrics, and `.mathmodel/runs/*/manifest.json` before claiming a result is reproducible, validated, or releasable.

## Maintain the evidence chain

Create and cross-link `problem-map`, `data-audit`, `model-registry`, `result-registry`, `claim-registry`, `figure-registry`, and `validation` artifacts. Assign stable IDs before using a number, figure, or conclusion in the paper. Require every important claim to cite a result ID and validation ID; reject an unsupported conclusion instead of softening it into an unverified claim.

Read [evidence-contracts.md](references/evidence-contracts.md) for required fields and repair rules. Read [figure-system.md](references/figure-system.md) before making publication figures.

## Write the body before the appendix

Put assumptions, definitions, derivations, main results, validation, limitations, and conclusions in the 正文. Put code listings, exhaustive tables, and supplementary derivations in the 附录 only after the body tells a complete evidence-backed story.

Require the LaTeX boundary labels `mm:body-start`, `mm:body-end`, `mm:appendix-start`, and `mm:appendix-end`. Record total, body, reference, and appendix page counts plus appendix/body ratio from the CLI. Reject a release when the body misses its configured target, the appendix/body ratio exceeds its configured limit, or core evidence exists only in the appendix. Repair imbalance with missing evidence, derivations, comparisons, error analysis, robustness, or interpretation; never pad with whitespace, repeated figures, or font changes.

Read [paper-architecture.md](references/paper-architecture.md) for the section contract and [quality-gates.md](references/quality-gates.md) for release-blocking rules.

## Route by problem type

| Need | Read |
|---|---|
| Choose stages, recover failures, or revise an existing project | [workflow.md](references/workflow.md) |
| Define artifact IDs, sources, and claim support | [evidence-contracts.md](references/evidence-contracts.md) |
| Plan the abstract, body, appendix, and page budget | [paper-architecture.md](references/paper-architecture.md) |
| Design common validation and robustness checks | [model-validation.md](references/model-validation.md) |
| Interpret audit output and manual release checks | [quality-gates.md](references/quality-gates.md) |
| Register and assess data, method, result, and validation figures | [figure-system.md](references/figure-system.md) |
| Forecast time-ordered outcomes | [forecasting.md](references/forecasting.md) |
| Allocate resources or solve constrained objectives | [optimization.md](references/optimization.md) |
| Rank alternatives or combine multiple indicators | [evaluation.md](references/evaluation.md) |
| Classification or class-imbalance modeling | [classification.md](references/classification.md) |
| Statistical inference or uncertainty analysis | [statistics.md](references/statistics.md) |
| Simulation, Monte Carlo, or queueing models | [simulation.md](references/simulation.md) |
| Mechanistic, physical, or differential-equation models | [mechanism.md](references/mechanism.md) |
| Multi-stage or mixed-type problems | [hybrid.md](references/hybrid.md) |
| Select a model family or document heuristic settings | [modeling-methods.md](references/modeling-methods.md) |
| Draft the abstract or per-question paper chain | [modeling-paper.md](references/modeling-paper.md) |
| Select CUMCM LaTeX packages, labels, or citation commands | [latex-template.md](references/latex-template.md) |
| Run a concise final writing and rendering checklist | [quality-checklist.md](references/quality-checklist.md) |
| Verify contest, literature, or citation support | [research-and-citation.md](references/research-and-citation.md) |

Use vendored CUMCM templates only as structural baselines. Read the supplied current contest notice for submission rules; do not copy vendored answers, data, or conclusions.

For `competition_max`, also provide `artifacts/competition-max-review.json` with the configured scout depth, route coverage, robustness attacks, red-team rounds, and a completed ARS review whose evidence path is an existing project-relative file. External providers may advise, but local evaluators alone decide PASS/FAIL.

## Validate before writing conclusions

Define variables, units, assumptions, data lineage, estimation method, algorithm settings, random seeds, and stopping rules. Select the simplest model that answers the stated question and record a baseline or a reason no baseline applies. Run the validation required by [model-validation.md](references/model-validation.md) and the selected problem-type reference before asserting accuracy, optimality, robustness, improvement, or significance.

Use `build` after changing analysis, registries, figures, LaTeX, or configuration. Use `audit` after editorial or page-balance revisions. Treat a CLI failure, broken ID link, missing source, unresolved reference, failed page gate, or stale report as a blocker, not as a warning to explain away.

Core JSON artifacts may use schema v1 (legacy) or v2 (current). For an explicit non-destructive preview, run `python mathmodel-skill/scripts/mathmodel.py migrate PROJECT --dry-run --json`; run it without `--dry-run` only when you intend to upgrade v1 JSON files. JSONL ledgers remain append-only and are not rewritten.

## Complete the manual review

Perform manual review after machine checks pass. Inspect the rendered PDF for clipped equations, unreadable tables, misleading axes, duplicate decorative figures, empty pages, broken citations, and body sections that merely point to appendix-only reasoning. Judge whether assumptions are defensible, the model answers each question, validation challenges the conclusion, citations support their claims, and recommendations remain within the model's scope.

Do not claim that a paper is ready to submit, award-worthy, correct, or reproducible until both CLI evidence and manual review are complete. State any unresolved boundary as a limitation and leave the release blocked.
