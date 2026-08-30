# Model Validation

Run common checks first: verify units and signs, test boundary and hand-calculated cases, compare a baseline where one exists, perturb influential assumptions, and record at least one failure mode or limitation.

| Type | Require |
|---|---|
| Forecasting | Time-ordered split, rolling or holdout evaluation, MAE/RMSE or justified metric, residual or interval analysis |
| Optimization | Solver status, feasibility, maximum constraint violation, bound or optimality gap, baseline, and scenario perturbation |
| Evaluation | Indicator direction, normalization, weight source, ranking stability, and weight perturbation |
| Simulation | Seed, repetitions, uncertainty interval, convergence evidence, and scenario comparison |
| Mechanism | Dimensional consistency, boundary behavior, parameter identifiability, and calibration or external comparison |

Write each check to `validation.json` with its input IDs, metric, threshold, observed result, and interpretation. Reject a conclusion when a required check fails; report the failure and restrict the claim instead.
