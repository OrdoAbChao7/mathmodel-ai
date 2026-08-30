# MathModel Paper Factory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable natural-language-plus-CLI production framework that initializes, validates, builds, audits, and packages high-quality CUMCM papers with traceable evidence and body/appendix page controls.

**Architecture:** Keep `mathmodel-skill` as the judgment and writing coordinator, and add a small Python standard-library CLI under `mathmodel-skill/scripts/`. Projects communicate with the CLI through `mathmodel.json` and seven JSON registries; the CLI never implements a universal solver. LaTeX templates expose page-boundary labels so the audit can distinguish body, references, and appendices.

**Tech Stack:** Python 3.13 (stdlib first), `unittest`, optional `openpyxl`, XeLaTeX, `pdfinfo`, `pdftoppm`, JSON, CUMCM split-file LaTeX templates.

**Spec:** `docs/superpowers/specs/2026-08-30-mathmodel-paper-factory-design.md`

## Global Constraints

- Original problem statements and raw attachments remain unchanged and read-only to the pipeline.
- Every run records input/config/code hashes, stage status, parameters, outputs, warnings, and errors.
- A result, claim, figure, or model without a stable ID and traceable source is not releasable.
- Body pages, reference pages, appendix pages, and total pages are reported separately.
- Default release profile is body 26--34 pages, total 32--40 pages, appendix/body ratio at most 0.25, and score at least 85.
- Core definitions, derivations, main results, validation, and conclusions must be in the body; appendix content cannot satisfy the body minimum.
- No placeholder text, repeated filler, empty pages, repeated decorative figures, or hard-coded unverified numbers may pass.
- Build failures, unresolved references, broken evidence links, failed validation, and invalid PDF boundaries block packaging.
- All new behavior follows RED-GREEN-REFACTOR: write a failing test, run it, implement the smallest change, rerun tests, then refactor.
- Do not claim a completed phase without fresh command output proving it.

---

### Task 1: Establish the CLI package and configuration contract

**Files:**
- Create: `mathmodel-skill/scripts/mathmodel.py`
- Create: `mathmodel-skill/scripts/mmcore/__init__.py`
- Create: `mathmodel-skill/scripts/mmcore/config.py`
- Create: `mathmodel-skill/tests/test_config.py`

**Interfaces:**
- `load_config(project: Path) -> dict` loads UTF-8 `mathmodel.json`, validates `schema_version`, required keys, enum values, and quality ranges.
- `resolve_project_path(project: Path, relative: str) -> Path` resolves a relative path and raises `ConfigError` if it escapes the project root.
- `main(argv: list[str] | None = None) -> int` dispatches CLI commands and returns a process exit code.

- [ ] **Step 1: Write the failing tests**

```python
class ConfigTests(unittest.TestCase):
    def test_load_config_accepts_minimal_valid_contract(self):
        write_json(self.root / "mathmodel.json", valid_config())
        cfg = load_config(self.root)
        self.assertEqual(cfg["problem_type"], "optimization")

    def test_rejects_path_escape(self):
        with self.assertRaises(ConfigError):
            resolve_project_path(self.root, "../outside.txt")

    def test_rejects_appendix_ratio_above_one(self):
        cfg = valid_config()
        cfg["quality"]["max_appendix_body_ratio"] = 1.1
        write_json(self.root / "mathmodel.json", cfg)
        with self.assertRaises(ConfigError):
            load_config(self.root)
```

- [ ] **Step 2: Run the tests to verify the expected failure**

Run: `python -m unittest mathmodel-skill.tests.test_config -v`

Expected: FAIL because `mmcore.config` and `ConfigError` do not exist.

- [ ] **Step 3: Implement the minimal contract**

