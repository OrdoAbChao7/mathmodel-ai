"""Real-case training runner for Phase 10.

Runs one private case end-to-end through the training loop:

    init workspace -> SOLVER (opencode run) -> deterministic audit
    -> JUDGE (opencode run) -> failure registry entry

Isolation model:
- The workspace receives ONLY the case's problem/ materials (never oracle/).
- Solver and Judge are separate opencode agents run non-interactively via
  `opencode run --agent ... --dir ...` with separate working directories.
- All local gates and evidence contracts remain authoritative; agent output
  is advisory evidence and can never set a gate to PASS by itself.

This file contains no private case data. Cases resolve at runtime from
`benchmarks-private/cases/` (gitignored).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PRIVATE_CASES = REPO_ROOT / "benchmarks-private" / "cases"
WORKSPACES = REPO_ROOT / "benchmark-workspaces"
REGISTRY_DIR = REPO_ROOT / "benchmarks-private" / "failure-registry"
SPLIT_MANIFEST = REPO_ROOT / "benchmarks-private" / "split-manifest.md"

FAILURE_TAGS = {
    "FRAMING", "MODEL_SELECTION", "DATA", "MATH", "VALIDATION",
    "UNCERTAINTY", "INNOVATION", "EVIDENCE", "WRITING", "FIGURE",
    "CITATION", "ORCHESTRATION", "TIME",
}


@dataclass
class StageResult:
    stage: str
    ok: bool
    detail: str


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_case(case_ref: str) -> tuple[dict, Path]:
    """Resolve a case by directory name (case-02) or case_id (wut-2026-07)."""
    if not PRIVATE_CASES.is_dir():
        raise SystemExit("benchmarks-private/cases not found")
    for d in sorted(PRIVATE_CASES.iterdir()):
        meta_path = d / "case.json"
        if not meta_path.is_file():
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if d.name == case_ref or meta.get("case_id") == case_ref:
            return meta, d
    raise SystemExit(f"case not found: {case_ref}")


def check_split(case_ref: str, meta: dict) -> None:
    manifest = SPLIT_MANIFEST.read_text(encoding="utf-8")
    if "CONFIRMED" not in manifest:
        raise SystemExit("split manifest is not confirmed; aborting")
    if "UNASSIGNED" in json.dumps(meta):
        raise SystemExit(f"case {case_ref} has split=UNASSIGNED; aborting")


def init_workspace(meta: dict, case_dir: Path, run_id: str) -> Path:
    ws = WORKSPACES / run_id
    if ws.exists():
        raise SystemExit(f"workspace already exists: {ws}")
    solver = ws / "solver"
    judge = ws / "judge"
    solver.mkdir(parents=True)
    judge.mkdir(parents=True)

    # Only problem/ materials go to the solver. oracle/ never leaves the case dir.
    shutil.copytree(case_dir / "problem", solver / "problem")
    (solver / "case-meta.json").write_text(
        json.dumps({k: v for k, v in meta.items() if k != "notes"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Judge gets problem/ plus a handoff copy of candidate artifacts after solve.
    shutil.copytree(case_dir / "problem", judge / "problem")
    (ws / "run-meta.json").write_text(
        json.dumps({"run_id": run_id, "case_id": meta["case_id"], "started_utc": _utc()},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return ws


def run_opencode(agent: str, cwd: Path, prompt: str, log_path: Path,
                  timeout_s: int, fmt: str = "json") -> tuple[int, str]:
    cmd = [
        "opencode", "run",
        "--agent", agent,
        "--format", fmt,
        "--title", f"{agent}:{cwd.name}",
        prompt,
    ]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    # Subagents must not scan user-level external skills (permission noise, drift).
    env["OPENCODE_DISABLE_EXTERNAL_SKILLS"] = "1"
    env["OPENCODE_DISABLE_CLAUDE_CODE_SKILLS"] = "1"
    with log_path.open("w", encoding="utf-8", errors="replace") as log:
        proc = subprocess.run(cmd, cwd=str(cwd), stdout=log, stderr=subprocess.STDOUT,
                              timeout=timeout_s, env=env)
    text = log_path.read_text(encoding="utf-8", errors="replace")
    return proc.returncode, text


SOLVER_COMPLETE_MARKER = "SOLVE-COMPLETE.txt"


def parse_agent_text(json_log: str) -> str:
    """Extract assistant text from opencode run --format json output.

    Observed event shapes in opencode 1.18.25:
      {"type":"text", "part":{"type":"text","text":"..."}}
      {"type":"message.part.updated", "part":{"type":"text","text":"..."}}
    """
    parts: list[str] = []
    for line in json_log.splitlines():
        line = line.strip()
        if not (line.startswith("{") and line.endswith("}")):
            continue
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            continue
        evt_type = evt.get("type")
        part = evt.get("part") or {}
        if (evt_type == "text" or evt_type == "message.part.updated") \
                and part.get("type") == "text":
            text = part.get("text") or ""
            if text.strip():
                parts.append(text)
    return "\n".join(parts)


def last_session_id(json_log: str) -> str | None:
    for line in reversed(json_log.splitlines()):
        line = line.strip()
        if not (line.startswith("{") and line.endswith("}")):
            continue
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            continue
        sid = evt.get("sessionID") or (evt.get("part") or {}).get("sessionID")
        if sid:
            return sid
    return None


def stage_solve(ws: Path, meta: dict, timeout_s: int, max_continues: int = 2) -> StageResult:
    solver_ws = ws / "solver"
    cli = REPO_ROOT / "mathmodel-skill" / "scripts" / "mathmodel.py"
    prompt = (
        f"Case: {meta['case_id']} ({meta.get('competition','')}). "
        f"The problem statement and official attachments are in ./problem/ of your "
        f"workspace. The local CLI is at: {cli}\n"
        "Do the complete solve: problem map, model selection with justification, "
        "reproducible analysis code, results with validation/falsification, and an "
        "evidence-bound paper draft. Keep every evidence JSON the CLI produces. "
        "Work only inside this workspace.\n"
        "IMPORTANT: work incrementally and write intermediate state to files so your "
        "progress survives a context reset. When the whole solve is finished, write a "
        f"one-line summary to ./{SOLVER_COMPLETE_MARKER} in your workspace root."
    )
    code, log = run_opencode("mathmodel-solver", solver_ws, prompt,
                             ws / "logs" / "solver.json", timeout_s)
    marker = solver_ws / SOLVER_COMPLETE_MARKER
    continues = 0
    while code == 0 and not marker.exists() and continues < max_continues:
        sid = last_session_id(log)
        if not sid:
            break
        continues += 1
        (ws / "logs" / f"solver-continue-{continues}.json").parent.mkdir(exist_ok=True, parents=True)
        code, log = run_opencode(
            "mathmodel-solver", solver_ws,
            "Your previous run ended before completion (context/output limit). "
            "Read your own workspace state (artifacts, analysis, paper) and continue "
            "the solve from exactly where you stopped. Finish validation and the "
            "evidence-bound paper draft, then write "
            f"./{SOLVER_COMPLETE_MARKER}.",
            ws / "logs" / f"solver-continue-{continues}.json", timeout_s)
    final_text = parse_agent_text(log)
    (ws / "logs" / "solver-final.txt").write_text(final_text, encoding="utf-8")
    ok = code == 0 and marker.exists()
    detail = f"exit={code} continues={continues} marker={marker.exists()}"
    return StageResult("solve", ok, detail)


def find_project_dir(solver_ws: Path) -> Path | None:
    """Locate the solver's project dir (marker file: mathmodel.json)."""
    if not solver_ws.is_dir():
        return None
    if (solver_ws / "mathmodel.json").is_file() or (solver_ws / "project.json").is_file():
        return solver_ws
    for p in sorted(solver_ws.iterdir()):
        if p.is_dir() and ((p / "mathmodel.json").is_file() or (p / "project.json").is_file()):
            return p
    return None


