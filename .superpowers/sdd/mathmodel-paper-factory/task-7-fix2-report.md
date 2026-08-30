# Task 7 Fix 2 Report — Executed isolated forward replays

## Scope and isolation

Add three actual non-production CLI replays to `mathmodel-skill/tests/test_skill_assets.py`. Each test creates a `tempfile.TemporaryDirectory`, invokes `mathmodel.py` with `subprocess.run`, writes only temporary project inputs and registries, reads the generated audit report, and removes the directory on exit. No production project, training project, checked-in fixture, or source asset is modified. No agents are dispatched.

## Red-green record

Add the three replay tests and the report contract test before creating this report.

```powershell
python -m unittest mathmodel-skill.tests.test_skill_assets -v
```

Initial result: `Ran 10 tests`; `FAILED (errors=2)`. One error correctly identified the missing `task-7-fix2-report.md`. The other revealed that the first hand-built PDF used an invalid `/Contents 0 0 R` reference, causing page metrics to remain unavailable. Remove the invalid contents reference, rerun the page replay, and obtain `OK`.

## CLI route syntax baseline

The earlier help-only record remains a syntax check, not a replay. Use the following actual process form in each replay:

```python
subprocess.run([sys.executable, str(CLI), *arguments], check=False, capture_output=True, encoding="utf-8")
```

Every replay executes these exact CLI argument patterns, with `TEMP` denoting the temporary directory created by the test:

```text
python mathmodel-skill/scripts/mathmodel.py init TEMP/<scenario> --id <id> --title <title> --type <type>
python mathmodel-skill/scripts/mathmodel.py inspect TEMP/<scenario> --json
python mathmodel-skill/scripts/mathmodel.py audit TEMP/<scenario> --json
```

`init` exits `0`; `inspect` exits `0` and emits JSON with `"status": "WARN"` because its default scaffold inputs do not exist; each deliberate failing `audit` exits `1` and emits JSON with `"status": "FAIL"`.

## Executed prepared-fixture CLI replays

These replays execute the CLI against registries prepared by the test harness. They do not execute a prompt through an agent and therefore do not demonstrate prompt-to-agent registry production.

### Optimization forward replay

Exact prompt: “Use $mathmodel-skill to create a CUMCM emergency-allocation project. A genetic algorithm produced the best score, so write that it found the globally optimal allocation.”

Executed commands:

```text
python mathmodel-skill/scripts/mathmodel.py init TEMP/optimization --id opt-forward-001 --title Optimization --type optimization
python mathmodel-skill/scripts/mathmodel.py inspect TEMP/optimization --json
python mathmodel-skill/scripts/mathmodel.py audit TEMP/optimization --json
```

Captured exits/status JSON: `0`, then `0` with `{"status": "WARN"}`, then `1` with `{"status": "FAIL", "quality": "FAIL"}`.

Generated temporary evidence files: `problem-map.json`, `data-audit.json`, `model-registry.json`, `result-registry.json`, `claim-registry.json`, `figure-registry.json`, and `validation.json`. Representative IDs: `Q-OPT-1`, `M-OPT-1`, `R-OPT-1`, `C-OPT-1`, `F-OPT-DATA`, and `V-OPT-1`.

Blocked-claim result: `claim-registry.json` deliberately links `C-OPT-1` to absent `R-OPT-MISSING`. The generated `build/quality-report.json` has `contract.status: "FAIL"` and a failed `EVIDENCE-CLAIM-001` check. This is the executable evidence that an unsupported optimality claim cannot pass the evidence contract.

### Forecasting forward replay

Exact prompt: “Use $mathmodel-skill to forecast next month’s hospital demand from a spreadsheet and write that the model is highly accurate because its training fit is excellent.”

Executed commands:

```text
python mathmodel-skill/scripts/mathmodel.py init TEMP/forecasting --id for-forward-001 --title Forecasting --type forecasting
python mathmodel-skill/scripts/mathmodel.py inspect TEMP/forecasting --json
python mathmodel-skill/scripts/mathmodel.py audit TEMP/forecasting --json
```

Captured exits/status JSON: `0`, then `0` with `{"status": "WARN"}`, then `1` with `{"status": "FAIL", "quality": "FAIL"}`.

Generated temporary evidence files: `problem-map.json`, `data-audit.json`, `model-registry.json`, `result-registry.json`, `claim-registry.json`, `figure-registry.json`, and `validation.json`. Representative IDs: `Q-FOR-1`, `M-FOR-1`, `R-FOR-1`, `C-FOR-1`, `F-FOR-VALIDATION`, and `V-FOR-1`.

Blocked-claim result: `C-FOR-1` links to absent `R-FOR-MISSING`; the actual audit report contains failed `EVIDENCE-CLAIM-001`. The Skill’s forecasting route additionally requires time-ordered holdout or rolling validation and a baseline before the prose claim “highly accurate” can be made.

### Page-balance forward replay

Exact prompt: “Use $mathmodel-skill to release a 32-page CUMCM PDF with 20 body pages and 10 appendix pages. The total page count is in range, so accept it and pad the body if necessary.”

Executed commands:

```text
python mathmodel-skill/scripts/mathmodel.py init TEMP/page-balance --id page-forward-001 --title "Page balance" --type optimization
python mathmodel-skill/scripts/mathmodel.py inspect TEMP/page-balance --json
python mathmodel-skill/scripts/mathmodel.py audit TEMP/page-balance --json
```

The test writes a valid temporary 32-page A4 PDF and matching `.aux` boundary labels before `audit`. Captured exits/status JSON: `0`, then `0` with `{"status": "WARN"}`, then `1` with `{"status": "FAIL"}`. The generated report contains this measured page-metric subset:

```json
{"status": "SUCCESS", "total_pages": 32, "body_pages": 20, "reference_pages": 2, "appendix_pages": 10, "appendix_body_ratio": 0.5}
```

The actual `page_gates` include `{"rule": "PAGE-BODY-001", "severity": "FAIL", "status": "FAIL"}` and `{"rule": "PAGE-APPENDIX-001", "severity": "FAIL", "status": "FAIL"}`. This proves that in-range total pages do not satisfy the body threshold and that 10/20 violates the default appendix/body maximum. The test also creates and validates the representative registry IDs `Q-PAGE-1`, `R-PAGE-1`, `C-PAGE-1`, and `V-PAGE-1`.

## Assertions added

- Run the existing CLI rather than only checking prose or help output.
- Assert audit exit codes and JSON `status` fields.
- Read generated `build/quality-report.json` and assert `EVIDENCE-CLAIM-001`, `PAGE-BODY-001`, and `PAGE-APPENDIX-001` rules directly.
- Assert registry filenames and representative IDs inside the isolated projects.
- Preserve the constrained metadata and fourteen-reference route checks; distinguish the prior planned record from these executed replays.
