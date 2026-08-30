# Evidence Contracts

Create UTF-8 JSON registries under `artifacts/`. Use stable IDs and project-relative source paths.

| Artifact | Record | Reject when |
|---|---|---|
| `problem-map.json` | Question ID, objective, inputs, outputs, constraints, method, validation, section | A question lacks a model, result, validation, or conclusion link |
| `data-audit.json` | Source path, hash, units, preprocessing, missingness | Data provenance or units are unknown |
| `model-registry.json` | Model ID, variables, parameters, objective, constraints, solver, seed, limitations | A model cannot be reproduced or tied to a question |
| `result-registry.json` | Result ID, value, unit, precision, generating code, input hash, model and validation IDs | A paper number has no traceable source |
| `claim-registry.json` | Claim ID, body text, supported result IDs, scope, failure case, section | A conclusion has no result or validation support |
| `figure-registry.json` | Figure ID, file, role, source data, script, label, supported IDs, readability check | A required role or source is missing |
| `validation.json` | Check ID, method, inputs, metric, threshold, result, failure case | Validation is absent, failed, or irrelevant |

Link IDs rather than copying values. Regenerate affected results and figures after changing inputs, code, configuration, or model parameters. Reject “best,” “accurate,” “robust,” “improved,” and “significant” unless the registry records the appropriate comparison or test.
