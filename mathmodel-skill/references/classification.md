# Classification Problems

For classification tasks, define the prediction target and decision threshold before fitting models. Preserve class proportions with a documented stratified split, and keep every preprocessing step inside the training fold. Record a majority-class or cost-aware baseline before comparing candidate models.

At minimum, verify leakage control, out-of-sample metrics, threshold policy, and class-imbalance behavior. Use metrics that match the task: balanced accuracy, precision/recall, F1, ROC-AUC, or PR-AUC. Report a confusion matrix and failure analysis by class; do not call a classifier accurate or robust from one aggregate score alone.

The machine validation record should include `stratified_split`, `leakage_check`, `baseline`, and `metric_recomputation`. Falsification should include a threshold perturbation, class-balance stress test, or feature ablation appropriate to the claim.
