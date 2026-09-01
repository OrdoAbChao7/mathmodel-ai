"""Release-candidate packaging with strict evidence and page gates."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import load_config
from .compliance import requires_formal_compliance
from .manifest import inventory_project, sha256_file


def _record(rule: str, status: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"rule": rule, "status": status, "message": message, **extra}


def _load_report(project: Path, report: dict[str, Any] | str | Path | None) -> dict[str, Any]:
    if isinstance(report, dict):
        return report
    path = Path(report) if report else project / "build" / "quality-report.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _selected_pdf(project: Path, report: dict[str, Any]) -> Path | None:
    compile_info = report.get("compile") if isinstance(report.get("compile"), dict) else {}
    declared = compile_info.get("pdf")
    if declared is not None:
        candidates = [declared]
    else:
        metrics = report.get("page_metrics") if isinstance(report.get("page_metrics"), dict) else {}
        candidates = [
            report.get("pdf"),
            report.get("build", {}).get("pdf") if isinstance(report.get("build"), dict) else None,
            metrics.get("pdf"),
        ]
    for candidate in candidates:
        if isinstance(candidate, str):
            path = Path(candidate)
            if not path.is_absolute():
                path = project / path
            try:
                path = path.resolve()
                path.relative_to(project.resolve())
            except ValueError:
                continue
            if path.is_file():
                return path
    return None


def _gate_records(report: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    quality = report.get("quality") if isinstance(report.get("quality"), dict) else {}
    records.extend(
        gate for gate in (report.get("page_gates", []) if isinstance(report.get("page_gates"), list) else [])
        if isinstance(gate, dict) and gate.get("status") != "PASS"
    )
    records.extend(quality.get("hard_failures", []) if isinstance(quality.get("hard_failures"), list) else [])
    if quality.get("release_status") != "PASS":
        records.append(_record("PACKAGE-QUALITY-001", "FAIL", "quality release status is not PASS", release_status=quality.get("release_status")))
    if report.get("status") not in (None, "PASS"):
        records.append(_record("PACKAGE-REPORT-001", "FAIL", "build or audit report is not PASS", report_status=report.get("status")))
    compliance = report.get("compliance")
    if isinstance(compliance, dict) and compliance.get("status") not in (None, "PASS", "NOT_APPLICABLE"):
        records.append(_record("PACKAGE-COMPLIANCE-001", "FAIL", "CUMCM compliance status is not PASS", compliance_status=compliance.get("status")))
    hashes = report.get("hash_checks")
    if not isinstance(hashes, list) or not hashes:
        records.append(_record("PACKAGE-HASH-001", "FAIL", "source/output hash evidence is missing"))
    elif any(not isinstance(item, dict) or item.get("status") != "PASS" for item in hashes):
        records.append(_record("PACKAGE-HASH-001", "FAIL", "source/output hash evidence contains a failure"))
    return records


def _path_hashes(project: Path, report: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    checks: list[dict[str, Any]] = []
    files: list[dict[str, Any]] = []
    for key in ("source_manifest", "validation_report", "reproducibility_summary"):
        value = report.get(key)
        if isinstance(value, str):
            path = Path(value)
            path = path if path.is_absolute() else project / path
            try:
                path = path.resolve()
                path.relative_to(project.resolve())
            except ValueError:
                checks.append(_record("PACKAGE-PATH-001", "FAIL", f"{key} is outside project", path=str(value)))
                continue
            if path.is_file():
                files.append({"kind": key, "path": path.relative_to(project.resolve()).as_posix(), "sha256": sha256_file(path)})
            else:
                checks.append(_record("PACKAGE-EVIDENCE-001", "FAIL", f"{key} is missing", path=str(value)))
    return checks, files


def package(project: Path, report: dict[str, Any] | str | Path | None = None) -> dict[str, Any]:
    """Create a release bundle, or return BLOCKED with actionable checks."""
    root = Path(project).resolve()
    try:
        cfg = load_config(root)
        loaded = _load_report(root, report)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {"status": "BLOCKED", "checks": [_record("PACKAGE-INPUT-001", "FAIL", str(exc))]}
    checks = list(_gate_records(loaded))
    compliance = loaded.get("compliance")
    if requires_formal_compliance(cfg):
        if not isinstance(compliance, dict) or compliance.get("status") != "PASS":
            checks.append(_record("PACKAGE-COMPLIANCE-001", "FAIL", "formal competition package requires PASS CUMCM compliance evidence"))
        g1 = loaded.get("g1")
        if not isinstance(g1, dict) or g1.get("status") != "PASS":
            checks.append(_record("PACKAGE-INTERPRETATION-001", "FAIL", "formal competition package requires PASS G1 interpretation evidence"))
    quality = loaded.get("quality") if isinstance(loaded.get("quality"), dict) else {}
    manual = quality.get("manual_review")
    if manual != "COMPLETE":
        checks.append(_record("PACKAGE-MANUAL-001", "FAIL", "manual review/checklist is unresolved", manual_review=manual))
    metrics = loaded.get("page_metrics") if isinstance(loaded.get("page_metrics"), dict) else loaded.get("metrics", {})
    if metrics.get("status") != "SUCCESS":
        checks.append(_record("PACKAGE-PAGE-001", "FAIL", "page metrics are not successful", metrics_status=metrics.get("status")))
    pdf = _selected_pdf(root, loaded)
    if pdf is None:
        checks.append(_record("PACKAGE-PDF-001", "FAIL", "selected current PDF is missing or outside project"))
    extra_checks, evidence_files = _path_hashes(root, loaded)
    checks.extend(extra_checks)
    if checks:
        return {"status": "BLOCKED", "checks": checks, "project": str(root)}
    if not isinstance(metrics.get("total_pages"), int) or metrics["total_pages"] <= 0:
        return {"status": "BLOCKED", "project": str(root), "checks": [_record("PACKAGE-PAGE-002", "FAIL", "total page count is absent")]} 
    digest = sha256_file(pdf)
    release_dir = root / "release"
    release_dir.mkdir(parents=True, exist_ok=True)
    pdf_name = f"{cfg['paper']['jobname']}-{metrics['total_pages']}p-{digest[:8]}.pdf"
    destination = release_dir / pdf_name
    shutil.copy2(pdf, destination)
    snapshot = inventory_project(root, cfg)
    package_manifest = {
        "status": "PASS",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "project": str(root),
        "pdf": {"path": destination.relative_to(root).as_posix(), "sha256": sha256_file(destination), "pages": metrics["total_pages"]},
        "source_snapshot": snapshot,
        "evidence": evidence_files,
        "quality_report": loaded,
        "reproducibility": {"config_sha256": sha256_file(root / "mathmodel.json")},
    }
    manifest_path = release_dir / f"{cfg['paper']['jobname']}-{digest[:8]}-package-manifest.json"
    manifest_path.write_text(json.dumps(package_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "PASS", "pdf": str(destination), "manifest": str(manifest_path), "package_dir": str(release_dir), "checks": []}
