# Experiment Provenance Design

Formal G4/G5 validation now requires `artifacts/experiment-registry.json`. Each experiment record binds a stable experiment ID and run ID to a question, model, code hashes, input hashes, the current configuration hash, seed, environment, start/end timestamps, metrics, figures, and result artifacts. `metrics` and `result_artifacts` must contain at least one existing project-local file; `figures` may be empty only when the experiment legitimately produces no figure.

The evaluator recomputes all referenced file hashes and checks project containment and output existence. It does not trust an aggregate `status` supplied by an agent. Missing metadata, stale hashes, unsafe paths, or missing outputs produce a blocking G4 failure. Research mode remains not applicable, preserving training workflows.
