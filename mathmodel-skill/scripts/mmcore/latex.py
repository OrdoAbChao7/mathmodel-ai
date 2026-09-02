"""Safe, repeatable LaTeX compilation helpers."""

from __future__ import annotations

import re
import shutil
import subprocess
import os
import sys
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
    if "major issue: so far, you have not checked for miktex updates" in text.lower():
        errors.append(_record(
            "LATEX-ENV-001",
            "MiKTeX setup is incomplete; check updates and initialize the local package database",
            path=path,
            evidence={"remedy": "Run MiKTeX Console update check, then refresh the user file database."},
        ))
    return warnings, errors


def _scan_process_output(text: str, path: Path) -> list[dict[str, Any]]:
    """Extract environment diagnostics emitted before a TeX log exists."""
    lowered = text.lower()
    if (
        "major issue: so far, you have not checked for miktex updates" in lowered
        or "it seems that this is a fresh tex installation" in lowered
        or ("log4cxx" in lowered and ("io exception" in lowered or "denied" in lowered or "拒绝访问" in text))
    ):
        return [_record(
            "LATEX-ENV-001",
            "MiKTeX setup is incomplete; check updates and initialize the local package database",
            path=path,
            evidence={"remedy": "Run MiKTeX Console update check, then refresh the user file database."},
        )]
    return []


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
    engine_command = engine
    configured_engine = Path(engine.replace("\\", "/"))
    suffix = configured_engine.suffix.lower()
    use_python_wrapper = False
    if suffix == ".py":
        resolved_engine = configured_engine if configured_engine.is_absolute() else (root / configured_engine).resolve()
        if resolved_engine.is_file():
            engine_command = str(resolved_engine)
            use_python_wrapper = True
    elif suffix in {".cmd", ".bat"} and not configured_engine.is_absolute():
        candidate_engine = (root / configured_engine).resolve()
        if candidate_engine.is_file():
            engine_command = str(candidate_engine)
    command = [
        engine_command,
        "-interaction=nonstopmode",
        "-halt-on-error",
        f"-output-directory={output_dir}",
        f"-jobname={jobname}",
        f"-aux-directory={output_dir}",
        str(source),
    ]
    if use_python_wrapper:
        command = [sys.executable, *command]
    # Windows batch wrappers are executable through the command interpreter,
    # but Python cannot launch them with shell=False.  The engine path is
    # already resolved from the project configuration and is checked by the
    # caller, so enable the platform-native interpreter only for .cmd/.bat
    # wrappers; ordinary engines retain shell=False.
    use_shell = os.name == "nt" and Path(engine_command).suffix.lower() in {".cmd", ".bat"}
    for pass_number in (1, 2):
        result["commands"].append(command.copy())
        stdout_path = output_dir / f"pass-{pass_number}.stdout.log"
        stderr_path = output_dir / f"pass-{pass_number}.stderr.log"
        try:
            completed = subprocess.run(
                command,
                # Keep the project root as the process boundary.  A configured
                # wrapper may change into the paper directory for source-
                # relative TeX assets, while fixture compilers and project
                # scripts continue to resolve from the documented root.
                cwd=root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                shell=use_shell,
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
        result["errors"].extend(_scan_process_output(completed.stdout or "", stdout_path))
        result["errors"].extend(_scan_process_output(completed.stderr or "", stderr_path))
        result["exit_codes"].append(completed.returncode)
        engine_log = output_dir / f"{jobname}.log"
        if engine_log.is_file():
            preserved_log = output_dir / f"pass-{pass_number}.{jobname}.log"
            shutil.copyfile(engine_log, preserved_log)
            result["logs"].append(str(preserved_log))
            warnings, errors = _scan_log(preserved_log)
            if pass_number == 1:
                # Forward references are expected before the first auxiliary
                # file has been fully written.  Keep strict diagnostics on
                # the final pass, where unresolved references are real
                # release blockers.
                errors = [
                    item for item in errors
                    if item["rule"] not in {
                        "LATEX-UNDEFINED-REF-001",
                        "LATEX-UNDEFINED-CITATION-001",
                    }
                ]
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
