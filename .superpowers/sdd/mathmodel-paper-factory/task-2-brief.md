# Task 2 brief — Safe init and adopt scaffolding

Read this file first — it is the task requirements, with exact values to use verbatim.

## Files

- Create `mathmodel-skill/scripts/mmcore/scaffold.py`.
- Modify `mathmodel-skill/scripts/mathmodel.py` to add `init` and `adopt` dispatch, without breaking Task 1 config behavior.
- Create `mathmodel-skill/assets/project-template/paper/main.tex`.
- Create `mathmodel-skill/assets/project-template/mathmodel.json`.
- Create `mathmodel-skill/tests/test_scaffold.py`.

## Interfaces

- `init_project(target: Path, project_id: str, title: str, problem_type: str) -> list[Path]` creates only missing files and directories.
- `adopt_project(target: Path) -> list[Path]` adds configuration and artifact directories without changing existing source files.
- CLI commands: `python mathmodel-skill/scripts/mathmodel.py init TARGET --id ID --title TITLE --type TYPE` and `python mathmodel-skill/scripts/mathmodel.py adopt TARGET`.

## Required tests and order

Use `unittest`. Write the tests before implementation, run them once and record the expected failure, then implement the smallest feature:

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

Run focused tests with:

```powershell
python -m unittest discover -s mathmodel-skill/tests -p 'test_scaffold.py' -v
```

The template config must be valid under Task 1 `load_config`, use relative paths, and contain the six allowed problem types. The template paper must contain a minimal CUMCM-compatible document with body boundary labels named `mm:body-start`, `mm:body-end`, `mm:appendix-start`, and `mm:appendix-end` for later tasks. `analysis/run.py` may be a non-solving placeholder adapter that exits with a clear message; it must not fabricate results.

`init_project` creates `problem`, `data/raw`, `data/processed`, `analysis/models`, `analysis/tests`, `artifacts`, `paper/figures`, `paper/tables`, `build`, and `.mathmodel/runs` directories, plus at least the required config, adapter, and main file. Use `.gitkeep` where an empty directory must persist. `adopt_project` scans and writes `adoption-report.json` only; it must not rewrite existing source files, PDFs, scripts, or raw data.

Run focused tests and then `python -m unittest discover -s mathmodel-skill/tests -v`. Record exact outputs in `.superpowers/sdd/mathmodel-paper-factory/task-2-report.md`. No third-party dependencies, no shell interpolation, and no subagents.

## Global constraints

- Original problem statements and raw attachments remain unchanged and read-only.
- Existing files are user-owned; never overwrite them.
- All paths in generated config are project-relative.
- No feature from Tasks 3–10 may be implemented early.
