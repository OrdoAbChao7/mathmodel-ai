# Task 1 brief — Establish the CLI package and configuration contract

Read this file first — it is the task requirements, with the exact values to use verbatim.

## Files

- Create `mathmodel-skill/scripts/mathmodel.py`.
- Create `mathmodel-skill/scripts/mmcore/__init__.py`.
- Create `mathmodel-skill/scripts/mmcore/config.py`.
- Create `mathmodel-skill/tests/test_config.py`.

## Interfaces

- `load_config(project: Path) -> dict` loads UTF-8 `mathmodel.json`, validates `schema_version`, required keys, enum values, and quality ranges.
- `resolve_project_path(project: Path, relative: str) -> Path` resolves a relative path and raises `ConfigError` if it escapes the project root.
- `main(argv: list[str] | None = None) -> int` dispatches CLI commands and returns a process exit code.

## Required tests and order

Use Python `unittest`. Write tests before implementation and run the tests once to observe the expected failure. Cover exactly these behaviors:

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

Run tests with:

```powershell
python -m unittest discover -s mathmodel-skill/tests -p 'test_config.py' -v
```

The initial run must fail because the module and `ConfigError` are missing. Then implement the smallest contract: object-root JSON validation, required keys, allowed problem types `forecasting`, `optimization`, `evaluation`, `mechanism`, `simulation`, `hybrid`, two-element page ranges with integer bounds, ratio range `[0, 1]`, and project-root path containment using `Path.resolve()`.

Use no third-party dependency. Do not mutate files while loading config. The CLI may initially support only `--help` and return a useful error for unimplemented commands; do not implement later tasks early.

After implementation rerun the focused test and then the complete discovered suite. Record the exact commands and outputs in the report.

## Report contract

Write the full report to `.superpowers/sdd/mathmodel-paper-factory/task-1-report.md`. Return only: `DONE`, commit status (the workspace is not a Git repository), one-line test summary, and concerns. The report must include changed files, RED command/output, GREEN command/output, complete-suite command/output, and any concerns. Do not dispatch subagents.

## Global constraints

- Original problem statements and raw attachments remain unchanged and read-only.
- Every run will eventually record input/config/code hashes and stage status; do not add a shortcut that prevents this later.
- All new behavior follows RED-GREEN-REFACTOR.
- Do not use absolute project paths in generated config.
