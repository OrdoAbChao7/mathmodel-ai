"""Create and adopt mathmodel project scaffolding without overwriting user files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_DIRECTORIES = (
    "problem",
    "data/raw",
    "data/processed",
    "analysis/models",
    "analysis/tests",
    "artifacts",
    "paper/figures",
    "paper/tables",
    "build",
    ".mathmodel/runs",
)
_PROJECT_FILES = ("mathmodel.json", "analysis/run.py", "paper/main.tex")
_PROBLEM_TYPES = ("forecasting", "optimization", "evaluation", "mechanism", "simulation", "classification", "statistics", "hybrid")
_EXECUTION_MODES = ("research_autonomous", "competition_assisted", "competition_max")
_DOCUMENT_SUFFIXES = {".pdf", ".doc", ".docx", ".txt"}
_SCRIPT_SUFFIXES = {".py", ".m", ".r", ".jl", ".ipynb", ".sh"}


def _template_root() -> Path:
    return Path(__file__).resolve().parents[2] / "assets" / "project-template"


def _write_missing(path: Path, content: str) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def _ensure_directories(root: Path, created: list[Path]) -> None:
    for relative in _DIRECTORIES:
        directory = root / relative
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            created.append(directory)
        keep = directory / ".gitkeep"
        if _write_missing(keep, ""):
            created.append(keep)


def _config(project_id: str, title: str, problem_type: str, execution_mode: str = "research_autonomous") -> dict[str, Any]:
    config = {
        "schema_version": 2,
        "project_id": project_id,
        "title": title,
        "contest": "CUMCM",
        "problem_type": problem_type,
        "inputs": {"statements": ["problem/problem.pdf"], "attachments": ["data/raw/attachment.xlsx"]},
        "commands": {"analyze": ["python", "analysis/run.py"]},
        "paper": {"main": "paper/main.tex", "engine": "xelatex", "jobname": "paper"},
        "quality": {
            "target_total_pages": [32, 40],
            "target_body_pages": [26, 34],
            "max_appendix_body_ratio": 0.25,
            "minimum_score": 85,
            "minimum_figures": 8,
            "required_figure_roles": ["data", "method", "result", "validation"],
        },
        "orchestration": {
            "stages": ["build", "audit", "package"],
            "max_retries": 0,
        },
    }
    if execution_mode != "research_autonomous":
        config["execution_mode"] = execution_mode
    return config


def _workflow_guide(execution_mode: str) -> str:
    if execution_mode == "research_autonomous":
        return """# MathModel workflow\n\nThis project starts in `research_autonomous` mode. It is for training and benchmarking, not direct CUMCM submission.\n\nBefore formal submission, set `execution_mode` to `competition_assisted` or `competition_max` only after the team has prepared and reviewed the required evidence and human signoffs.\n"""
    return """# CUMCM human-governed workflow\n\nThis project was initialized in `{mode}` mode. The system will not treat generated artifacts as human judgment and will not create fake signoffs.\n\n1. Run `mathmodel inspect PROJECT --json` and prepare independent interpretation artifacts.\n2. Record a real `H1_PROBLEM_UNDERSTANDING` signoff in `artifacts/human-review-ledger.jsonl`.\n3. Complete candidate routes, baseline, method cards, and risk probes; record a real `H2_METHOD_SELECTION` signoff.\n4. Run experiments, machine validation, falsification, and coherence checks; record `H3_RESULT_VERIFICATION` only after reviewing numbers and figures.\n5. Complete paper/reviewer evidence, then record `H4_FINAL_SUBMISSION` for the exact final PDF and support files.\n6. Run `mathmodel run PROJECT --profile cumcm --mode {mode} --json`, then `submission` and `package`.\n\nMissing or stale checkpoints stop orchestration with `BLOCKED_HUMAN_INPUT`. Do not copy or invent approval records.\n""".format(mode=execution_mode)


def init_project(target: Path, project_id: str, title: str, problem_type: str, execution_mode: str = "research_autonomous") -> list[Path]:
    """Create a new project contract and directories, preserving existing files."""
    if problem_type not in _PROBLEM_TYPES:
        raise ValueError(f"unsupported problem type: {problem_type}")
    if execution_mode not in _EXECUTION_MODES:
        raise ValueError(f"unsupported execution mode: {execution_mode}")
    root = Path(target)
    root.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    _ensure_directories(root, created)
    files = {
        "mathmodel.json": json.dumps(_config(project_id, title, problem_type, execution_mode), ensure_ascii=False, indent=2) + "\n",
        "analysis/run.py": (_template_root() / "analysis-run.py").read_text(encoding="utf-8"),
        "paper/main.tex": (_template_root() / "paper" / "main.tex").read_text(encoding="utf-8"),
        "CUMCM-WORKFLOW.md": _workflow_guide(execution_mode),
    }
    for relative, content in files.items():
        path = root / relative
        if _write_missing(path, content):
            created.append(path)
    return created


def adopt_project(target: Path, execution_mode: str = "research_autonomous") -> list[Path]:
    """Add missing project metadata/directories and record a non-destructive inventory."""
    root = Path(target)
    if execution_mode not in _EXECUTION_MODES:
        raise ValueError(f"unsupported execution mode: {execution_mode}")
    root.mkdir(parents=True, exist_ok=True)
    preexisting = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name != "adoption-report.json"
    }
    created: list[Path] = []
    _ensure_directories(root, created)
    config_path = root / "mathmodel.json"
    if not config_path.exists():
        content = json.dumps(_config(root.name or "adopted-project", "Adopted project", "hybrid", execution_mode), ensure_ascii=False, indent=2) + "\n"
        if _write_missing(config_path, content):
            created.append(config_path)
    effective_mode = execution_mode
    try:
        existing_config = json.loads(config_path.read_text(encoding="utf-8"))
        configured_mode = existing_config.get("execution_mode") if isinstance(existing_config, dict) else None
        if configured_mode in _EXECUTION_MODES:
            effective_mode = configured_mode
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        pass
    inventory = _adoption_inventory(root)
    report = {
        "project": str(root.resolve()),
        "existing_files": inventory["existing_files"],
        "statements": inventory["statements"],
        "attachments": inventory["attachments"],
        "papers": inventory["papers"],
        "scripts": inventory["scripts"],
        "conflicts": sorted(path for path in _PROJECT_FILES if path in preexisting),
    }
    report_path = root / "adoption-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if report_path not in created:
        created.append(report_path)
    workflow_path = root / "CUMCM-WORKFLOW.md"
    if _write_missing(workflow_path, _workflow_guide(effective_mode)):
        created.append(workflow_path)
    return created


def _adoption_inventory(root: Path) -> dict[str, list[str]]:
    """Classify existing files using project-relative paths only."""
    paths = sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name != "adoption-report.json" and path.name != ".gitkeep"
    )
    categories = {"statements": [], "attachments": [], "papers": [], "scripts": []}
    for relative in paths:
        path = Path(relative)
        suffix = path.suffix.lower()
        if path.parts[:1] == ("data",) and path.parts[1:2] == ("raw",):
            categories["attachments"].append(relative)
        elif path.parts[:1] == ("problem",) and suffix in _DOCUMENT_SUFFIXES:
            categories["statements"].append(relative)
        elif suffix in {".tex", ".pdf"}:
            categories["papers"].append(relative)
        elif suffix in _SCRIPT_SUFFIXES:
            categories["scripts"].append(relative)
    return {"existing_files": paths, **categories}
