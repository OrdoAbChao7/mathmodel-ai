# Schema Versioning Design

## Contract

The current project configuration contract is schema version 2. `init` and `adopt` create v2 configurations, and the project template is v2. `load_config` accepts v1 as a legacy input and normalizes it to v2 in memory without rewriting the user's file. Unknown, non-integer, and boolean versions fail closed.

Existing evidence artifacts remain readable under their established v1 contracts. This staged migration avoids silently rewriting historical fixtures while giving downstream stages one current configuration representation and a deterministic migration boundary.

## Compatibility rule

The normalized configuration is the value used for run manifests and downstream pipeline decisions. The original legacy file remains unchanged, so adoption is non-destructive and old projects can be re-run. Future artifact-contract migrations should use the same explicit accepted-version and in-memory-normalization pattern.

## Verification

- v1 configuration loads and normalizes to v2;
- native v2 configuration loads unchanged;
- unknown, non-integer, and boolean versions fail closed;
- newly initialized projects report v2;
- the complete test suite and training fixture remain passing.
