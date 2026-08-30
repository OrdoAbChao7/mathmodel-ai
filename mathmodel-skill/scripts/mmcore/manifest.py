"""Project inventories and append-only run manifests."""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import resolve_project_path


_CHUNK_SIZE = 1024 * 1024
_TYPE_BY_SUFFIX = {
    ".pdf": "statement",
    ".doc": "statement",
    ".docx": "statement",
    ".txt": "statement",
    ".xlsx": "attachment",
    ".xls": "attachment",
    ".csv": "attachment",
    ".tex": "paper",
    ".py": "script",
    ".m": "script",
    ".r": "script",
    ".jl": "script",
    ".ipynb": "script",
    ".sh": "script",
}
_STAGE_FIELDS = ("status", "started_at", "finished_at", "exit_code", "outputs", "warnings", "errors", "output_inventory")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def recognized_path_decision(root: Path, candidate: Path) -> tuple[str | None, str | None]:
    """Return a safe relative path, or a warning for an out-of-root candidate."""
    try:
        return _relative(Path(root), Path(candidate)), None
    except ValueError:
        return None, f"skipped out-of-root recognized path: {candidate}"


def sha256_file(path: Path) -> str:
    """Return a lowercase SHA-256 digest using bounded memory."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _input_paths(project: Path, cfg: dict[str, Any]) -> set[Path]:
    paths: set[Path] = {project / "mathmodel.json"}
    inputs = cfg.get("inputs", {})
    for field in ("statements", "attachments"):
        for relative in inputs.get(field, []):
            paths.add(resolve_project_path(project, relative))
    paper = cfg.get("paper", {})
    if paper.get("main"):
        paths.add(resolve_project_path(project, paper["main"]))
    return paths


def _recognized_paths(project: Path) -> set[Path]:
    ignored = {".mathmodel", ".git", "__pycache__"}
    paths: set[Path] = set()
    for path in project.rglob("*"):
        if not path.is_file() or any(part in ignored for part in path.parts):
            continue
        if path.name == ".gitkeep":
            continue
        if path.suffix.lower() in _TYPE_BY_SUFFIX:
            paths.add(path)
    return paths


def inventory_project(project: Path, cfg: dict[str, Any]) -> dict[str, Any]:
    """Inventory configured inputs and recognized project files."""
    root = Path(project).resolve()
    paths = _input_paths(root, cfg) | _recognized_paths(root)
    files = []
    warnings = []
    for path in sorted(paths, key=lambda item: str(item).casefold()):
        relative, warning = recognized_path_decision(root, path)
        if warning:
            warnings.append(warning)
        if relative is None:
            continue
        entry: dict[str, Any] = {
            "path": relative,
            "type": _TYPE_BY_SUFFIX.get(path.suffix.lower(), "config" if path.name == "mathmodel.json" else "file"),
            "exists": path.is_file(),
        }
        if path.is_file():
            stat = path.stat()
            entry.update({
                "size": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                "sha256": sha256_file(path),
                "status": "OK",
            })
        else:
            entry.update({"size": 0, "modified_at": None, "status": "WARN"})
        files.append(entry)
    return {
        "project": str(root),
        "generated_at": _now(),
        "status": "WARN" if warnings or any(item["status"] == "WARN" for item in files) else "SUCCESS",
        "files": files,
        "warnings": warnings,
    }


def _stage(status: str = "PENDING") -> dict[str, Any]:
    return {
        "status": status,
        "started_at": None,
        "finished_at": None,
        "exit_code": None,
        "outputs": [],
        "warnings": [],
        "errors": [],
        "output_inventory": [],
    }


def new_run(project: Path, command: str, cfg: dict[str, Any], inventory: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    """Create a unique run directory and write its initial manifest."""
    root = Path(project).resolve()
    runs = root / ".mathmodel" / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    input_hashes = {
        item["path"]: item["sha256"]
        for item in inventory.get("files", [])
        if item.get("exists") and item.get("sha256")
    }
    created_at = _now()
    hash_input = json.dumps({"config": cfg, "input_hashes": input_hashes}, ensure_ascii=False, sort_keys=True).encode()
    base = f"{datetime.fromisoformat(created_at).strftime('%Y%m%dT%H%M%SZ')}-{hashlib.sha256(hash_input).hexdigest()[:12]}"
    run_dir = runs / base
    suffix = 0
    while run_dir.exists():
        suffix += 1
        run_dir = runs / f"{base}-{suffix}"
    run_dir.mkdir()
    manifest = {
        "run_id": run_dir.name,
        "created_at": created_at,
        "command": command,
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "config": cfg,
        "inventory": inventory,
        "input_hashes": input_hashes,
        "stages": {},
    }
    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest_path, manifest


def update_stage(manifest_path: Path, stage: str, status: str, **fields: Any) -> None:
    """Update one stage while retaining all existing stage evidence."""
    path = Path(manifest_path)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    current = dict(manifest.setdefault("stages", {}).get(stage, _stage()))
    for field in _STAGE_FIELDS:
        current.setdefault(field, _stage()[field])
    current["status"] = status
    if current["started_at"] is None:
        current["started_at"] = _now()
    if status in {"SUCCESS", "WARN", "ERROR", "FAILED"}:
        current["finished_at"] = _now()
    for key, value in fields.items():
        key = {"output": "outputs", "warning": "warnings", "error": "errors"}.get(key, key)
        if key not in _STAGE_FIELDS:
            continue
        if key in {"outputs", "warnings", "errors"}:
            existing = current[key]
            values = value if isinstance(value, list) else [value]
            current[key] = existing + values
        else:
            current[key] = value
    manifest["stages"][stage] = current
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
