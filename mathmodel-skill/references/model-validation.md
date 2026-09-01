# Model Validation

Run common checks first: verify units and signs, test boundary and hand-calculated cases, compare a baseline where one exists, perturb influential assumptions, and record at least one failure mode or limitation.

| Type | Require |
|---|---|
| Forecasting | Time-ordered split, rolling or holdout evaluation, MAE/RMSE or justified metric, residual or interval analysis |
| Optimization | Solver status, feasibility, maximum constraint violation, bound or optimality gap, baseline, and scenario perturbation |
| Evaluation | Indicator direction, normalization, weight source, ranking stability, and weight perturbation |
| Simulation | Seed, repetitions, uncertainty interval, convergence evidence, and scenario comparison |
| Mechanism | Dimensional consistency, boundary behavior, parameter identifiability, and calibration or external comparison |
| Classification | Stratified split, leakage check, baseline, threshold policy, class-wise diagnostics, and metric recomputation |
| Statistics | Sampling assumptions, uncertainty interval, baseline, missing-data policy, specification sensitivity, and metric recomputation |
| Hybrid | Component-specific checks, explicit dependency graph, uncertainty transfer, end-to-end baseline, and interface/boundary stress test |

Write each check to `validation.json` with its input IDs, metric, threshold, observed result, and interpretation. Reject a conclusion when a required check fails; report the failure and restrict the claim instead.
