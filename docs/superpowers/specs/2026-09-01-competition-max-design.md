# Competition Max Design

`competition_max` is a stricter formal execution mode, not an alias of `competition_assisted`. It requires a project-local `artifacts/competition-max-review.json` record with minimum scout depth, at least four reviewed candidate routes, alternative-split/extreme-scenario/bootstrap attacks, two red-team rounds, and a completed ARS external review reference.

The local evaluator remains authoritative: external ARS output is evidence only and cannot set a release status. Assisted mode and research mode keep their existing contracts. The max report is persisted in `quality-report.json` and represented as a blocking page gate, so omission or malformed evidence cannot be hidden by a quality score.
