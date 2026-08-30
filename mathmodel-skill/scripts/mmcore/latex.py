"""Safe, repeatable LaTeX compilation helpers."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


_SAFE_JOBNAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_PLACEHOLDER_RE = re.compile(r"\bTODO\b|\bTBD\b|待补充|将在后续任务中补充", re.IGNORECASE)
_OVERFULL_RE = re.compile(r"Overfull\s+\\+hbox\s+\((?P<points>\d+(?:\.\d+)?)pt too wide\)", re.IGNORECASE)


def _record(rule: str, message: str, *, path: Path | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "rule": rule,
        "message": message,
        "path": str(path) if path is not None else None,
        "evidence": {} if evidence is None else evidence,
    }


def _inside_project(project: Path, candidate: Path) -> bool:
    return candidate == project or project in candidate.parents


def find_latex_placeholders(path: Path) -> list[dict[str, Any]]:
    """Return release-blocking placeholder tokens found in a LaTeX source file."""
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    matches: list[dict[str, Any]] = []
    for match in _PLACEHOLDER_RE.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        column = match.start() - text.rfind("\n", 0, match.start())
        matches.append({"token": match.group(0), "line": line, "column": column})
    return matches


def _scan_log(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not path.is_file():
        return [], []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [], [_record("LATEX-LOG-001", "could not read LaTeX log", path=path, evidence={"error": str(exc)})]
    warnings: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    if "undefined references" in text.lower() or "there were undefined references" in text.lower():
        errors.append(_record("LATEX-UNDEFINED-REF-001", "LaTeX reported undefined references", path=path))
    if "citation" in text.lower() and "undefined" in text.lower():
        errors.append(_record("LATEX-UNDEFINED-CITATION-001", "LaTeX reported undefined citations", path=path))
    for match in _OVERFULL_RE.finditer(text):
        points = float(match.group("points"))
        record = _record(
            "LATEX-OVERFULL-002" if points > 2 else "LATEX-OVERFULL-001",
            "LaTeX reported an overfull box above the 2 pt limit" if points > 2 else "LaTeX reported an overfull box within the 2 pt warning limit",
            path=path,
            evidence={"points": points, "threshold": 2},
        )
        (errors if points > 2 else warnings).append(record)
    if "fatal error" in text.lower() or "emergency stop" in text.lower() or "undefined control sequence" in text.lower():
        errors.append(_record("LATEX-LOG-FATAL-001", "LaTeX log contains a fatal error", path=path))
    return warnings, errors


def _deduplicate(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str | None]] = set()
    kept: list[dict[str, Any]] = []
    for record in records:
        key = (record["rule"], record.get("path"))
        if key not in seen:
            seen.add(key)
            kept.append(record)
    return kept


def compile_latex(project: Path, main: Path, engine: str, jobname: str) -> dict[str, Any]:
    """Compile ``main`` twice in the project's private ``build/latex`` directory."""
    root = Path(project).resolve()
    source = Path(main).resolve()
    output_dir = root / "build" / "latex"
    pdf_path = output_dir / f"{jobname}.pdf"
    aux_path = output_dir / f"{jobname}.aux"
    result: dict[str, Any] = {
        "status": "FAILED",
        "project": str(root),
        "main": str(source),
        "engine": engine,
        "jobname": jobname,
        "output_dir": str(output_dir),
        "pdf": str(pdf_path),
        "aux": str(aux_path),
        "exit_codes": [],
        "commands": [],
        "logs": [],
        "warnings": [],
        "errors": [],
    }
    if not isinstance(engine, str) or not engine.strip():
        result["errors"].append(_record("LATEX-ENGINE-001", "LaTeX engine must be a non-empty command"))
        return result
    if not _SAFE_JOBNAME.fullmatch(jobname):
        result["errors"].append(_record("LATEX-JOBNAME-001", "LaTeX jobname contains unsafe characters", evidence={"jobname": jobname}))
        return result
    if not _inside_project(root, source):
        result["errors"].append(_record("LATEX-MAIN-PATH-001", "LaTeX main file must stay inside the project", path=source))
        return result
    if not source.is_file():
        result["errors"].append(_record("LATEX-MAIN-001", "LaTeX main file does not exist", path=source))
        return result
    placeholders = find_latex_placeholders(source)
    if placeholders:
        result["errors"].append(
            _record(
                "LATEX-PLACEHOLDER-001",
                "LaTeX source contains unresolved release-blocking placeholders",
                path=source,
                evidence={"placeholders": placeholders},
            )
        )
        return result

    output_dir.mkdir(parents=True, exist_ok=True)
    command = [
        engine,
        "-interaction=nonstopmode",
        "-halt-on-error",
        f"-output-directory={output_dir}",
        f"-jobname={jobname}",
        str(source),
    ]
    for pass_number in (1, 2):
        result["commands"].append(command.copy())
        stdout_path = output_dir / f"pass-{pass_number}.stdout.log"
        stderr_path = output_dir / f"pass-{pass_number}.stderr.log"
        try:
            completed = subprocess.run(
                command,
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
                shell=False,
            )
        except FileNotFoundError as exc:
            result["errors"].append(_record("LATEX-ENGINE-001", "LaTeX engine is unavailable", evidence={"error": str(exc), "engine": engine}))
            break
        except OSError as exc:
            result["errors"].append(_record("LATEX-RUN-001", "could not start LaTeX", evidence={"error": str(exc), "engine": engine}))
            break
        stdout_path.write_text(completed.stdout or "", encoding="utf-8")
        stderr_path.write_text(completed.stderr or "", encoding="utf-8")
        result["logs"].extend([str(stdout_path), str(stderr_path)])
        result["exit_codes"].append(completed.returncode)
        engine_log = output_dir / f"{jobname}.log"
        if engine_log.is_file():
            preserved_log = output_dir / f"pass-{pass_number}.{jobname}.log"
            shutil.copyfile(engine_log, preserved_log)
            result["logs"].append(str(preserved_log))
            warnings, errors = _scan_log(preserved_log)
            result["warnings"].extend(warnings)
            result["errors"].extend(errors)
        if completed.returncode != 0:
            result["errors"].append(
                _record(
                    "LATEX-COMPILE-001",
                    "LaTeX compilation pass failed",
                    evidence={"pass": pass_number, "exit_code": completed.returncode},
                )
            )
            break

    if len(result["exit_codes"]) == 2 and all(code == 0 for code in result["exit_codes"]):
        if not pdf_path.is_file():
            result["errors"].append(_record("LATEX-PDF-001", "LaTeX completed without producing a PDF", path=pdf_path))
        if not aux_path.is_file():
            result["errors"].append(_record("LATEX-AUX-001", "LaTeX completed without producing an AUX file", path=aux_path))
    result["warnings"] = _deduplicate(result["warnings"])
    result["errors"] = _deduplicate(result["errors"])
    if len(result["exit_codes"]) == 2 and all(code == 0 for code in result["exit_codes"]) and not result["errors"]:
        result["status"] = "SUCCESS"
    return result
