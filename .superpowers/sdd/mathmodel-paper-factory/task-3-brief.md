# Task 3 brief — Inventory, hashing, and run manifests

Read this file first — it is the task requirements, with exact values to use verbatim.

## Files

- Create `mathmodel-skill/scripts/mmcore/manifest.py`.
- Modify `mathmodel-skill/scripts/mathmodel.py` to add `inspect` dispatch without breaking `init`, `adopt`, or `main` help behavior.
- Create `mathmodel-skill/tests/test_manifest.py`.

## Interfaces

- `sha256_file(path: Path) -> str` returns a deterministic lowercase SHA-256.
- `inventory_project(project: Path, cfg: dict) -> dict` lists relevant inputs with relative path, type, size, modified time, and hash.
- `new_run(project: Path, command: str, cfg: dict, inventory: dict) -> tuple[Path, dict]` creates a timestamp/hash run directory and manifest.
- `update_stage(manifest_path: Path, stage: str, status: str, **fields) -> None` updates one stage without deleting prior evidence.
- CLI command: `python mathmodel-skill/scripts/mathmodel.py inspect PROJECT --json`.

## Required tests and order

Use `unittest`. Write tests before implementation and run them once to observe failure:

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

Run focused tests with:

```powershell
python -m unittest discover -s mathmodel-skill/tests -p 'test_manifest.py' -v
```

Implement chunked hashing, project-relative POSIX paths, input file inventory from config plus recognized project files, Python/tool version fields when available, and stages represented as `{status, started_at, finished_at, exit_code, outputs, warnings, errors}`. Use a fresh run ID for every invocation. `inspect` must write `artifacts/data-audit.json` and the new manifest, and print JSON when `--json` is supplied.

Do not overwrite raw data or prior run manifests. The project may be passed as a string by the CLI but public functions accept `Path`; normalize at the boundary. If an input path is listed but missing, record it with `exists: false` and status `WARN` rather than crashing inventory. Do not implement Tasks 4–10.

Write the full report to `.superpowers/sdd/mathmodel-paper-factory/task-3-report.md`. Include RED, GREEN, complete-suite commands and exact outputs. Do not dispatch subagents or fabricate a Git commit.

## Global constraints

- Original problem statements and raw attachments remain unchanged and read-only.
- Every run records hashes, command, configuration snapshot, stage status, outputs, warnings, and errors.
- Historical runs are append-only.
- No shell interpolation and no third-party dependency.
