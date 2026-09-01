"""Validation and path handling for a mathmodel project configuration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    """Raised when a project configuration does not satisfy its contract."""


CURRENT_CONFIG_SCHEMA_VERSION = 2
LEGACY_CONFIG_SCHEMA_VERSIONS = {1}


_PROBLEM_TYPES = {
    "forecasting",
    "optimization",
    "evaluation",
    "mechanism",
    "simulation",
    "classification",
    "statistics",
    "hybrid",
}
_EXECUTION_MODES = {"research_autonomous", "competition_assisted", "competition_max"}
_RIGOR_MODES = {"fast", "standard", "max"}
_REQUIRED_TOP_LEVEL = {
    "schema_version",
    "project_id",
    "title",
    "contest",
    "problem_type",
    "inputs",
    "commands",
    "paper",
    "quality",
}


def _require_mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"{name} must be an object")
    return value


def _require_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ConfigError(f"{name} must be a non-empty string")
    return value


def _validate_page_range(value: Any, name: str) -> None:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(isinstance(item, bool) or not isinstance(item, int) for item in value)
        or value[0] > value[1]
    ):
        raise ConfigError(f"{name} must contain two integer bounds in ascending order")


def _validate_relative_paths(config: dict[str, Any], project: Path) -> None:
    inputs = _require_mapping(config["inputs"], "inputs")
    for field in ("statements", "attachments"):
        values = inputs.get(field)
        if not isinstance(values, list):
            raise ConfigError(f"inputs.{field} must be an array")
        for index, value in enumerate(values):
            relative = _require_string(value, f"inputs.{field}[{index}]")
            resolve_project_path(project, relative)

    paper = _require_mapping(config["paper"], "paper")
    main = _require_string(paper.get("main"), "paper.main")
    resolve_project_path(project, main)


def _validate_benchmark(config: dict[str, Any]) -> None:
    benchmark = config.get("benchmark")
    if benchmark is None:
        return
    benchmark = _require_mapping(benchmark, "benchmark")
    for field in ("baseline_command", "candidate_command"):
        command = benchmark.get(field)
        if not isinstance(command, list) or not command or any(not isinstance(item, str) or not item for item in command):
            raise ConfigError(f"benchmark.{field} must be a non-empty array of strings")
    repeats = benchmark.get("repeats", 1)
    if isinstance(repeats, bool) or not isinstance(repeats, int) or not 1 <= repeats <= 20:
        raise ConfigError("benchmark.repeats must be an integer in [1, 20]")
    timeout = benchmark.get("timeout_seconds", 300)
    if isinstance(timeout, bool) or not isinstance(timeout, int) or not 1 <= timeout <= 3600:
        raise ConfigError("benchmark.timeout_seconds must be an integer in [1, 3600]")


def load_config(project: Path) -> dict[str, Any]:
    """Load and validate UTF-8 ``mathmodel.json`` without modifying it."""
    project = Path(project).resolve()
    config_path = project / "mathmodel.json"
    try:
        with config_path.open("r", encoding="utf-8") as stream:
            config = json.load(stream)
    except FileNotFoundError as exc:
        raise ConfigError(f"missing configuration: {config_path}") from exc
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConfigError(f"invalid configuration file: {config_path}") from exc

    config = _require_mapping(config, "configuration root")
    missing = sorted(_REQUIRED_TOP_LEVEL - config.keys())
    if missing:
        raise ConfigError(f"missing required keys: {', '.join(missing)}")
    schema_version = config.get("schema_version")
    if isinstance(schema_version, bool) or not isinstance(schema_version, int) or schema_version not in ({CURRENT_CONFIG_SCHEMA_VERSION} | LEGACY_CONFIG_SCHEMA_VERSIONS):
        raise ConfigError("schema_version must be 1 (legacy) or 2")
    # Keep legacy files immutable on disk while exposing one current in-memory
    # contract to every downstream stage.
    if schema_version in LEGACY_CONFIG_SCHEMA_VERSIONS:
        config = dict(config)
        config["schema_version"] = CURRENT_CONFIG_SCHEMA_VERSION
    for field in ("project_id", "title", "contest"):
        _require_string(config[field], field)
    if config["problem_type"] not in _PROBLEM_TYPES:
        raise ConfigError("problem_type is not supported")
    execution_mode = config.get("execution_mode", "research_autonomous")
    if not isinstance(execution_mode, str) or execution_mode not in _EXECUTION_MODES:
        raise ConfigError("execution_mode is not supported")
    rigor = config.get("rigor", "standard")
    if not isinstance(rigor, str) or rigor not in _RIGOR_MODES:
        raise ConfigError("rigor must be one of: fast, standard, max")

    commands = _require_mapping(config["commands"], "commands")
    analyze = commands.get("analyze")
    if not isinstance(analyze, list) or any(not isinstance(item, str) for item in analyze):
        raise ConfigError("commands.analyze must be an array of strings")
    _validate_benchmark(config)

    paper = _require_mapping(config["paper"], "paper")
    for field in ("main", "engine", "jobname"):
        _require_string(paper.get(field), f"paper.{field}")

    quality = _require_mapping(config["quality"], "quality")
    for field in ("target_total_pages", "target_body_pages"):
        _validate_page_range(quality.get(field), f"quality.{field}")
    ratio = quality.get("max_appendix_body_ratio")
    if isinstance(ratio, bool) or not isinstance(ratio, (int, float)) or not 0 <= ratio <= 1:
        raise ConfigError("quality.max_appendix_body_ratio must be in [0, 1]")
    for field in ("minimum_score", "minimum_figures"):
        value = quality.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ConfigError(f"quality.{field} must be a non-negative integer")
    roles = quality.get("required_figure_roles")
    if not isinstance(roles, list) or any(not isinstance(role, str) for role in roles):
        raise ConfigError("quality.required_figure_roles must be an array of strings")

    _validate_relative_paths(config, project)
    return config


def resolve_project_path(project: Path, relative: str) -> Path:
    """Resolve a project-relative path and reject paths outside the project root."""
    root = Path(project).resolve()
    candidate = Path(relative)
    if candidate.is_absolute():
        raise ConfigError(f"path must be relative to project: {relative}")
    resolved = (root / candidate).resolve()
    if resolved != root and root not in resolved.parents:
        raise ConfigError(f"path escapes project root: {relative}")
    return resolved
