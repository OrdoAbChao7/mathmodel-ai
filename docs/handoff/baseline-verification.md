# Pre-real-case Baseline Verification

**Verification date:** 2026-09-02

This file records the commands run on the final handoff tree. It separates code regressions from machine/environment blockers.

## Commands and results

### Full regression suite

```text
python -m unittest discover -s mathmodel-skill/tests -p "test_*.py"
```

Result: **PASS** — 326 tests ran, 0 failures, 0 errors, 2 skips.

The suite emits an expected negative-case diagnostic (`unsupported problem type: unknown`) while testing rejection behavior; the process exits 0 and the unittest summary is green.

### Deterministic fixture benchmark

```text
python benchmarks/run_fixture_benchmark.py
```

Result: **PASS** — 12 records, promotion status `DEFAULT`, no hard regressions. The benchmark is a deterministic harness check, not a CUMCM quality score and not evidence of award performance.

### Formal submission fixture

```text
python mathmodel-skill/scripts/mathmodel.py submission benchmarks/cases/formal-submission-fixture --json
```

Result: **PASS** — G9 reports G0–G8 PASS, current PDF evidence, page metrics, anonymity, references, source/supporting-material presence, AI-use detail, and current release hashes.

### Capability and authority smoke checks

```text
python mathmodel-skill/scripts/mathmodel.py capability . --json
python mathmodel-skill/scripts/mathmodel.py authority . --json
```

Result: capability registry **PASS**; constitution **PASS**; external authority is **REJECTED** as intended. External sources remain advisory and pinned.

## Environment limitation

The repository's real `traning1` example depends on a functioning local TeX/MiKTeX installation and its configured numerical Python environment. If a fresh `traning1` build fails with the classified MiKTeX environment code, that is an **ENVIRONMENT BLOCKER**, not evidence of a code regression, provided the solver and analysis stages succeed. Any ordinary solver, analysis, artifact, semantic, or gate failure remains a **CODE/PROJECT REGRESSION** and must not be relabeled as environment noise.

The synthetic formal fixture is the reproducible release-path check used for this handoff.

## Baseline interpretation

These results establish reproducibility of the local OS contracts. They do not establish real-case modeling quality, LLM-agent quality, or competition results. The baseline tag `pre-realcase-training-v1` must remain immutable once created.
