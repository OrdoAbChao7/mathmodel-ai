# Phase 5 — Model Architecture & Results Freeze

## Goal

Make dependencies between questions and the manuscript's numerical evidence explicit, machine-checkable, and invalidated by upstream changes.

## Contracts

`artifacts/model-architecture.json` records question nodes, typed outputs, variables, parameters, assumptions, data sources, and directed links. A link must declare how uncertainty is transferred when its source output is uncertain. G5.5 recomputes symbol, unit, parameter, assumption, data-lineage, model-dependency, and uncertainty checks; a claimed aggregate status is never trusted.

`artifacts/frozen-results.json` records the exact result-registry values accepted for publication. `artifacts/freeze-manifest.json` records hashes for configured inputs, code, configuration, registries, validation, and decision evidence. G6 recomputes those hashes and reports dependency-aware stale nodes when they differ.

Formal execution modes require G5.5 and G6. Research mode remains backward-compatible and reports both gates as `NOT_APPLICABLE`.

## Safety rules

- Missing, malformed, conflicting, or stale evidence fails closed.
- Project-relative evidence paths are required.
- Human H3 approval must cover frozen-results and freeze-manifest and explicitly confirm numbers, figures, conclusions, and limitations.
- The freeze layer never mutates source artifacts; it only evaluates their current state.
