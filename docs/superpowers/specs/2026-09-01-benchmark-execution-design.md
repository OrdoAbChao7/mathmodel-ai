# Benchmark execution fixture

`benchmarks/run_fixture_benchmark.py` is a deterministic smoke run for the Phase 9 harness. It exercises each enabled fixture's declared `benchmark_command`, then uses the real registry loader, paired A/B runner, three repeats, metric aggregation, promotion policy, and content-addressed report writer. The training paper remains an enabled build example but is excluded from this fast smoke benchmark because its full pipeline includes a long solver/LaTeX build.

The fixture intentionally uses synthetic metrics and a deterministic provider. Its `DEFAULT` result verifies orchestration semantics only; it is not evidence of CUMCM award quality and must not be used as a competition claim. Real historical cases remain separately registered with pinned source metadata and disabled until their materials are explicitly materialized and reviewed.
