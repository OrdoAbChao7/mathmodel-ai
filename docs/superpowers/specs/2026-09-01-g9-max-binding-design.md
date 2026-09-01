# G9 Competition-Max Binding Design

The G9 submission evaluator now includes the `max_rigor` report in its gate map when `execution_mode` is `competition_max`. It adds `G9-MAX-001`, which fails if the audit report omits the max extension report or records any status other than `PASS`. Assisted submissions retain the original gate set.

This closes the distinction between an audit-time max page gate and the final release authority: a max-mode submission cannot become `RELEASE_STATUS=PASS` from a report that contains G0–G8 but omits the required max-specific robustness, red-team, and ARS evidence. G9 also re-evaluates the current `competition-max-review.json` instead of trusting the persisted report alone, so deleting or tampering with the extension after audit blocks release.
