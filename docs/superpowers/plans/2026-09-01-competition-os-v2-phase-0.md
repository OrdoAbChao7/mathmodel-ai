# MathModel-AI v2 Phase 0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make authority, schema, source/capability, conflict, and `UNASSESSED` semantics explicit while preserving the existing evidence-chain pipeline.

**Architecture:** Add a small `authority` module and versioned JSON schemas beside the existing `mmcore` modules. Extend quality scoring with explicit assessment state and a fail-closed release rule; keep current artifact contracts and CLI commands backward compatible.

**Tech Stack:** Python 3.11+, standard library JSON/pathlib, unittest, existing `mathmodel` CLI.

**Spec:** `docs/superpowers/specs/2026-09-01-competition-os-v2-design.md`

## Global Constraints

- Phase 0 only; do not implement later tournament, human-gate, freeze, adapter, orchestrator, or benchmark phases.
- Existing projects and fixtures must remain compatible.
- Missing checks are `UNASSESSED` and never receive full machine credit.
- External capability output cannot override local gate results.
- Invalid schema or conflict records fail closed.

### Task 1: Lock the semantic failure with tests

**Files:**
- Modify: `mathmodel-skill/tests/test_quality.py`
- Create: `mathmodel-skill/tests/test_authority.py`

- [ ] Add tests asserting an empty check set returns `UNASSESSED`, score `0`, and non-PASS release status.
- [ ] Add tests for valid/invalid schema version, unresolved conflict, and external release status rejection.
- [ ] Run `python -m unittest mathmodel-skill.tests.test_quality mathmodel-skill.tests.test_authority` and verify failure is caused by missing behavior.

### Task 2: Implement authority and schema primitives

**Files:**
- Create: `mathmodel-skill/CONSTITUTION.md`
- Create: `mathmodel-skill/schemas/capability-registry.v1.json`
- Create: `mathmodel-skill/schemas/source-registry.v1.json`
- Create: `mathmodel-skill/scripts/mmcore/authority.py`

- [ ] Implement `load_json(path)`, `validate_schema_version(record, expected=1)`, `resolve_conflict(conflict)`, and `accept_external_status(status)` with standard-library-only checks.
- [ ] Return structured statuses `PASS`, `FAIL`, `UNASSESSED`, or `CONFLICT`; reject unknown versions and external `RELEASE=PASS` authority.
- [ ] Run the focused authority tests and confirm they pass.

### Task 3: Integrate fail-closed quality semantics

**Files:**
- Modify: `mathmodel-skill/scripts/mmcore/quality.py`

- [ ] Change machine scoring with no relevant checks to status `UNASSESSED` and score zero.
- [ ] Include `assessment_status`, `unassessed_dimensions`, and the new release-block reason in the result.
- [ ] Preserve manual score validation and all existing hard-failure behavior.
- [ ] Run the full suite and the training fixture.

### Task 4: Add authority diagnostics and compatibility checks

**Files:**
- Modify: `mathmodel-skill/scripts/mathmodel.py`
- Modify: `mathmodel-skill/tests/test_config.py`
- Modify: `mathmodel-skill/tests/test_end_to_end.py`

- [ ] Add a read-only `authority` CLI subcommand that reports constitution and registry status without changing project artifacts.
- [ ] Keep existing subcommands and JSON output fields compatible.
- [ ] Run `build`, `audit`, and `package` on `traning1`, then run all tests.

### Task 5: Verify and commit Phase 0

- [ ] Run focused tests, full tests, fixture build/audit/package, and negative release cases.
- [ ] Inspect reports and confirm no external status can override local status.
- [ ] Commit with `feat: add phase 0 authority semantics`.