Implement `ConfigError`, JSON loading with an object-root check, default-free required-key validation, allowed problem types, two-element page ranges with integer bounds, ratio range `[0, 1]`, and project-root path containment using `Path.resolve()`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest mathmodel-skill.tests.test_config -v`

Expected: all configuration tests PASS.

- [ ] **Step 5: Refactor and run the complete current test suite**

Run: `python -m unittest discover -s mathmodel-skill/tests -v`

Expected: no failures; keep config validation independent from filesystem mutation.

---

### Task 2: Implement safe `init` and `adopt` project scaffolding

**Files:**
- Create: `mathmodel-skill/scripts/mmcore/scaffold.py`
- Modify: `mathmodel-skill/scripts/mathmodel.py`
- Create: `mathmodel-skill/assets/project-template/paper/main.tex`
- Create: `mathmodel-skill/assets/project-template/mathmodel.json`
- Create: `mathmodel-skill/tests/test_scaffold.py`

**Interfaces:**
- `init_project(target: Path, project_id: str, title: str, problem_type: str) -> list[Path]` creates only missing files and directories.
- `adopt_project(target: Path) -> list[Path]` adds configuration and artifact directories without changing existing source files.
- CLI commands: `mathmodel.py init TARGET --id ID --title TITLE --type TYPE`, `mathmodel.py adopt TARGET`.

- [ ] **Step 1: Write the failing tests**

```python
def test_init_creates_contract_and_required_directories(self):
    created = init_project(self.root, "demo-001", "Demo", "forecasting")
    self.assertTrue((self.root / "mathmodel.json").exists())
    self.assertTrue((self.root / "analysis" / "run.py").exists())
    self.assertTrue((self.root / "paper" / "main.tex").exists())
    self.assertGreaterEqual(len(created), 8)

def test_init_never_overwrites_existing_file(self):
    old = self.root / "paper" / "main.tex"
    old.parent.mkdir(parents=True)
    old.write_text("user source", encoding="utf-8")
    init_project(self.root, "demo-001", "Demo", "optimization")
    self.assertEqual(old.read_text(encoding="utf-8"), "user source")

def test_adopt_preserves_existing_paper_and_solver(self):
    solver = self.root / "solve.py"
    solver.write_text("user code", encoding="utf-8")
    adopt_project(self.root)
    self.assertEqual(solver.read_text(encoding="utf-8"), "user code")
```

- [ ] **Step 2: Run the tests and confirm the scaffold is missing**

Run: `python -m unittest mathmodel-skill.tests.test_scaffold -v`

Expected: FAIL with missing scaffold functions.

- [ ] **Step 3: Implement safe scaffolding**

Copy only template files that do not exist, create empty working directories with `.gitkeep`, generate a valid config containing relative paths, and write an `adoption-report.json` listing detected statements, attachments, papers, scripts, and conflicts. Never delete or rewrite an existing file.

- [ ] **Step 4: Run scaffold tests**

Run: `python -m unittest mathmodel-skill.tests.test_scaffold -v`

Expected: all scaffold tests PASS.

- [ ] **Step 5: Verify CLI behavior on a temporary directory**

Run: `python mathmodel-skill/scripts/mathmodel.py init <temp-dir> --id demo-001 --title Demo --type forecasting --json`

Expected: exit code 0 and JSON listing created paths; repeat command and confirm no source content changes.

---

### Task 3: Add file inventory, hashing, and run manifests

**Files:**
- Create: `mathmodel-skill/scripts/mmcore/manifest.py`
- Modify: `mathmodel-skill/scripts/mathmodel.py`
- Create: `mathmodel-skill/tests/test_manifest.py`

**Interfaces:**
- `sha256_file(path: Path) -> str` returns a deterministic lowercase SHA-256.
- `inventory_project(project: Path, cfg: dict) -> dict` lists relevant inputs with relative path, type, size, modified time, and hash.
- `new_run(project: Path, command: str, cfg: dict, inventory: dict) -> tuple[Path, dict]` creates a timestamp/hash run directory and manifest.
- `update_stage(manifest_path: Path, stage: str, status: str, **fields) -> None` updates one stage without deleting prior evidence.

- [ ] **Step 1: Write the failing tests**

```python
def test_sha256_is_stable(self):
    path = self.root / "data.txt"
    path.write_bytes(b"abc")
    self.assertEqual(sha256_file(path), "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")

def test_run_manifest_records_input_hash_and_stages(self):
    manifest_path, manifest = new_run(self.root, "inspect", valid_config(), inventory)
    update_stage(manifest_path, "inventory", "SUCCESS", output="artifacts/data-audit.json")
    saved = json.loads(manifest_path.read_text(encoding="utf-8"))
    self.assertEqual(saved["stages"]["inventory"]["status"], "SUCCESS")
    self.assertIn("input_hashes", saved)
