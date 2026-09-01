"""G9 submission-readiness gate for formal CUMCM packages."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .config import load_config


_FORMAL_MODES = {"competition_assisted", "competition_max"}
_IDENTITY_PATTERNS = (
    r"姓名\s*[:：=]",
    r"学号\s*[:：=]",
    r"学校(?:名称)?\s*[:：=]",
    r"参赛队",
    r"指导教师",
)


def _check(rule: str, status: str, message: str, **evidence: Any) -> dict[str, Any]:
    return {"rule": rule, "status": status, "message": message, "evidence": evidence}


def _inside(root: Path, value: str) -> Path | None:
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    try:
        path = path.resolve()
        path.relative_to(root.resolve())
    except (OSError, ValueError):
        return None
    return path


def _load_report(root: Path, report: dict[str, Any] | None) -> dict[str, Any] | None:
    if isinstance(report, dict):
        return report
    try:
        value = json.loads((root / "build" / "quality-report.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _paper_files(root: Path, main: Path) -> tuple[list[Path], list[str]]:
    files: list[Path] = []
    errors: list[str] = []
    queue = [main]
    seen: set[Path] = set()
    while queue:
        current = queue.pop()
        if current in seen:
            continue
        seen.add(current)
        if not current.is_file():
            errors.append(f"missing TeX input: {current}")
            continue
        files.append(current)
        try:
            text = current.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"cannot read TeX input {current}: {exc}")
            continue
        for raw in re.findall(r"\\(?:input|include)\s*\{([^}]+)\}", text):
            candidate = Path(raw)
            if candidate.suffix == "":
                candidate = candidate.with_suffix(".tex")
            resolved = _inside(root, str(current.parent / candidate))
            if resolved is None:
                errors.append(f"TeX input escapes project: {raw}")
            else:
                queue.append(resolved)
    return files, errors


def _reference_check(root: Path, files: list[Path]) -> tuple[bool, dict[str, Any]]:
    combined = "\n".join(path.read_text(encoding="utf-8") for path in files)
    cited: set[str] = set()
    for group in re.findall(r"\\cite[a-zA-Z*]*\s*\{([^}]+)\}", combined):
        cited.update(item.strip() for item in group.split(",") if item.strip())
    reference_files = [
        path for path in files
        if path.suffix.lower() in {".tex", ".bib"}
        and ("reference" in path.name.lower() or path.suffix.lower() == ".bib" or "\\bibitem" in path.read_text(encoding="utf-8"))
    ]
    definitions = "\n".join(path.read_text(encoding="utf-8") for path in reference_files)
    defined = set(re.findall(r"\\bibitem(?:\[[^]]+\])?\s*\{([^}]+)\}", definitions))
    defined.update(re.findall(r"@[A-Za-z]+\s*\{\s*([^,\s]+)", definitions))
    missing = sorted(cited - defined)
    return not missing and bool(reference_files), {"cited": sorted(cited), "reference_files": [str(p.relative_to(root)) for p in reference_files], "missing": missing}


def _source_check(root: Path, config: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    commands = config.get("commands") if isinstance(config.get("commands"), dict) else {}
    found: list[str] = []
    for command in commands.values():
        if not isinstance(command, list):
            continue
        for token in command:
            if not isinstance(token, str) or not Path(token).suffix.lower() in {".py", ".m", ".r", ".jl", ".ipynb", ".cmd", ".sh"}:
                continue
            path = _inside(root, token)
            if path is not None and path.is_file():
                found.append(path.relative_to(root).as_posix())
    manifest_path = root / "artifacts" / "submission-manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False, {"error": "submission-manifest.json is missing or malformed"}
    materials = manifest.get("supporting_materials") if isinstance(manifest, dict) else None
    listed_sources = manifest.get("source_programs") if isinstance(manifest, dict) else None
    valid_lists = isinstance(materials, list) and bool(materials) and isinstance(listed_sources, list) and bool(listed_sources)
    invalid = []
    for value in (materials or []) + (listed_sources or []):
        if not isinstance(value, str) or (_inside(root, value) is None) or not _inside(root, value).is_file():
            invalid.append(value)
    configured_inputs = config.get("inputs") if isinstance(config.get("inputs"), dict) else {}
    required_materials = configured_inputs.get("attachments") if isinstance(configured_inputs.get("attachments"), list) else []
    material_set = {value.replace("\\", "/") for value in materials or [] if isinstance(value, str)}
    missing_materials = [value for value in required_materials if isinstance(value, str) and value.replace("\\", "/") not in material_set]
    return bool(found) and valid_lists and not invalid and not missing_materials, {"detected_programs": sorted(set(found)), "supporting_materials": materials, "source_programs": listed_sources, "invalid": invalid, "missing_configured_attachments": missing_materials}


def evaluate_submission(project: Path, config: dict[str, Any] | None = None, report: dict[str, Any] | None = None) -> dict[str, Any]:
    """Evaluate G9; formal mode is the only mode that can return RELEASE PASS."""
    root = Path(project).resolve()
    try:
        cfg = config if isinstance(config, dict) else load_config(root)
    except (OSError, ValueError, TypeError) as exc:
        return {"status": "FAIL", "checks": [_check("G9-CONFIG-001", "FAIL", "configuration cannot be loaded", error=str(exc))]}
    mode = cfg.get("execution_mode", "research_autonomous")
    if mode not in _FORMAL_MODES:
        return {"status": "NOT_APPLICABLE", "mode": mode, "checks": [_check("G9-MODE-001", "PASS", "G9 is reserved for formal competition modes", mode=mode)]}
    checks: list[dict[str, Any]] = []
    loaded = _load_report(root, report)
    if loaded is None:
        return {"status": "FAIL", "mode": mode, "checks": [_check("G9-REPORT-001", "FAIL", "quality report is missing or malformed")]}

    gates = {
        "compliance": loaded.get("compliance"),
        "g1": loaded.get("g1"),
        "g2": loaded.get("model_tournament", {}).get("g2") if isinstance(loaded.get("model_tournament"), dict) else None,
        "g3": loaded.get("model_tournament", {}).get("g3") if isinstance(loaded.get("model_tournament"), dict) else None,
        "g4": loaded.get("semantic_validation", {}).get("g4") if isinstance(loaded.get("semantic_validation"), dict) else None,
        "g5": loaded.get("semantic_validation", {}).get("g5") if isinstance(loaded.get("semantic_validation"), dict) else None,
        "g5.5": loaded.get("model_architecture"),
        "g6": loaded.get("results_freeze"),
        "g7": loaded.get("writer_package"),
        "g8": loaded.get("review_registry"),
    }
    gate_ok = all(isinstance(value, dict) and value.get("status") == "PASS" for value in gates.values())
    checks.append(_check("G9-GATE-001", "PASS" if gate_ok else "FAIL", "G0-G8 evidence is complete" if gate_ok else "one or more G0-G8 gates are not PASS", gates={key: value.get("status") if isinstance(value, dict) else None for key, value in gates.items()}))
    open_critical = loaded.get("review_registry", {}).get("open_critical") if isinstance(loaded.get("review_registry"), dict) else None
    critical_ok = isinstance(open_critical, list) and not open_critical
    checks.append(_check("G9-CRITICAL-001", "PASS" if critical_ok else "FAIL", "no open critical review findings", open_critical=open_critical))
    compile_info = loaded.get("compile") if isinstance(loaded.get("compile"), dict) else {}
    pdf = _inside(root, compile_info.get("pdf")) if isinstance(compile_info.get("pdf"), str) else None
    pdf_ok = compile_info.get("status") == "SUCCESS" and pdf is not None and pdf.is_file()
    checks.append(_check("G9-PDF-001", "PASS" if pdf_ok else "FAIL", "real PDF compilation evidence is current", pdf=str(pdf) if pdf else None))
    page_metrics = loaded.get("page_metrics") if isinstance(loaded.get("page_metrics"), dict) else {}
    page_gates = loaded.get("page_gates")
    pages_ok = page_metrics.get("status") == "SUCCESS" and isinstance(page_gates, list) and bool(page_gates) and all(isinstance(gate, dict) and gate.get("status") == "PASS" for gate in page_gates)
    checks.append(_check("G9-PAGE-001", "PASS" if pages_ok else "FAIL", "page metrics and page gates are PASS", total_pages=page_metrics.get("total_pages")))
    main_value = cfg.get("paper", {}).get("main") if isinstance(cfg.get("paper"), dict) else None
    main = _inside(root, main_value) if isinstance(main_value, str) else None
    files, input_errors = _paper_files(root, main) if main else ([], ["paper.main is missing or outside project"])
    readable_text: list[str] = []
    read_errors: list[str] = []
    for path in files:
        try:
            readable_text.append(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError) as exc:
            read_errors.append(str(exc))
    source_text = "\n".join(readable_text)
    anonymous = not any(re.search(pattern, source_text, re.IGNORECASE) for pattern in _IDENTITY_PATTERNS)
    checks.append(_check("G9-ANONYMITY-001", "PASS" if anonymous and not read_errors else "FAIL", "paper source contains no prohibited identity fields", input_errors=input_errors, read_errors=read_errors))
    references_ok, reference_evidence = _reference_check(root, files) if not input_errors and not read_errors else (False, {"missing_inputs": input_errors + read_errors})
    checks.append(_check("G9-REFERENCES-001", "PASS" if references_ok else "FAIL", "references and TeX inputs resolve", **reference_evidence))
    source_ok, source_evidence = _source_check(root, cfg)
    checks.append(_check("G9-SOURCE-001", "PASS" if source_ok else "FAIL", "source programs and supporting-material list are present", **source_evidence))
    ai_ledger = root / "artifacts" / "ai-usage-ledger.jsonl"
    ai_ok = ai_ledger.is_file() and bool(ai_ledger.read_text(encoding="utf-8").strip()) and bool(re.search(r"AI\s*(usage|使用|disclosure|声明)", source_text, re.IGNORECASE))
    checks.append(_check("G9-AI-001", "PASS" if ai_ok else "FAIL", "AI usage detail artifact and paper disclosure are present", ledger=str(ai_ledger)))
    hashes = loaded.get("hash_checks")
    hashes_ok = isinstance(hashes, list) and bool(hashes) and all(isinstance(item, dict) and item.get("status") == "PASS" for item in hashes)
    checks.append(_check("G9-HASH-001", "PASS" if hashes_ok else "FAIL", "release hashes are current", count=len(hashes) if isinstance(hashes, list) else 0))
    status = "PASS" if checks and all(item["status"] == "PASS" for item in checks) else "FAIL"
    return {"status": status, "mode": mode, "release_status": status, "checks": checks}
