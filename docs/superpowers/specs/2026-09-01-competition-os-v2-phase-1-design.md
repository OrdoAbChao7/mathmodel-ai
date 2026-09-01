# MathModel-AI v2 Phase 1 Design

**Goal:** Add a data-driven CUMCM compliance layer and human governance gates without allowing scores or external adapters to substitute for human signoff.

## Mode boundary

`research_autonomous` is the backward-compatible default when a project does not declare `execution_mode`. `competition_assisted` and `competition_max` are formal modes and require G0 plus H1, H2, H3, and H4. The mode is stored in `mathmodel.json`; contest rules are stored in `profiles/cumcm/*.yaml`, not hard-coded in gate logic.

## Artifacts

- `artifacts/ai-usage-ledger.jsonl`: one JSON object per AI contribution, with model, purpose, stage, prompt hash, output artifacts, acceptance, human modification/verification, and review ID. Sensitive tokens are rejected.
- `artifacts/human-review-ledger.jsonl`: one JSON object per human gate decision, with gate, artifacts reviewed, reviewer identity/role, timestamp, decision, and evidence notes.
- `profiles/cumcm/profile.yaml`, `official-rules.yaml`, `paper-rules.yaml`, `ai-rules.yaml`, `gate-overrides.yaml`: versioned rule sources with effective date, title, verification timestamp, and required gate configuration.

## Gate behavior

The compliance evaluator returns structured checks and a status. Formal mode fails when any ledger is missing, malformed, incomplete, stale, or contains an unapproved H1–H4 gate. Research mode reports the gates as not applicable and preserves legacy build behavior. Package consumes the same report and never recomputes a weaker interpretation.

Each formal human record must also reference a non-empty set of existing project-relative artifacts. This prevents a signoff from claiming review of nonexistent files or from using absolute/path-traversal references; invalid references produce a blocking integrity check.

## Non-goals

Do not implement model tournaments, freeze manifests, falsification, adapters, benchmark harnesses, or the unified orchestrator in Phase 1.