```

- [ ] **Step 2: Run tests to see the expected failure**

Run: `python -m unittest mathmodel-skill.tests.test_manifest -v`

Expected: FAIL because manifest functions are not implemented.

- [ ] **Step 3: Implement hashing and append-only manifests**

Hash files in chunks, normalize all stored paths to project-relative POSIX form, include Python and external tool versions when available, and represent every stage as `{status, started_at, finished_at, exit_code, outputs, warnings, errors}`. Use a fresh run ID for every invocation.

- [ ] **Step 4: Run tests and inspect raw JSON**

Run: `python -m unittest mathmodel-skill.tests.test_manifest -v`

Expected: PASS and a manifest that can be parsed without custom classes.

- [ ] **Step 5: Run `inspect` against `traning1`**

Run: `python mathmodel-skill/scripts/mathmodel.py inspect E:/Projects/school/mathmodel/traning1 --json`

Expected: exit code 0, raw input files listed, and no source file modified.

---

### Task 4: Implement evidence-contract validation and quality scoring

**Files:**
- Create: `mathmodel-skill/scripts/mmcore/contracts.py`
- Create: `mathmodel-skill/scripts/mmcore/quality.py`
- Modify: `mathmodel-skill/scripts/mathmodel.py`
- Create: `mathmodel-skill/tests/test_quality.py`

**Interfaces:**
- `validate_artifacts(project: Path, required: tuple[str, ...]) -> dict` returns `{"status": "PASS|FAIL", "checks": [...]}`.
- `audit_cross_references(artifacts: dict) -> list[dict]` checks model/question/result/claim/figure/validation IDs.
- `score_quality(checks: list[dict], manual: dict | None = None) -> dict` returns dimension scores, weighted total, hard failures, and release status.
- CLI command: `mathmodel.py audit PROJECT [--json]`.

- [ ] **Step 1: Write failing tests for hard gates**

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

- [ ] **Step 2: Run tests and confirm missing validators**

Run: `python -m unittest mathmodel-skill.tests.test_quality -v`

Expected: FAIL with missing contract functions.

- [ ] **Step 3: Implement contract checks and scoring**

Validate JSON shape, stable IDs, required question coverage, result sources, claim support, figure files/roles, validation status, placeholder text, and duplicate IDs. Assign hard failures before weighted scores; use the design weights 10/10/20/20/15/10/10/5.

- [ ] **Step 4: Run tests and inspect failure evidence**

Run: `python -m unittest mathmodel-skill.tests.test_quality -v`

Expected: PASS with each failure containing rule ID, JSON path, severity, and repair message.

- [ ] **Step 5: Add CLI Markdown and JSON reports**

Run: `python mathmodel-skill/scripts/mathmodel.py audit <fixture> --json`

Expected: both `build/quality-report.json` and `build/quality-report.md` contain the same hard-gate verdict and score.

---

### Task 5: Implement LaTeX build, PDF metrics, and body/appendix gates

**Files:**
- Create: `mathmodel-skill/scripts/mmcore/latex.py`
- Create: `mathmodel-skill/scripts/mmcore/pdfmetrics.py`
- Modify: `mathmodel-skill/scripts/mathmodel.py`
- Modify: `mathmodel-skill/assets/project-template/paper/main.tex`
- Create: `mathmodel-skill/tests/test_latex_metrics.py`

**Interfaces:**
- `compile_latex(project: Path, main: Path, engine: str, jobname: str) -> dict` runs two passes and returns exit codes, log paths, PDF path, and warnings.
- `parse_aux_pages(aux: Path, labels: tuple[str, ...]) -> dict[str, int]` reads label page numbers.
- `measure_pdf(pdf: Path, aux: Path) -> dict` returns total/body/reference/appendix page counts and ratio.
- `evaluate_page_gates(metrics: dict, quality: dict) -> list[dict]` emits hard gates and warnings.

- [ ] **Step 1: Write failing parser and gate tests**

```python
def test_aux_parser_reads_boundary_labels(self):
    aux.write_text(r"\\newlabel{mm:body-start}{{}{1}}\n\\newlabel{mm:body-end}{{}{28}}\n\\newlabel{mm:appendix-start}{{}{31}}\n\\newlabel{mm:appendix-end}{{}{35}}", encoding="utf-8")
    self.assertEqual(parse_aux_pages(aux, LABELS)["mm:body-end"], 28)

