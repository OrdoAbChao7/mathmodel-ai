# G9 — Submission Ready

`mmcore.submission.evaluate_submission` is the final formal-mode gate. It consumes the same quality report as packaging, but independently checks the release boundary: G0–G8 status, absence of open critical findings, real in-project PDF compilation, page gates, safe TeX inputs and references, anonymity markers, source programs, configured attachments, AI usage detail/disclosure, and current hash evidence.

Only `competition_assisted` and `competition_max` can return `PASS`. Research mode returns `NOT_APPLICABLE` and preserves the existing training workflow. Formal `package` calls G9 before creating a release bundle; a failed G9 adds `PACKAGE-G9-001` and blocks packaging.

The evaluator is deliberately fail-closed. It does not infer missing evidence, treat a claimed status as proof, or download external material. Submission manifests are project-relative and must list the configured supporting attachments and source programs.
