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

The three deterministic fixtures are under `mathmodel-skill/tests/fixtures/`. The real `traning1` project remains intentionally blocked until its substantive body is expanded; no appendix pages are counted as body pages.