def test_appendix_ratio_is_hard_failure(self):
    gates = evaluate_page_gates({"total_pages": 40, "body_pages": 20, "appendix_pages": 10}, quality_defaults())
    self.assertTrue(any(g["rule"] == "PAGE-APPENDIX-001" and g["severity"] == "FAIL" for g in gates))
```

- [ ] **Step 2: Run tests to verify the expected failure**

Run: `python -m unittest mathmodel-skill.tests.test_latex_metrics -v`

Expected: FAIL because the parsers and compiler module do not exist.

- [ ] **Step 3: Implement compilation and metrics**

Run XeLaTeX with argument arrays, twice in `build/latex`, preserve logs, scan fatal/undefined/overfull patterns, call `pdfinfo` for total pages and A4 size, parse `.aux` labels, and calculate body/appendix boundaries. Treat body below minimum or appendix/body above maximum as FAIL.

- [ ] **Step 4: Run tests and compile the template fixture**

Run: `python -m unittest mathmodel-skill.tests.test_latex_metrics -v`

Expected: PASS; template PDF metrics distinguish body and appendix pages.

- [ ] **Step 5: Verify the historical failure mode**

Run the audit on both `traning1/paper/main.pdf` and the current 38-page build. Expected: the report names the selected input PDF, reports separate body/appendix counts, and never treats total pages alone as body quality.

---

### Task 6: Add figure/result registries and reproducible analysis hooks

**Files:**
- Create: `mathmodel-skill/scripts/mmcore/analysis.py`
- Create: `mathmodel-skill/scripts/mmcore/figures.py`
- Modify: `mathmodel-skill/scripts/mathmodel.py`
- Create: `mathmodel-skill/tests/test_analysis_hooks.py`

**Interfaces:**
- `run_analysis(project: Path, command: list[str], env: dict[str, str] | None = None) -> dict` runs the project adapter and captures outputs.
- `validate_result_registry(path: Path) -> list[dict]` checks result IDs, source paths, fields, units, and references.
- `validate_figure_registry(path: Path, project: Path) -> list[dict]` checks role coverage, file existence, source scripts, and citation labels.
- `record_output_hashes(project: Path, paths: list[Path]) -> dict[str, str]` returns output hashes.

- [ ] **Step 1: Write failing analysis-hook tests**

```python
def test_analysis_failure_preserves_stdout_and_manifest(self):
    result = run_analysis(self.root, [sys.executable, "fail.py"])
    self.assertNotEqual(result["exit_code"], 0)
    self.assertIn("intentional failure", result["stderr"])

def test_figure_registry_requires_all_default_roles(self):
    report = validate_figure_registry(self.root / "artifacts/figure-registry.json", self.root)
    self.assertTrue(any(item["rule"] == "FIGURE-ROLE-001" for item in report))
```

- [ ] **Step 2: Run tests to observe missing hooks**

Run: `python -m unittest mathmodel-skill.tests.test_analysis_hooks -v`

Expected: FAIL because analysis and registry functions do not exist.

- [ ] **Step 3: Implement subprocess capture and registry validation**

Run commands without shell interpolation, capture stdout/stderr and timeout, hash outputs, and write no result as successful when the adapter exits nonzero. Validate that every figure has one of data/method/result/validation roles and that every role is covered.

- [ ] **Step 4: Run tests and integrate with `build`**

Run: `python -m unittest mathmodel-skill.tests.test_analysis_hooks -v`

Expected: PASS; failed adapter evidence remains available for repair.

- [ ] **Step 5: Re-run the existing `traning1` adapter**

Add a thin adapter under `traning1/analysis/run.py` that calls the existing solver/generator without changing its numerical logic, then verify generated result hashes and figure registry entries.

---

### Task 7: Rewrite `mathmodel-skill` as the reusable coordination skill

**Files:**
- Modify: `mathmodel-skill/SKILL.md`
- Create: `mathmodel-skill/agents/openai.yaml`
- Create: `mathmodel-skill/references/workflow.md`
- Create: `mathmodel-skill/references/evidence-contracts.md`
- Create: `mathmodel-skill/references/paper-architecture.md`
- Create: `mathmodel-skill/references/model-validation.md`
- Create: `mathmodel-skill/references/quality-gates.md`
- Create: `mathmodel-skill/references/figure-system.md`
- Create: `mathmodel-skill/references/forecasting.md`
- Create: `mathmodel-skill/references/optimization.md`
- Create: `mathmodel-skill/references/evaluation.md`
- Create: `mathmodel-skill/tests/test_skill_assets.py`

**Interfaces:**
- Skill triggers on CUMCM paper creation/revision, modeling, LaTeX, data, reproducibility, page-balance, quality-audit, and compile requests.
- Skill always routes deterministic checks through `scripts/mathmodel.py` and uses references only when the problem type requires them.

- [ ] **Step 1: Write failing asset tests**

```python
def test_skill_description_is_searchable_and_uses_trigger_form(self):
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    self.assertRegex(text.split("---", 2)[1], r"description: Use when")
    self.assertIn("正文", text)
    self.assertIn("result-registry", text)

