# Paper Architecture

Write a complete body in this order: abstract and keywords; problem restatement; analysis and data processing; assumptions and notation; overall route; one model-result-validation chain per question; robustness or sensitivity; model evaluation; conclusions; references; appendix.

Give each question section eight elements: goal and input, assumptions and variables, mechanism or derivation, algorithm and parameters, quantitative result, interpretation, validation or counterexample, and bounded conclusion. Place core equations, result tables, and validation figures in the body.

State the problem, methods, principal quantitative results, and bounded conclusions in the abstract. Define every symbol, unit, sign, and index before reuse. Generate tables and figures from registered outputs rather than hand-entering values.

Place `\label{mm:body-start}` and `\label{mm:body-end}` around the body, then use `\clearpage` before references and appendices. Place `\label{mm:appendix-start}` and `\label{mm:appendix-end}` around appendix content. Use measured body, reference, appendix, and total pages to balance content; do not use visual padding or appendix-only core logic.
