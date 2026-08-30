"""Analysis adapter execution and deterministic run-output inventories."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .manifest import sha256_file
from .runner import run_project_command


def collect_outputs(run_dir: Path) -> dict[str, Any]:
    """Inventory regular files stored inside a run directory without escaping it."""
    root = Path(run_dir).resolve()
    files: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    if not root.is_dir():
        return {"status": "FAILED", "files": files, "warnings": warnings, "errors": [{"rule": "OUTPUT-RUN-DIR-001", "message": "run directory does not exist"}]}
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().casefold()):
        if not path.is_file():
            continue
        try:
            resolved = path.resolve()
            relative = resolved.relative_to(root)
        except ValueError:
            warnings.append({"rule": "OUTPUT-PATH-001", "message": "skipped output that resolves outside the run directory", "path": str(path)})
            continue
        relative_path = relative.as_posix()
        if relative_path == "manifest.json":
            kind = "framework_manifest"
        elif path.name.endswith((".stdout.log", ".stderr.log")):
            kind = "framework_log"
        else:
            kind = "generated_output"
        files.append({
            "path": relative_path,
            "size": resolved.stat().st_size,
            "sha256": sha256_file(resolved),
            "kind": kind,
            "provenance": {"run_id": root.name, "run_directory": str(root)},
        })
    return {"status": "WARN" if warnings else "SUCCESS", "files": files, "warnings": warnings, "errors": []}


def run_analysis(project: Path, command: list[str], run_dir: Path) -> dict[str, Any]:
    """Execute analysis only through the same safe project-scoped runner."""
    return run_project_command(project, command, run_dir, "analysis")
