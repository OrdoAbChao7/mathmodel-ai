# Model Tournament Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement profile-driven G2/G3 model-search and selection gates.

**Architecture:** A pure `mmcore.model_tournament` evaluator reads candidate, method-card, risk-probe, and decision-ledger artifacts. It recomputes candidate coverage and conceptual diversity, validates risk fields and selection provenance, and returns structured G2/G3 evidence. The existing CLI and package remain the only release authorities.

**Tech Stack:** Python 3.11+, JSON/JSONL, YAML profiles, `unittest`, existing `mathmodel.py` CLI.

**Spec:** `docs/superpowers/specs/2026-09-01-model-tournament-design.md`

## Global Constraints

- Keep implementation in `mathmodel-skill/scripts/mmcore/`.
- Existing v1 fixtures and research mode remain compatible.
- Formal modes fail closed on missing or malformed model-search evidence.
- Candidate diversity is conceptual, not merely algorithm-name diversity.
- Machine checks ignore agent-authored aggregate status fields.
- Every behavior change has a failing test before production code.

---

### Task 1: Model tournament evaluator

**Files:**
- Create: `mathmodel-skill/tests/test_model_tournament.py`
- Create: `mathmodel-skill/scripts/mmcore/model_tournament.py`
- Modify: `mathmodel-skill/profiles/cumcm/profile.yaml`

**Interfaces:**
- Consumes: project root and config dictionary.
- Produces: `evaluate_model_tournament(project: Path, config: dict[str, Any]) -> dict[str, Any]` with `g2`, `g3`, `status`, `checks`, and profile provenance.

- [ ] **Step 1: Write failing tests** for coverage, baseline, diversity, risk, method cards, selection, H2 linkage, forged status, and research mode.
- [ ] **Step 2: Run focused tests** and confirm the evaluator module is absent.
- [ ] **Step 3: Implement deterministic validation and recomputation.**
- [ ] **Step 4: Run focused tests** and confirm all evaluator cases pass.
- [ ] **Step 5: Commit** with `feat: add model tournament evaluator`.

### Task 2: G2/G3 CLI and package integration

**Files:**
- Modify: `mathmodel-skill/scripts/mathmodel.py`
- Modify: `mathmodel-skill/scripts/mmcore/package.py`
- Modify: `mathmodel-skill/tests/test_release_audit.py`
- Modify: `mathmodel-skill/tests/test_latex_metrics.py`

**Interfaces:**
- Consumes: `evaluate_model_tournament`.
- Produces: `G2-MODEL-SEARCH-001`, `G3-MODEL-SELECTION-001`, `PACKAGE-MODEL-TOURNAMENT-001`.

- [ ] **Step 1: Write failing integration tests** for formal audit and package without G2/G3.
- [ ] **Step 2: Run those tests** and confirm current CLI/package can pass without model-search evidence.
- [ ] **Step 3: Add G2/G3 reports and hard gates** with research-mode compatibility.
- [ ] **Step 4: Run focused integration tests.**
- [ ] **Step 5: Commit** with `feat: enforce G2 and G3 model gates`.

### Task 3: Verification and delivery

**Files:**
- No additional production files unless a scoped verification defect is found.

- [ ] **Step 1: Run the complete test suite.**
- [ ] **Step 2: Run `traning1` build/audit/package.**
- [ ] **Step 3: Review the branch diff and run `git diff --check`.**
- [ ] **Step 4: Request independent code review and fix Critical/Important findings.**
- [ ] **Step 5: Merge into `main` and push feature and main branches.**
