"""Safe, reproducible execution for project-specific solver commands."""

from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from typing import Any

from .manifest import sha256_file


DEFAULT_TIMEOUT_SECONDS = 300


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _error(rule: str, message: str, **evidence: Any) -> dict[str, Any]:
    return {"rule": rule, "severity": "FAIL", "message": message, "evidence": evidence}


def _within(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _argument_path_text(argument: str) -> str:
    """Extract a path-like value under the runner's conservative fail-closed policy.

    Every positional argument and every ``--key=value`` value is checked as a
    possible project path. This can reject scalar values that resemble paths,
    but prevents an option-value path from bypassing containment validation.
    """
    return argument.split("=", 1)[1] if argument.startswith("-") and "=" in argument else argument


def _resolve_existing_path(project: Path, value: str) -> Path | None:
    """Resolve an existing path-like argument relative to the project root."""
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate.resolve()
    candidate = project / candidate
    if candidate.exists() or candidate.is_symlink():
        return candidate.resolve()
    return None


def _is_relative_path_like_executable(value: str) -> bool:
    """Distinguish project-relative executable paths from bare PATH names."""
    return not Path(value).is_absolute() and (value.startswith(".") or "/" in value or "\\" in value)


def _validate_command(project: Path, command: object) -> list[dict[str, Any]]:
    if not isinstance(command, list) or not command or any(not isinstance(item, str) or not item or "\0" in item for item in command):
        return [_error("RUNNER-COMMAND-002", "command must be a non-empty array of non-empty strings")]

    errors: list[dict[str, Any]] = []
    executable = command[0]
    if _is_relative_path_like_executable(executable):
        candidate = Path(executable)
        if ".." in candidate.parts:
            errors.append(_error("RUNNER-PATH-001", "relative executable path escapes the project-scoped working directory", argument=executable))
        else:
            resolved = _resolve_existing_path(project, executable)
            if resolved is not None and not _within(project, resolved):
                errors.append(_error("RUNNER-PATH-001", "relative executable path resolves outside the project-scoped working directory", argument=executable, resolved_path=str(resolved)))
    for argument in command[1:]:
        candidate_text = _argument_path_text(argument)
        candidate = Path(candidate_text)
        if candidate.is_absolute() or ".." in candidate.parts:
            errors.append(_error("RUNNER-PATH-001", "command argument escapes the project-scoped working directory", argument=argument))
            continue
        resolved = _resolve_existing_path(project, candidate_text)
        if resolved is not None and not _within(project, resolved):
            errors.append(_error("RUNNER-PATH-001", "command argument resolves outside the project-scoped working directory", argument=argument, resolved_path=str(resolved)))
    return errors


def _log_paths(project: Path, run_dir: Path, stage: str) -> tuple[Path, Path] | None:
    if not _within(project, run_dir):
        return None
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir / f"{stage}.stdout.log", run_dir / f"{stage}.stderr.log"


def _reproducibility(project: Path, command: list[str]) -> dict[str, Any]:
    config = project / "mathmodel.json"
    code_hashes: dict[str, str] = {}
    for argument in command[1:]:
        candidate = _resolve_existing_path(project, _argument_path_text(argument))
        if candidate is None:
            continue
        if _within(project, candidate) and candidate.is_file():
            code_hashes[candidate.relative_to(project).as_posix()] = sha256_file(candidate)
    return {
        "config_sha256": sha256_file(config) if config.is_file() else None,
        "code_hashes": code_hashes,
        "working_directory": str(project),
    }


def _output_fingerprints(run_dir: Path) -> dict[str, str]:
    from .analysis import collect_outputs

    return {item["path"]: item["sha256"] for item in collect_outputs(run_dir).get("files", [])}


def _attach_output_inventory(result: dict[str, Any], run_dir: Path, before: dict[str, str]) -> dict[str, Any]:
    from .analysis import collect_outputs

    inventory = collect_outputs(run_dir)
    inventory["generated_files"] = [
        item for item in inventory.get("files", [])
        if item.get("kind") == "generated_output" and before.get(item["path"]) != item["sha256"]
    ]
    result["output_inventory"] = inventory
    return result


def run_project_command(project: Path, command: object, run_dir: Path, stage: str) -> dict[str, Any]:
    """Run a command array without a shell and retain machine-readable evidence."""
    root = Path(project).resolve()
    target_run_dir = Path(run_dir).resolve()
    started_at = _now()
    errors = _validate_command(root, command)
    paths = _log_paths(root, target_run_dir, stage)
    stdout_path = str(target_run_dir / f"{stage}.stdout.log")
    stderr_path = str(target_run_dir / f"{stage}.stderr.log")
    stdout = ""
    stderr = ""
    if paths is None:
        return {
            "stage": stage,
            "status": "FAILED",
            "command": command if isinstance(command, list) else None,
            "started_at": started_at,
            "finished_at": _now(),
            "exit_code": None,
            "timed_out": False,
            "stdout": stdout,
            "stderr": stderr,
            "stdout_path": stdout_path,
            "stderr_path": stderr_path,
            "errors": [_error("RUNNER-RUN-DIR-001", "run directory must remain inside the project root", run_dir=str(run_dir))],
            "warnings": [],
            "reproducibility": {},
        }

    stdout_file, stderr_file = paths
    before_outputs = _output_fingerprints(target_run_dir)
    if errors:
        stderr = "\n".join(error["message"] for error in errors) + "\n"
        stdout_file.write_text(stdout, encoding="utf-8")
        stderr_file.write_text(stderr, encoding="utf-8")
        return _attach_output_inventory({
            "stage": stage,
            "status": "FAILED",
            "command": command if isinstance(command, list) else None,
            "started_at": started_at,
            "finished_at": _now(),
            "exit_code": None,
            "timed_out": False,
            "stdout": stdout,
            "stderr": stderr,
            "stdout_path": str(stdout_file),
            "stderr_path": str(stderr_file),
            "errors": errors,
            "warnings": [],
            "reproducibility": {},
        }, target_run_dir, before_outputs)

    safe_command = list(command)
    environment = os.environ.copy()
    environment["MM_RUN_DIR"] = str(target_run_dir)
    environment["MM_PROJECT_DIR"] = str(root)
    started = monotonic()
    exit_code: int | None = None
    timed_out = False
    try:
        completed = subprocess.run(
            safe_command,
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=DEFAULT_TIMEOUT_SECONDS,
            check=False,
        )
        stdout, stderr = _text(completed.stdout), _text(completed.stderr)
        exit_code = completed.returncode
        if exit_code != 0:
            errors.append(_error("RUNNER-EXIT-001", "command exited with a non-zero status", exit_code=exit_code))
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout, stderr = _text(exc.stdout), _text(exc.stderr)
        errors.append(_error("RUNNER-TIMEOUT-001", "command exceeded its execution timeout", timeout_seconds=DEFAULT_TIMEOUT_SECONDS))
    except FileNotFoundError as exc:
        stderr = str(exc)
        errors.append(_error("RUNNER-COMMAND-001", "command executable was not found", executable=safe_command[0]))
    except OSError as exc:
        stderr = str(exc)
        errors.append(_error("RUNNER-OS-001", "command could not be started", error=str(exc)))

    stdout_file.write_text(stdout, encoding="utf-8")
    stderr_file.write_text(stderr, encoding="utf-8")
    return _attach_output_inventory({
        "stage": stage,
        "status": "SUCCESS" if not errors else "FAILED",
        "command": safe_command,
        "started_at": started_at,
        "finished_at": _now(),
        "duration_seconds": round(monotonic() - started, 6),
        "exit_code": exit_code,
        "timed_out": timed_out,
        "stdout": stdout,
        "stderr": stderr,
        "stdout_path": str(stdout_file),
        "stderr_path": str(stderr_file),
        "errors": errors,
        "warnings": [],
        "reproducibility": _reproducibility(root, safe_command),
    }, target_run_dir, before_outputs)


def run_solver(project: Path, command: list[str], run_dir: Path) -> dict[str, Any]:
    """Execute a configured solver from the project root.

    A bare command element zero is resolved through ``PATH``. An absolute
    command element zero is allowed for a configured interpreter such as
    ``sys.executable``. A relative path-like executable is resolved and must
    remain within the project root; all remaining arguments use the documented
    conservative path-like validation policy.
    """
    return run_project_command(project, command, run_dir, "solver")
