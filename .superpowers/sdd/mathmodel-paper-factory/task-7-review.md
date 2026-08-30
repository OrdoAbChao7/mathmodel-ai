# Task 7 Independent Review

## Review scope

Reviewed the current Task 7 package, brief, report, plan/spec context, `mathmodel-skill/SKILL.md`, `agents/openai.yaml`, all files under `mathmodel-skill/assets/`, all files under `mathmodel-skill/references/`, and `mathmodel-skill/tests/test_skill_assets.py`. Also checked the local Skill Creator/OpenAI interface guidance and ran the requested validation commands.

No source, test, asset, or implementation file was edited. This review was performed in the current non-Git workspace without dispatching subagents.

## Summary

The Task 7 Skill is concise, readable, and well aligned with the main coordination contract. It has a searchable `Use when...` description, explicitly routes deterministic checks through the CLI, requires traceable evidence and separate body/reference/appendix metrics, and clearly leaves mathematical, visual, and submission-readiness judgment to manual review. The nine Task 7 references, template assets, and OpenAI interface metadata are present and internally consistent.

The main weakness is verification depth, not the Skill prose itself. The four asset tests mostly assert literal strings and file existence; they do not parse the YAML, validate reference content/routing, exercise the CLI route, or test unsupported-claim/body-metric/manual-review behavior. The report's three forward tests are useful scenario summaries, but they contain no prompt transcripts, command output, or generated evidence artifacts, so the claims cannot be independently reproduced from the repository.

## Verdicts

### Spec-compliance verdict: PASS with minor documentation/routing gap

The owned Task 7 deliverables satisfy the explicit acceptance requirements that can be verified from the current files:

- `SKILL.md` is 69 lines, below the 500-line limit.
- Front matter uses the required searchable `description: Use when...` form and includes CUMCM paper/revision/modeling/LaTeX/data/reproducibility/page-balance/quality-audit/compile vocabulary.
- The Skill requires CLI evidence, stable registry IDs, validation support, body/reference/appendix/total page metrics, appendix/body ratio checks, and manual review boundaries.
- All nine required Task 7 references exist and are linked from the Skill's routing table.
- `agents/openai.yaml` uses only `display_name`, `short_description`, and `default_prompt`; its default prompt explicitly names `$mathmodel-skill`.
- The requested validation commands pass, with only the documented environment-only symlink skip.
- The report records optimization, forecasting, and body/appendix imbalance forward scenarios and the intended unsupported-claim outcomes.

The qualification is that five other existing reference files (`latex-template.md`, `modeling-methods.md`, `modeling-paper.md`, `quality-checklist.md`, and `research-and-citation.md`) are not linked or routed by `SKILL.md`. They are not among the nine Task 7-created references, so this does not invalidate the owned-file contract, but it leaves useful existing resources undiscoverable through the Skill.

### Task-quality verdict: NEEDS IMPROVEMENT before treating validation as strong

The implementation is likely usable and the complete suite is green, but the Task 7-specific evidence is weaker than the acceptance language suggests. Passing tests demonstrate the expected text and paths, not that another agent can reliably follow the Skill in the three forward scenarios or that the metadata/reference contracts are semantically valid. Strengthening the tests and preserving minimal forward-test traces would materially improve confidence without expanding the Skill body.

## Findings

### 🟡 Important — Task 7 asset tests are too shallow for the acceptance surface

`mathmodel-skill/tests/test_skill_assets.py:43-81` checks front-matter and body requirements through substring assertions, discovers only Markdown links, checks the nine expected paths, and extracts YAML keys by looking at indented lines. It does not parse YAML, verify that all reference files intended for discovery are routed, inspect required CLI command names, validate the body/appendix metric wording, or exercise the unsupported-claim/manual-review rules.

**Why:** A materially incomplete Skill can remain green by retaining the expected keywords. For example, a malformed quoted value, a stale route target, or a prose change that mentions “manual review” without defining a release boundary would not be caught. This makes the four focused tests a weak proxy for the broader acceptance requirements.