def test_all_referenced_files_exist(self):
    for relative in referenced_files(SKILL / "SKILL.md"):
        self.assertTrue((SKILL / relative).exists(), relative)
```

- [ ] **Step 2: Run tests and confirm the current skill is incomplete**

Run: `python -m unittest mathmodel-skill.tests.test_skill_assets -v`

Expected: FAIL because the current skill lacks the referenced reusable resources and UI metadata.

- [ ] **Step 3: Implement the concise skill and references**

Keep `SKILL.md` under 500 lines, write imperative instructions, route to the CLI, require evidence before claims, require body/appendix metrics, and describe manual review boundaries. Create valid `agents/openai.yaml` metadata after checking the local OpenAI interface reference.

- [ ] **Step 4: Run validation and asset tests**

Run: `python D:/Dev/.codex/skills/.system/skill-creator/scripts/quick_validate.py mathmodel-skill`

Then run: `python -m unittest mathmodel-skill.tests.test_skill_assets -v`

Expected: valid skill metadata and all referenced files present.

- [ ] **Step 5: Forward-test the skill on three realistic prompts**

Run fresh agent scenarios for a new optimization project, a forecasting project, and a body/appendix imbalance repair. Record whether the agents use the CLI, create registries, and reject unsupported conclusions.

---

### Task 8: Build optimization, forecasting, and evaluation fixtures

**Files:**
- Create: `mathmodel-skill/tests/fixtures/optimization/`
- Create: `mathmodel-skill/tests/fixtures/forecasting/`
- Create: `mathmodel-skill/tests/fixtures/evaluation/`
- Create: `mathmodel-skill/tests/test_end_to_end.py`
- Modify: `traning1/` only where required for adapter integration

**Interfaces:**
- Each fixture provides `mathmodel.json`, raw input, deterministic `analysis/run.py`, all seven registries, minimal LaTeX, and expected audit outcomes.
- `run_fixture(path: Path) -> dict` executes inspect → analyze → validate → compile → audit.

- [ ] **Step 1: Write failing end-to-end tests**

```python
def test_three_problem_types_reach_auditable_output(self):
    for name in ("optimization", "forecasting", "evaluation"):
        report = run_fixture(FIXTURES / name)
        self.assertEqual(report["status"], "PASS", name)
        self.assertTrue(Path(report["pdf"]).exists())
        self.assertTrue(Path(report["quality_report"]).exists())
```

- [ ] **Step 2: Run tests and confirm fixtures are absent**

Run: `python -m unittest mathmodel-skill.tests.test_end_to_end -v`

Expected: FAIL because fixtures and orchestration are absent.

- [ ] **Step 3: Implement deterministic fixtures and orchestration**

Use a small hand-checkable optimization, a time-ordered linear forecast with a holdout, and a multi-criteria weighted evaluation. Ensure each fixture produces role-complete figures, traceable claims, validation evidence, and a compileable PDF.

- [ ] **Step 4: Run the end-to-end suite**

Run: `python -m unittest mathmodel-skill.tests.test_end_to_end -v`

Expected: all three fixtures PASS with distinct result hashes.

- [ ] **Step 5: Run two-repeat reproducibility check**

Run the same fixture twice with the same seed/config and compare `results.json`, registry files, PDF text hash, and figure source hashes. Expected: identical content hashes except timestamps and run IDs.

---

### Task 9: Integrate and certify the real `traning1` project

**Files:**
- Modify: `traning1/mathmodel.json`
- Create: `traning1/analysis/run.py`
- Create: `traning1/artifacts/`
- Create: `traning1/build/`
- Create: `traning1/quality-report/`
- Create: `mathmodel-skill/tests/test_training1.py`
- Modify: `traning1/paper/main38.tex` only to add stable boundary labels and registry references

**Interfaces:**
- `traning1` becomes a real optimization fixture with existing numerical solver preserved.
- The high-level profile requires body pages to satisfy its configured range, not merely total pages.

- [ ] **Step 1: Write the failing integration assertions**

```python
def test_training1_has_traceable_problem_to_pdf_chain(self):
    report = run_fixture(TRAINING1)
    self.assertEqual(report["status"], "PASS")
    self.assertGreaterEqual(report["metrics"]["body_pages"], 26)
    self.assertLessEqual(report["metrics"]["appendix_body_ratio"], 0.25)
    self.assertIn("q3", report["problem_map"]["question_ids"])
