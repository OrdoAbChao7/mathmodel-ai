# MathModel-AI v2 Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce CUMCM compliance and H1–H4 human governance in explicit competition modes.

**Architecture:** Store rule data in YAML profiles and evaluate project JSONL ledgers through a single `compliance` module. Integrate its result into build, audit, and package release gates while defaulting undeclared legacy projects to research mode.

**Tech Stack:** Python 3.11+, PyYAML, JSONL, unittest, existing `mathmodel` CLI.

**Spec:** `docs/superpowers/specs/2026-09-01-competition-os-v2-phase-1-design.md`

## Global Constraints

- Formal modes are `competition_assisted` and `competition_max`.
- Formal modes require G0, H1, H2, H3, and H4.
- Missing or malformed ledgers fail closed.
- AI ledgers must not contain API keys or tokens.
- External output cannot change local compliance status.
- Legacy projects without `execution_mode` remain compatible as research mode.

### Task 1: Write failing compliance tests

**Files:** `mathmodel-skill/tests/test_compliance.py`, `mathmodel-skill/tests/test_runner_analysis.py`

- [ ] Test formal mode with missing ledgers returns `FAIL` and lists H1–H4.
- [ ] Test valid JSONL ledgers return `PASS`.
- [ ] Test malformed JSONL, missing fields, sensitive token text, stale timestamps, and rejected decisions return `FAIL`.
- [ ] Test research mode returns `NOT_APPLICABLE` without breaking legacy behavior.
- [ ] Run focused tests and observe failure before implementation.

### Task 2: Add profile and compliance evaluator

**Files:** `mathmodel-skill/profiles/cumcm/*.yaml`, `mathmodel-skill/scripts/mmcore/compliance.py`

- [ ] Add versioned rule files and implement JSONL parsing, required-field validation, and formal-mode gate evaluation.
- [ ] Return machine-readable checks, rule metadata, mode, required gates, and status.
- [ ] Run focused tests to green.

### Task 3: Integrate G0 into CLI and release packaging

**Files:** `mathmodel-skill/scripts/mathmodel.py`, `mathmodel-skill/scripts/mmcore/package.py`

- [ ] Add `compliance` to build/audit reports and make formal failures release-blocking.
- [ ] Make package refuse reports with failed or absent formal compliance.
- [ ] Preserve legacy research-mode behavior.
- [ ] Add CLI regression tests.

### Task 4: Verify and publish

- [ ] Run all tests, build/audit/package fixtures, and negative formal-mode cases.
- [ ] Run `git diff --check`, independent review, commit Phase 1, and push to `mathmodel-ai`.
