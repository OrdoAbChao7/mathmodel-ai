# Hybrid Problems

A hybrid problem combines different structures, such as forecasting followed by optimization, simulation inside a policy evaluation, or statistical estimation feeding a mechanistic model. Build an explicit question-dependency graph and label every interface variable with its unit, uncertainty, and provenance.

Do not silently turn a forecast interval into a fixed constant. Specify uncertainty transfer, timing, and scenario coupling; validate each component with its type-specific checks and validate the composition with an end-to-end baseline. Test interface failures, alternative decomposition orders, and at least one boundary scenario.

The body should explain the dependency graph and interface contracts before presenting results. Report component and end-to-end metrics separately, then state which conclusions remain valid when an upstream component changes.