```

- [ ] **Step 2: Run and record the expected failure before adapter integration**

Run: `python -m unittest mathmodel-skill.tests.test_training1 -v`

Expected: FAIL because `traning1` lacks the standard config, registries, and page labels.

- [ ] **Step 3: Add the adapter and registries without changing solver math**

Call the existing solver and enhancer, convert existing JSON/CSV/XLSX results into the seven registry contracts, add body boundary labels to the chosen main file, and set quality profile values based on measured body pages. Keep original `main.tex` and numerical outputs available.

- [ ] **Step 4: Run the integration test and inspect the quality report**

Run: `python -m unittest mathmodel-skill.tests.test_training1 -v`

Expected: PASS with page metrics, figure roles, model/result/claim links, and no hard failures.

- [ ] **Step 5: Render and visually inspect the complete PDF**

Run the framework preview stage, inspect the contact sheet and every flagged page, then record manual-review decisions. Expected: no clipped equations, unreadable tables, missing figures, or appendix-only core content.

---

### Task 10: Release audit and regression certification

**Files:**
- Create: `mathmodel-skill/tests/test_release_audit.py`
- Create: `mathmodel-skill/references/release-checklist.md`
- Modify: `mathmodel-skill/SKILL.md` only for fixes found by forward tests

**Interfaces:**
- `package` refuses to run when any hard gate fails or manual review is unresolved.
- Release bundle contains unique PDF name, source snapshot manifest, quality report, validation report, and reproducibility summary.

- [ ] **Step 1: Write failing release tests**

```python
def test_package_refuses_body_shortfall(self):
    report = build_release_candidate(self.fixture, body_pages=10)
    self.assertEqual(package(self.fixture, report).status, "BLOCKED")

def test_package_name_contains_page_count_and_hash(self):
    result = package(self.clean_fixture, clean_report)
    self.assertRegex(result.pdf.name, r"-\d+p-[0-9a-f]{8}\\.pdf$")
```

- [ ] **Step 2: Run tests and verify the release command is absent**

Run: `python -m unittest mathmodel-skill.tests.test_release_audit -v`

Expected: FAIL because packaging and release checks are not implemented.

- [ ] **Step 3: Implement package blocking and unique output naming**

Require machine PASS, score threshold, body/appendix thresholds, complete manual checklist, and source/output hashes. Copy rather than mutate the build artifact and write a package manifest beside the PDF.

- [ ] **Step 4: Run the complete test and fixture suite**

Run: `python -m unittest discover -s mathmodel-skill/tests -v`

Expected: all unit, integration, fixture, and release tests PASS.

- [ ] **Step 5: Perform the final fresh audit**

Run: `python mathmodel-skill/scripts/mathmodel.py package E:/Projects/school/mathmodel/traning1 --json`

Expected: exit code 0, unique PDF path, body/appendix metrics, quality score, and manifest all point to the same current build hash. Then run a clean-directory fixture build to prove the framework is not relying on stale artifacts.

***

## Plan Self-Review

- Spec coverage: configuration, scaffolding, manifests, evidence, page metrics, figures, skill content, three fixtures, real-project integration, and release gates each have dedicated tasks.
- Placeholder scan: the plan contains no unresolved implementation placeholder; words such as “missing” and “absent” describe deliberate RED test states.
- Interface consistency: all later tasks consume `mathmodel.json`, `artifacts/*.json`, `build/quality-report.json`, and `run_fixture`; page labels and profile fields match the specification.
- Scope: universal solver intelligence remains outside the CLI; the framework standardizes evidence, repeatability, paper rendering, and review rather than pretending every model can be automated.
