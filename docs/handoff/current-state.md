# Current State — OpenCode Handoff

This document is the factual entry point for a new agent. It records the repository after the final pre-training handoff preparation, not an aspirational roadmap.

## Repository checkpoint

- **Checkpoint date:** 2026-09-02
- **Branch:** `main`
- **HEAD at handoff preparation start:** `e95ab2823f82e9a5460eb4815ab8abab26a2d6a7` (`feat: expose bounded capability resolver CLI`)
- **Working tree at handoff preparation start:** no tracked or staged changes; pre-existing untracked `skill-dist/` was deliberately preserved and is not part of the public v2 core.
- **Stable baseline tag:** `pre-realcase-training-v1`, pointing to the last verified implementation commit `e95ab2823f82e9a5460eb4815ab8abab26a2d6a7`; the handoff-document commit is recorded separately in the repository history.

## Project positioning

The repository has evolved from a **Verifiable MathModel Paper Factory** into **MathModel-AI v2 — CUMCM Competition OS**. It is a local evidence and governance system around an external coding/modeling agent. It does not claim to guarantee an award, mathematical correctness, or citation correctness.

## Architecture phase audit

Statuses below describe the implementation that exists in the repository. `COMPLETE` means the local contract and evaluator are implemented and tested; it does not mean an external LLM runner or real historical corpus exists.

| Phase | Status | Evidence and boundary |
|---|---|---|
| Phase 0 — Authority & semantic safety | **COMPLETE** | `mathmodel-skill/CONSTITUTION.md`, `scripts/mmcore/authority.py`, `quality.py`, `schema.py`, capability/source registries, and explicit `UNASSESSED` semantics. |
| Phase 1 — Compliance + human governance | **COMPLETE** | `profiles/cumcm/`, `scripts/mmcore/compliance.py`, AI-use and human-review ledgers, H1–H4 enforcement, and formal-mode tests. |
| Phase 2 — Interpretation tournament | **COMPLETE** | `scripts/mmcore/interpretation.py`, `interpretation-candidates.json`/conflict contracts, G1 conflict blocking, and `test_interpretation.py`. |
| Phase 3 — Model tournament | **COMPLETE** | `scripts/mmcore/model_tournament.py`, candidate/method-card/risk/decision artifacts, diversity and complexity checks, and `test_model_tournament.py`. |
| Phase 4 — Semantic validation / falsification | **COMPLETE** | `experiment.py` and `semantic_validation.py` recompute provenance and validation outcomes, enforce problem-type evidence and falsification coverage, and are covered by `test_semantic_validation.py`. |
| Phase 5 — Cross-question coherence / freeze | **COMPLETE** | `architecture_freeze.py` checks dependencies, uncertainty propagation, frozen values, hashes, H3, and dependency-aware stale propagation. |
| Phase 6 — Paper / adversarial review | **MOSTLY_COMPLETE** | `paper_review.py`, `max_rigor.py`, quality judge-view scoring, claim/evidence checks, innovation review, and G8/G9 integration exist. A real blind judge and real-case reviewer corpus are not present. |
| Phase 7 — External capability boundaries | **COMPLETE** | `external_capabilities.py`, pinned source metadata, local ownership checks, read-only `capability` CLI, and no external gate authority. The providers are adapters/registries, not live external execution. |
| Phase 8 — Unified orchestration | **COMPLETE** | `orchestration/orchestrator.py` and `orchestration/time_budget.py` coordinate stages, resume, bounded retries, deadlines, stopping policy, and formal human checkpoints. |
| Phase 9 — Benchmark infrastructure | **MOSTLY_COMPLETE** | `benchmarks/` contains the isolated deterministic A/B harness, registry, metrics, promotion policy, CI smoke path, and synthetic fixtures. It does not yet contain private historical cases, a blind judge, or empirical LLM-agent comparisons. |

## Critical architecture boundary

`mathmodel run` is not the LLM modeling intelligence. The local orchestrator mainly coordinates:

```text
build
audit
package
resume
time budget
human checkpoints
```

The actual reading of a problem, modeling, code writing, experiments, result interpretation, and paper writing are performed by an external Agent following `mathmodel-skill/SKILL.md`. This boundary is intentional and is the central design premise for the future OpenCode Agent Runner.

## Current biggest gap

The largest missing capability is not another gate. It is the empirical loop:

```text
Real Agent Runner
+ Real Historical Case Corpus
+ Evidence-derived Evaluation
+ Failure-driven Learning
+ Locked Holdout Benchmark
```

The repository currently proves deterministic local contracts with synthetic fixtures. It does not yet prove that an external agent produces better mathematical models or papers on real CUMCM problems.

## Existing transition debt

The root contains historical `task-*.md` reports and the pre-existing untracked `skill-dist/` directory. They were not deleted or moved because their ownership and historical value were not safely inferable during handoff preparation. They are outside the canonical v2 implementation and should be reviewed separately.

## Baseline pointer

The immutable pre-training code baseline is the tag `pre-realcase-training-v1`, pointing at `e95ab2823f82e9a5460eb4815ab8abab26a2d6a7`. The handoff preparation itself is committed afterward as `7a8c58cd560619aeadf10afe5b8b0fedd6ca3951`. Future Phase 10 work must compare against the tag rather than against an assumed chat history.
