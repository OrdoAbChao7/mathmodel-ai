# Phase 6 — Evidence-Constrained Paper & Adversarial Review

## Goal

Turn paper writing into evidence translation. A formal competition package may only use locked artifacts, frozen results, validated claims, canonical figures, verified citations, and completed independent reviews.

## Contracts

`artifacts/writer-package.json` binds every claim to the exact registry support, every figure to its canonical file, every citation to local verification evidence, and the final abstract to a three-candidate tournament plus judge-view answers. Strong claims without the required evidence emit `UNSUPPORTED_STRONG_CLAIM` and fail G7.

`artifacts/review-registry.json` records independent mathematical, statistical, evidence-consistency, red-team, citation, judge-view, and final-judge reviews. Duplicate identities, malformed findings, missing reviewer types, or an `OPEN` `CRITICAL` finding fail G8.

Research mode remains backward-compatible and reports G7/G8 as `NOT_APPLICABLE`; formal modes fail closed.
