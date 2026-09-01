# MathModel-AI v2 Phase 0 Design

**Goal:** Add an authority and semantic-safety layer without replacing the trusted `mmcore` pipeline.

**Scope:** Phase 0 only. Add explicit schema versioning, a local constitution, capability/source registries, conflict-policy semantics, and `UNASSESSED` quality semantics. Preserve all existing project commands and evidence-chain behavior.

## Decisions

1. Existing artifact validation remains the source of truth for current projects. New metadata is additive and defaults conservatively.
2. A quality dimension with no applicable machine checks is `UNASSESSED`, scores zero for machine scoring, and cannot produce a release `PASS` by itself.
3. External capabilities are advisory records. They cannot change local gate outcomes or emit a trusted release status.
4. Schema versions are explicit integers. Unsupported versions fail closed with a clear diagnostic.
5. Conflicts are recorded, never silently resolved: `UNASSESSED` is the safe status until a declared policy and human decision resolve them.
6. The constitution is a checked-in text policy and the registries are JSON with deterministic shape checks. No database or web UI is introduced.

## Components

- `mathmodel-skill/CONSTITUTION.md`: local authority, provenance, human ownership, and release principles.
- `mathmodel-skill/schemas/`: versioned JSON schemas for capability and source records.
- `mathmodel-skill/scripts/mmcore/authority.py`: load/validate policy and registry records; normalize assessment statuses.
- `mathmodel-skill/scripts/mmcore/quality.py`: return `UNASSESSED` dimensions and block false full scores.
- `mathmodel-skill/scripts/mathmodel.py`: expose read-only `authority` diagnostics without changing build/audit contracts.
- `mathmodel-skill/tests/`: red/green tests for missing checks, unknown schema, conflicts, and external PASS rejection.

## Competition-facing score view

The internal eight-dimension score remains the compatibility and release-gate score. For CUMCM review, the quality report additionally emits `official_judge_view` with four weighted dimensions: modeling reasonableness (30), modeling creativity (20), result correctness and trust (30), and communication clarity (20). Each entry retains its assessment status and the internal evidence dimensions used to form it. This is a diagnostic projection only; it cannot override hard failures, missing human signoffs, or other release gates. Modeling creativity is deliberately `UNASSESSED` unless the governed innovation-review layer supplies explicit, evidence-backed assessment.

## Non-goals

Do not implement human H1-H4 ledgers, model tournaments, validators, freeze manifests, adapters, benchmark harnesses, or a unified `run` command in Phase 0.

## Acceptance

- Existing 108-test baseline remains green.
- Empty or irrelevant checks produce `UNASSESSED`, not a full machine score.
- A quality report with unassessed dimensions cannot be `PASS`.
- Invalid registry/schema/conflict records fail closed.
- External capability records are never accepted as local release authority.
- `training1` continues to build/audit with unchanged result semantics.
