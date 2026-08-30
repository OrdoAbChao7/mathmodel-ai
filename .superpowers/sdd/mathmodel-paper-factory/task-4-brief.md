# Task 4 brief — Evidence-contract validation and quality scoring

Read this file first — it is the task requirements, with exact values to use verbatim.

## Files

- Create `mathmodel-skill/scripts/mmcore/contracts.py`.
- Create `mathmodel-skill/scripts/mmcore/quality.py`.
- Modify `mathmodel-skill/scripts/mathmodel.py` to add `audit PROJECT --json` without breaking Tasks 1–3 commands.
- Create `mathmodel-skill/tests/test_quality.py`.

## Interfaces

- `validate_artifacts(project: Path, required: tuple[str, ...]) -> dict` returns `{"status": "PASS|FAIL", "checks": [...]}`.
- `audit_cross_references(artifacts: dict) -> list[dict]` checks question/model/result/claim/figure/validation IDs.
- `score_quality(checks: list[dict], manual: dict | None = None) -> dict` returns dimension scores, weighted total, hard failures, and release status.
- CLI command: `python mathmodel-skill/scripts/mathmodel.py audit PROJECT --json`.

## Registry files and minimum contract

The seven artifact files are `problem-map.json`, `data-audit.json`, `model-registry.json`, `result-registry.json`, `claim-registry.json`, `figure-registry.json`, and `validation.json` under `artifacts/`. Each is a JSON object or array with stable IDs where applicable. A complete fixture may use the following object shapes:

```json
{
  "problem-map": {"questions": [{"id": "q1", "model_ids": ["M1"], "result_ids": ["R1"], "validation_ids": ["V1"], "claim_ids": ["C1"]}]},
  "model-registry": {"models": [{"id": "M1", "question_id": "q1"}]},
  "result-registry": {"results": [{"id": "R1", "source": "analysis/run.py", "value": 1, "unit": "unit"}]},
  "claim-registry": {"claims": [{"id": "C1", "result_ids": ["R1"], "validation_ids": ["V1"]}]},
  "figure-registry": {"figures": [{"id": "F1", "role": "result", "file": "paper/figures/result.pdf", "claim_ids": ["C1"]}]},
  "validation": {"validations": [{"id": "V1", "status": "PASS", "question_id": "q1"}]}
}
```

`data-audit.json` must be present and valid JSON; its detailed schema is owned by Task 3 and must not be reimplemented. Contract validation must report missing files, malformed JSON, duplicate IDs, broken cross-references, missing result sources, missing figure files, missing required roles, and non-PASS validation statuses. The required roles default to `data`, `method`, `result`, and `validation` when no config override is available.

## Required tests and order

Use `unittest`. Write tests first and run once to observe the expected failure:

```python
def test_missing_claim_support_is_hard_failure(self):
    write_artifacts(self.root, result_ids=["R-1"], claim_support=["R-missing"])
    report = validate_artifacts(self.root, REQUIRED)
    self.assertEqual(report["status"], "FAIL")
    self.assertTrue(any(c["rule"] == "EVIDENCE-CLAIM-001" for c in report["checks"]))

def test_clean_contract_scores_at_least_eighty_five(self):
    write_complete_artifacts(self.root)
    report = validate_artifacts(self.root, REQUIRED)
    scored = score_quality(report["checks"])
    self.assertEqual(report["status"], "PASS")
    self.assertGreaterEqual(scored["total"], 85)
```

Run focused tests with:

```powershell
python -m unittest discover -s mathmodel-skill/tests -p 'test_quality.py' -v
```

Every check record must contain `rule`, `severity`, `status`, `message`, and a path or evidence field. Hard failures use `severity: FAIL` and force report status `FAIL`; warnings do not. Use score dimensions and weights exactly as specified: problem coverage 10, data/traceability 10, model rigor 20, validation/robustness 20, result/claim evidence 15, body expression 10, figures 10, LaTeX 5. If no manual review is supplied, score only machine checks and mark `manual_review: PENDING`; a future package command will block on that state.

The CLI `audit` loads config, validates artifacts, writes `build/quality-report.json` and `build/quality-report.md`, and prints JSON with `--json`. It may report page metrics as `PENDING` until Task 5; do not implement PDF parsing or compilation early. It must preserve prior reports by writing in the current build directory only.

Write the full report to `.superpowers/sdd/mathmodel-paper-factory/task-4-report.md`. Include RED, GREEN, complete-suite commands and exact outputs. Do not dispatch subagents or fabricate a Git commit.

## Global constraints

- Original statements and raw attachments remain unchanged.
- Every result, claim, figure, model, and validation reference uses stable IDs.
- A hard failure cannot be hidden by a high weighted score.
- No later Task 5–10 behavior may be implemented early.
