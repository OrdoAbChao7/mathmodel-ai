# CUMCM MathModel Paper Factory

This project provides a reproducible workflow for producing and auditing mathematical-modeling contest papers. It includes a reusable `mathmodel-skill`, deterministic CLI checks, evidence registries, solver/analysis runners, LaTeX page-balance gates, three end-to-end fixtures, and release packaging rules.

## Quick start

```text
python mathmodel-skill/scripts/mathmodel.py init <project> --id <id> --title <title> --type optimization
python mathmodel-skill/scripts/mathmodel.py inspect <project> --json
python mathmodel-skill/scripts/mathmodel.py build <project> --json
python mathmodel-skill/scripts/mathmodel.py audit <project> --json
python mathmodel-skill/scripts/mathmodel.py package <project> --json
```

The package command blocks unresolved manual review, missing evidence, failed quality/page gates, stale or missing PDFs, and absent hashes. Total PDF pages never substitute for substantive body pages.

The three deterministic fixtures are under `mathmodel-skill/tests/fixtures/`. The real `traning1` project is an integrated example: its configured build runs `solve.py`, `enhance.py`, the LaTeX compiler, page-balance gates, evidence checks, and release packaging. Its current verified output is 38 total pages, 32 body pages, 3 appendix pages, and an appendix/body ratio below 10%.

On this Windows workspace the example uses the bundled Python runtime path in `traning1/mathmodel.json`, because the system Python does not include the numerical and plotting dependencies required by `solve.py`. When moving the project to another machine, replace that interpreter path with a Python environment containing NumPy, SciPy, Matplotlib, and OpenPyXL.
