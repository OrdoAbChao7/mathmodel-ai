"""Version policy and explicit migration for project artifact contracts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CURRENT_ARTIFACT_SCHEMA_VERSION = 2
LEGACY_ARTIFACT_SCHEMA_VERSIONS = {1}


def supported_artifact_schema(value: Any) -> bool:
    return isinstance(value, dict) and not isinstance(value.get("schema_version"), bool) and value.get("schema_version") in ({CURRENT_ARTIFACT_SCHEMA_VERSION} | LEGACY_ARTIFACT_SCHEMA_VERSIONS)


def normalize_artifact(value: Any) -> dict[str, Any] | None:
    """Return a v2 in-memory view while leaving the source object untouched."""
    if not supported_artifact_schema(value):
        return None
    normalized = dict(value)
    normalized["schema_version"] = CURRENT_ARTIFACT_SCHEMA_VERSION
    return normalized


def migrate_artifacts(project: Path, *, dry_run: bool = False) -> dict[str, Any]:
    """Upgrade v1 JSON artifacts under ``artifacts/`` to v2 atomically per file."""
    root = Path(project).resolve()
    migrated: list[str] = []
    skipped: list[str] = []
    errors: list[dict[str, str]] = []
    artifact_root = root / "artifacts"
    for path in sorted(artifact_root.glob("*.json")) if artifact_root.is_dir() else []:
        relative = path.relative_to(root).as_posix()
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append({"path": relative, "error": str(exc)})
            continue
        if not isinstance(value, dict) or value.get("schema_version") != 1:
            skipped.append(relative)
            continue
        value["schema_version"] = CURRENT_ARTIFACT_SCHEMA_VERSION
        migrated.append(relative)
        if not dry_run:
            path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "FAIL" if errors else "PASS", "project": str(root), "dry_run": dry_run, "migrated": migrated, "skipped": skipped, "errors": errors}
