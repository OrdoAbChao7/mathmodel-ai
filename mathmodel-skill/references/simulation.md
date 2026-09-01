# Simulation Modeling

Use simulation when uncertainty, queues, interactions, or unavailable closed-form solutions make a deterministic formula inadequate. Define the state, transition rule, random inputs, decision policy, and output estimand before coding. Keep the random seed, replication count, warm-up rule, stopping rule, and confidence-interval method in the experiment record.

Validate convergence by increasing replications or checking batch means, compare a simple baseline policy, and test at least one extreme scenario. Report uncertainty intervals with the point estimate; never present one random realization as a stable conclusion. Explain which conclusions are conditional on the input distributions and simulator assumptions.

In the paper, put the state-transition diagram, estimand, replication design, convergence evidence, and key scenario table in the body. Put exhaustive random-seed logs and supplementary replications in the appendix.
