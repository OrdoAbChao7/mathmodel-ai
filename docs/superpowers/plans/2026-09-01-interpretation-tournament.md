# Interpretation Tournament Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a profile-driven Interpretation Tournament and G1 gate without breaking v1 research projects.

**Architecture:** A pure `mmcore.interpretation` evaluator reads three project artifacts and the CUMCM profile, recomputes semantic conflicts, and returns structured gate evidence. The existing CLI remains the orchestration entry point; audit/build add the G1 gate and package rechecks formal reports.

**Tech Stack:** Python 3.11+, JSON, YAML profile files, `unittest`, existing `mathmodel.py` CLI.

**Spec:** `docs/superpowers/specs/2026-09-01-interpretation-tournament-design.md`

## Global Constraints

- Keep `mathmodel-skill/scripts/mmcore/` as the implementation location.
- Existing v1 fixtures and undeclared research mode remain compatible.
- Formal CUMCM modes fail closed on missing or fabricated interpretation evidence.
- Machine-computed status, not agent-supplied status, determines G1.
- Use project-relative artifact references and do not execute artifact content.
- Every production behavior is introduced by a failing test first.

---

### Task 1: Interpretation evaluator contract

**Files:**
- Create: `mathmodel-skill/tests/test_interpretation.py`
- Create: `mathmodel-skill/scripts/mmcore/interpretation.py`
- Modify: `mathmodel-skill/profiles/cumcm/profile.yaml`

**Interfaces:**
- Consumes: project root, config dictionary, and H1 review records from `artifacts/human-review-ledger.jsonl`.
- Produces: `evaluate_g1(project: Path, config: dict[str, Any]) -> dict[str, Any]` with `status`, `gate`, `checks`, `conflicts`, `missing_artifacts`, and profile provenance.

- [ ] **Step 1: Write failing tests** for missing candidates, malformed records, major conflict, resolved conflict, forged status, missing H1 linkage, valid evidence, and research mode.
- [ ] **Step 2: Run the focused tests** and confirm failure because `mmcore.interpretation` is absent.
- [ ] **Step 3: Implement the smallest evaluator** with JSON shape checks, normalized set comparison, deterministic conflict IDs, and H1 artifact-link verification.
- [ ] **Step 4: Run focused tests** and confirm all evaluator cases pass.
- [ ] **Step 5: Commit** with `feat: add interpretation tournament evaluator`.

### Task 2: CLI G1 gate integration

**Files:**
- Modify: `mathmodel-skill/scripts/mathmodel.py`
- Modify: `mathmodel-skill/scripts/mmcore/package.py`
- Modify: `mathmodel-skill/tests/test_release_audit.py`
- Modify: `mathmodel-skill/tests/test_latex_metrics.py` if CLI report assertions require it

**Interfaces:**
- Consumes: `evaluate_g1` and formal-mode/profile policy.
- Produces: `G1-PROBLEM-INTERPRETATION-001` in formal audit/build reports and `PACKAGE-INTERPRETATION-001` for formal package failures.

- [ ] **Step 1: Write failing integration tests** for formal audit/build G1 failure and formal package missing G1.
- [ ] **Step 2: Run those tests** and confirm the current CLI/package can incorrectly pass.
- [ ] **Step 3: Add G1 to report and release gates** while leaving research mode `NOT_APPLICABLE`.
- [ ] **Step 4: Run focused integration tests** and confirm fail-closed behavior.
- [ ] **Step 5: Commit** with `feat: enforce G1 interpretation gate`.

### Task 3: Verification and delivery

**Files:**
- No additional production files unless a test exposes a scoped defect.

- [ ] **Step 1: Run `python -m unittest discover -s mathmodel-skill/tests -p 'test_*.py'`.**
- [ ] **Step 2: Run build, audit, and package for `traning1`.**
- [ ] **Step 3: Inspect reports for G1 and confirm research compatibility.**
- [ ] **Step 4: Run `git diff --check` and review the complete branch diff.**
- [ ] **Step 5: Merge the reviewed branch into `main` and push both branch state and the merge to `origin`.**
