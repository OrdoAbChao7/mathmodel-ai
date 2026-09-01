# Semantic Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement machine-computed G4 validation and falsification-first G5 gates.

**Architecture:** A pure `mmcore.semantic_validation` evaluator reads validation and falsification artifacts, computes comparison outcomes locally, checks problem-type semantic evidence from the profile, and returns structured G4/G5 results. The existing CLI and package remain the only release authorities.

**Tech Stack:** Python 3.11+, JSON, YAML profiles, `unittest`, existing `mathmodel.py` CLI.

**Spec:** `docs/superpowers/specs/2026-09-01-semantic-validation-design.md`

## Global Constraints

- Keep implementation in `mathmodel-skill/scripts/mmcore/`.
- Existing v1 projects and research mode remain compatible.
- Formal gates fail closed on missing, malformed, stale, or path-unsafe evidence.
- Agent-provided aggregate status fields never determine gate outcomes.
- Every production behavior is preceded by a failing test.

---

### Task 1: Machine validation evaluator

**Files:**
- Create: `mathmodel-skill/tests/test_semantic_validation.py`
- Create: `mathmodel-skill/scripts/mmcore/semantic_validation.py`
- Modify: `mathmodel-skill/profiles/cumcm/profile.yaml`

**Interfaces:**
- Consumes: project root and config dictionary.
- Produces: `evaluate_semantic_validation(project: Path, config: dict[str, Any]) -> dict[str, Any]` with `g4`, `g5`, `status`, and profile provenance.

- [ ] **Step 1: Write failing tests** for numeric computation, semantic requirements, falsification outcomes, malformed evidence, and research mode.
- [ ] **Step 2: Run focused tests** and confirm the evaluator module is absent.
- [ ] **Step 3: Implement path-safe loading, operator computation, profile-driven semantic checks, and attack coverage.**
- [ ] **Step 4: Run focused tests** and confirm all cases pass.
- [ ] **Step 5: Commit** with `feat: add semantic validation evaluator`.

### Task 2: G4/G5 CLI and package integration

**Files:**
- Modify: `mathmodel-skill/scripts/mathmodel.py`
- Modify: `mathmodel-skill/scripts/mmcore/package.py`
- Modify: `mathmodel-skill/tests/test_latex_metrics.py`
- Modify: `mathmodel-skill/tests/test_release_audit.py`

**Interfaces:**
- Consumes: `evaluate_semantic_validation`.
- Produces: `G4-SEMANTIC-VALIDATION-001`, `G5-FALSIFICATION-001`, and `PACKAGE-VALIDATION-001`.

- [ ] **Step 1: Write failing integration tests** for formal reports and packages without G4/G5 evidence.
- [ ] **Step 2: Run those tests** and confirm current CLI/package can pass without semantic evidence.
- [ ] **Step 3: Add report fields and hard gates** while preserving research mode.
- [ ] **Step 4: Run focused integration tests.**
- [ ] **Step 5: Commit** with `feat: enforce G4 and G5 validation gates`.

### Task 3: Verification and delivery

**Files:**
- No additional production files unless a scoped verification defect is found.

- [ ] **Step 1: Run the complete test suite.**
- [ ] **Step 2: Run `traning1` build/audit/package.**
- [ ] **Step 3: Run `git diff --check` and review the branch diff.**
- [ ] **Step 4: Request independent code review and fix Critical/Important findings.**
- [ ] **Step 5: Merge into `main` and push both feature and main branches.**