**Suggestion:** Keep the lightweight text tests, but add focused semantic checks: parse `openai.yaml` with the available YAML parser or a constrained parser, assert every intended reference target exists and is routed, assert the required CLI subcommands and boundary labels are present, and test representative rejection phrases/conditions for unsupported optimality/accuracy claims and body-vs-total page confusion. These can remain read-only asset tests.

### 🟡 Important — Forward-test records are not independently reproducible

`task-7-report.md` records three prompts and expected outcomes in a table, but provides no exact walkthrough transcript, CLI stdout/stderr, registry snapshots, or immutable test fixture. The report says the walkthroughs were performed, yet a reviewer cannot distinguish actual CLI/tool execution from an interpretation of the Skill text.

**Why:** Acceptance requirement 7 asks to record whether the Skill invokes the CLI, creates registries, and rejects unsupported claims. A narrative assertion records the conclusion but not the evidence needed to audit it. This is especially relevant because the Skill is a coordination asset whose quality depends on behavior under realistic prompts, not only on static wording.

**Suggestion:** Preserve a compact forward-test record for each scenario containing the exact prompt, selected route, representative command invocations/output, registry names/IDs expected or observed, and the blocked claim. Use isolated temporary projects or a non-mutating transcript fixture so production files remain untouched.

### 💭 Minor — Existing useful references are not discoverable through the Skill

The reference directory contains `latex-template.md`, `modeling-methods.md`, `modeling-paper.md`, `quality-checklist.md`, and `research-and-citation.md`, but the Skill routes only the nine Task 7 references (`SKILL.md:45-55`).

**Why:** An agent following the Skill has no direct route to the LaTeX, method-selection, paper-structure, checklist, or citation guidance even though those files are present and relevant to the requested workflow. This can lead to duplicated guidance or inconsistent use of the existing material.

**Suggestion:** Either add concise rows for these existing resources to the route table, or explicitly document that they are legacy/non-routed resources and why. If they are intentionally out of Task 7 scope, record that boundary in the review/report rather than leaving silent dead documentation.

## What is good

- The Skill's core principle is clear: deterministic state belongs to the CLI, while mathematical and visual judgment remains documented human review (`SKILL.md:8`, `65-69`).
- Evidence discipline is concrete rather than aspirational: stable IDs, source paths, result/validation support, and rejection of unsupported conclusions are stated directly (`SKILL.md:29-33`, `59-63`).
- The body/appendix guidance correctly prevents total page count from substituting for body content and explicitly rejects padding, repeated figures, and font changes (`SKILL.md:35-41`).
- Problem-type routing is concise and maps optimization, forecasting, and evaluation to dedicated references (`SKILL.md:43-55`).
- The template exposes executable page-boundary labels and keeps the analysis adapter visibly unconfigured instead of pretending to provide a solver.
- All requested fresh validation commands passed; the single skip is consistent with the documented Windows symlink privilege limitation.

## Validation evidence

```text
python D:/Dev/.codex/skills/.system/skill-creator/scripts/quick_validate.py mathmodel-skill
Skill is valid!

python -m unittest mathmodel-skill.tests.test_skill_assets -v
Ran 4 tests ...
OK

python -m unittest discover -s mathmodel-skill/tests -v
Ran 84 tests in 2.649s
OK (skipped=1)
```

The skipped test is `test_out_of_root_recognized_symlink_is_warned_or_skipped`, skipped because the current Windows user lacks symlink privilege (`WinError 1314`). No other test failed or skipped.

## Recommended next steps

1. Add semantic asset-contract tests and one or more isolated forward-test transcripts.
2. Decide whether the five existing reference files are part of the supported Skill surface; route them or document their exclusion.
3. Keep the current Skill prose and metadata structure; no broad rewrite is warranted based on this review.

