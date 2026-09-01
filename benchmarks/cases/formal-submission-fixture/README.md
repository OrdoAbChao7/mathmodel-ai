# Formal submission fixture

This directory is a synthetic, deterministic fixture for exercising the `competition_assisted` G9 command. Its PDF and review records are test evidence only; they are not a CUMCM submission, an official score, or a claim of award quality.

Run from the repository root:

```bash
python mathmodel-skill/scripts/mathmodel.py submission benchmarks/cases/formal-submission-fixture --json
```

The expected result is `RELEASE_STATUS=PASS`. Real competition projects must replace every fixture artifact with human-reviewed evidence.
