# Artifact Schema v2 Design

Core JSON artifacts accept legacy schema v1 and current schema v2 through one shared version policy. `normalize_artifact` provides a non-mutating v2 in-memory view, while `mathmodel migrate PROJECT` explicitly upgrades v1 JSON files under `artifacts/`. Unknown versions fail closed. JSONL ledgers are excluded so append-only history is preserved.

The migration is intentionally structural: existing fields and evidence IDs are retained, and only the schema marker changes. Specialized evaluators can therefore read historical v1 fixtures and migrated v2 artifacts with the same semantic checks.
