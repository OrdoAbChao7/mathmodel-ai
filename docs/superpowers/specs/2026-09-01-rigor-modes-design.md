# Rigor Modes Design

## Goal

Expose the v2 rigor modes as a validated project setting without allowing a time-saving setting to bypass evidence integrity or competition compliance.

## Contract

`mathmodel.json` may contain `rigor`, defaulting to `standard`. Accepted values are `fast`, `standard`, and `max`.

The setting changes only G2 candidate breadth and route-review limits. `fast` uses two total candidates, one non-baseline route, and a two-route review budget. `standard` and `max` use the CUMCM profile values unless the profile changes them. Baseline uniqueness, method-card links, complete risk probes, critical-risk blocking, G3 decisions, complexity justification, and H2 signoff are invariant.

The evaluator records the selected mode and effective limits in its report. Invalid values fail closed both during configuration loading and when the evaluator is called directly.

## Verification

- configuration tests cover all accepted values and reject unknown values;
- a minimal baseline-plus-alternative fixture passes in `fast`;
- a critical leakage risk still fails in `fast`;
- the existing standard tournament tests remain unchanged and passing.
