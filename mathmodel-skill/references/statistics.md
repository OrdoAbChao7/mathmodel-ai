# Statistical Problems

For statistical inference tasks, state the estimand, sampling assumptions, unit of analysis, and uncertainty convention before calculating estimates. Distinguish descriptive summaries from inferential claims, and document missing-data handling, dependence, and multiple-comparison decisions.

Use a transparent baseline such as a direct estimator or null model. Recompute reported estimates from the recorded inputs, report confidence or prediction intervals when uncertainty matters, and test sensitivity to plausible distributional or sampling assumptions. A small p-value alone does not establish practical importance, causality, or robustness.

The machine validation record should include `sample_assumptions`, `uncertainty_interval`, `baseline`, and `metric_recomputation`. Falsification should include a bootstrap or permutation check, an alternative specification, or a boundary-case analysis tied to the claim.
