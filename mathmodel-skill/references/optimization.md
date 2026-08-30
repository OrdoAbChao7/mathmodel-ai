# Optimization Route

Define decision variables, sets, units, objective, constraints, and feasibility conditions before choosing a solver. Separate hard constraints from penalties and explain every coefficient's source. Formulate a small hand-checkable instance or boundary case before trusting a large run.

Use an exact linear, integer, or nonlinear method when the formulation permits it. When using a heuristic, record encoding, initialization, seed, repair operator, stopping rule, runtime, and a comparison baseline or bound. Record solver status, objective value, feasibility, maximum constraint violation, and optimality gap when available.

Test scenarios that perturb demand, capacity, cost, weights, or other key inputs. Store each selected allocation, objective, constraint check, solver log source, and scenario result in the registries. Reject “optimal” when the solver has no proof or gap; state “best feasible solution found” with its conditions instead.