def stage_audit(ws: Path, timeout_s: int) -> StageResult:
    """Deterministic audit of the solver workspace via the local CLI.

    The audit command is run from the repo root against the solver project.
    Its JSON output is the authoritative evidence; agent prose is advisory.
    """
    solver_ws = ws / "solver"
    cli = REPO_ROOT / "mathmodel-skill" / "scripts" / "mathmodel.py"
    project = find_project_dir(solver_ws)
    if project is None:
        return StageResult("audit", False, "no mathmodel.json project found in solver workspace")
    out = ws / "eval" / "audit.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    code = subprocess.run(
        [sys.executable, str(cli), "audit", str(project), "--json"],
        cwd=str(REPO_ROOT), stdout=out.open("w", encoding="utf-8"),
        stderr=subprocess.STDOUT, timeout=timeout_s,
    ).returncode
    return StageResult("audit", code == 0, f"exit={code} project={project.name}")


def stage_judge(ws: Path, meta: dict, timeout_s: int) -> StageResult:
    judge_ws = ws / "judge"
    # Hand the judge the candidate evidence (paper, results, audit) without solver prose.
    candidate = judge_ws / "candidate"
    candidate.mkdir(exist_ok=True)
    audit = ws / "eval" / "audit.json"
    if audit.is_file():
        shutil.copy2(audit, candidate / "audit.json")
    solver_ws = ws / "solver"
    project = find_project_dir(solver_ws)
    if project is not None:
        paper_main = project / "paper" / "main.tex"
        if paper_main.is_file():
            shutil.copy2(paper_main, candidate / "paper-main.tex")
        for pdf in (project / "build").rglob("*.pdf"):
            shutil.copy2(pdf, candidate / f"paper-{pdf.name}")
            break
        for extra in ("artifacts", "results", "analysis"):
            d = project / extra
            if d.is_dir():
                shutil.copytree(d, candidate / extra, dirs_exist_ok=True,
                                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    prompt = (
        f"Blind-judge the candidate package in ./candidate/ for case {meta['case_id']}. "
        "The original problem is in ./problem/. Follow your evaluation procedure and "
        "return exactly the JSON object contract from your instructions. "
        "Return ONLY the JSON object as your final message, with no markdown fences."
    )
    code, log = run_opencode("mathmodel-judge", judge_ws, prompt,
                             ws / "logs" / "judge.json", timeout_s)
    text = parse_agent_text(log)
    report = _extract_json(text)
    if report is None:
        (ws / "logs" / "judge-raw.txt").write_text(text, encoding="utf-8")
        return StageResult("judge", False, "no JSON report found in judge output")
    (ws / "eval" / "judge_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return StageResult("judge", True, f"overall={report.get('overall')}")


def _extract_json(text: str) -> dict | None:
    """Extract the last JSON object from assistant text, tolerating fences."""
    cleaned = re.sub(r"```(?:json)?", "", text)
    dec = json.JSONDecoder()
    candidates = []
    for i, ch in enumerate(cleaned):
        if ch == "{":
            try:
                obj, _end = dec.raw_decode(cleaned[i:])
                candidates.append(obj)
            except json.JSONDecodeError:
                continue
    for obj in reversed(candidates):
        if isinstance(obj, dict) and "scores" in obj:
            return obj
    if candidates:
        return candidates[-1]
    return None


def stage_registry(ws: Path, meta: dict, stages: list[StageResult]) -> StageResult:
    audit_path = ws / "eval" / "audit.json"
    judge_path = ws / "eval" / "judge_report.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.is_file() else {}
    judge = json.loads(judge_path.read_text(encoding="utf-8")) if judge_path.is_file() else {}
    tags = sorted(set(t for t in (judge.get("failure_tags") or []) if t in FAILURE_TAGS))
    if not all(s.ok for s in stages):
        tags = sorted(set(tags or []) | {"ORCHESTRATION"})
    entry = {
        "schema_version": 1,
        "run_id": ws.name,
        "case_id": meta["case_id"],
        "recorded_utc": _utc(),
        "stages": [{"stage": s.stage, "ok": s.ok, "detail": s.detail} for s in stages],
        "failure_tags": tags,
        "judge_overall": judge.get("overall"),
        "top_improvement": judge.get("top_improvement"),
        "evidence_binding_violations": judge.get("evidence_binding_violations") or [],
        "audit_summary": _shrink(audit),
    }
    path = REGISTRY_DIR / f"{ws.name}.json"
    path.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")
    return StageResult("registry", True, str(path))


def _shrink(obj, depth: int = 0):
    if depth >= 3:
        return "..."
    if isinstance(obj, dict):
        return {k: _shrink(v, depth + 1) for k, v in list(obj.items())[:12]}
    if isinstance(obj, list):
        return [_shrink(v, depth + 1) for v in obj[:12]]
    if isinstance(obj, str) and len(obj) > 300:
        return obj[:300] + "..."
    return obj


def main() -> int:
    ap = argparse.ArgumentParser(description="Run one real case through the training loop.")
    ap.add_argument("case", help="case directory name (case-02) or case_id (wut-2026-07)")
    ap.add_argument("--solve-timeout", type=int, default=7200, help="solver timeout seconds")
    ap.add_argument("--judge-timeout", type=int, default=1800, help="judge timeout seconds")
    ap.add_argument("--skip-solve", action="store_true", help="reuse existing workspace, only eval/judge")
    ap.add_argument("--stage", choices=["audit", "judge", "registry"],
                    help="run only the selected stage (implies --skip-solve)")
    ap.add_argument("--resume-solve", action="store_true",
                    help="with --skip-solve: continue solving the existing workspace instead of re-init")
    args = ap.parse_args()

    meta, case_dir = load_case(args.case)
    check_split(args.case, meta)

    if args.skip_solve or args.stage:
        matches = sorted(WORKSPACES.glob(f"*-{meta['case_id']}"))
        if not matches:
            raise SystemExit("no existing workspace for --skip-solve")
        ws = matches[-1]
        stages: list[StageResult] = []
        if args.stage == "audit":
            stages = [stage_audit(ws, timeout_s=600)]
            print(f"[runner] audit: {stages[0].ok} {stages[0].detail}")
            return 0 if stages[0].ok else 1
        if args.stage == "judge":
            r = stage_judge(ws, meta, args.judge_timeout)
            print(f"[runner] judge: {r.ok} {r.detail}")
            return 0 if r.ok else 1
        if args.stage == "registry":
            r = stage_registry(ws, meta, [
                StageResult("solve", (ws / "solver" / SOLVER_COMPLETE_MARKER).exists(), "replayed"),
                StageResult("audit", (ws / "eval" / "audit.json").is_file(), "replayed"),
                StageResult("judge", (ws / "eval" / "judge_report.json").is_file(), "replayed"),
            ])
            print(f"[runner] registry: {r.ok} {r.detail}")
            return 0 if r.ok else 1
        if args.resume_solve:
            r = stage_solve(ws, meta, args.solve_timeout)
            print(f"[runner] solve(resume): {r.ok} {r.detail}")
            stages = [r]
    else:
        run_id = f"{_utc()}-{meta['case_id']}"
        ws = init_workspace(meta, case_dir, run_id)
        print(f"[runner] workspace: {ws}")
        r = stage_solve(ws, meta, args.solve_timeout)
        print(f"[runner] solve: {r.ok} {r.detail}")
        stages = [r]

    r = stage_audit(ws, timeout_s=600)
    print(f"[runner] audit: {r.ok} {r.detail}")
    stages.append(r)

    r = stage_judge(ws, meta, args.judge_timeout)
    print(f"[runner] judge: {r.ok} {r.detail}")
    stages.append(r)

    r = stage_registry(ws, meta, stages)
    print(f"[runner] registry: {r.ok} {r.detail}")

    return 0 if all(s.ok for s in stages) else 1


if __name__ == "__main__":
    raise SystemExit(main())
