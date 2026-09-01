# Phase 9 — Controlled Benchmark Harness

## Goal

Measure whether a new capability improves the system under paired, reproducible conditions. A benchmark is evidence for promotion, not a claim that a model or paper is always correct.

## Contracts

- `benchmarks/cases/registry.json` is the allow-list of cases. Case IDs are unique, paths are project-relative, and enabled cases must exist.
- Baseline and candidate run on the same registered case and repeat index.
- Each result must be `PASS`, include all declared metrics, and include control metadata. Provider, model, budget, and evidence controls must match within and across repetitions.
- Metrics are aggregated by arithmetic mean. Higher-is-better and lower-is-better directions are explicit in code.
- `DEFAULT` requires a meaningful improvement and no hard regression. A tie is `OPTIONAL`; any hard regression is `REJECTED`.
- Malformed registry, runner exceptions, missing metrics, non-finite values, control drift, and empty enabled registries fail closed.

## CLI contract

```text
mathmodel benchmark PROJECT [--registry PATH] [--repeats N] [--json]
```

Commands are configured in the project as `benchmark.baseline_command` and `benchmark.candidate_command`. Each command receives `MATHMODEL_BENCHMARK_CASE`, `MATHMODEL_BENCHMARK_CASE_ID`, `MATHMODEL_BENCHMARK_VARIANT`, and `MATHMODEL_BENCHMARK_REPEAT`, and must print one JSON result.

Reports are content-addressed under `benchmarks/reports/` so rerunning the same report does not create duplicate filenames.
