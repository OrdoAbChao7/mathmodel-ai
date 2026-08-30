# Forecasting Route

Define the forecast target, horizon, observation time, units, information available at each prediction time, and operational decision that uses the forecast. Sort observations chronologically; prevent future information from entering feature construction, scaling, imputation, or tuning.

Establish a simple baseline such as persistence, seasonal naive, moving average, or trend. Fit the simplest justified model, record feature definitions and hyperparameters, and evaluate with a final holdout or rolling-origin procedure. Report MAE, RMSE, MAPE only when meaningful for the scale, and interval coverage or residual diagnostics when uncertainty matters.

Store forecast values, errors, split dates, seed, and model IDs in the result and validation registries. Compare against the baseline, test sensitivity to horizon or key assumptions, and reject claims of improved accuracy unless evaluation uses the same time-ordered test data.
