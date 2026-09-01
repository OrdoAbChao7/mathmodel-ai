"""Command-line entry point for the mathmodel paper factory."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mmcore.analysis import collect_outputs, run_analysis
from mmcore.authority import accept_external_status, load_json, validate_registry
from mmcore.config import ConfigError, load_config
from mmcore.compliance import evaluate_compliance
from mmcore.interpretation import evaluate_g1
from mmcore.model_tournament import evaluate_model_tournament
from mmcore.semantic_validation import evaluate_semantic_validation
from mmcore.architecture_freeze import evaluate_model_architecture, evaluate_results_freeze
from mmcore.paper_review import evaluate_review_registry, evaluate_writer_package
from mmcore.external_capabilities import evaluate_capability_configuration
from mmcore.orchestration.orchestrator import run_pipeline
from mmcore.contracts import REQUIRED_ARTIFACTS, validate_artifacts
from mmcore.manifest import inventory_project, new_run, update_stage, sha256_file
from mmcore.latex import compile_latex, find_latex_placeholders
from mmcore.pdfmetrics import evaluate_page_gates, measure_pdf
from mmcore.package import package as package_project
from mmcore.quality import score_quality
from mmcore.scaffold import adopt_project, init_project
from mmcore.runner import run_solver


def _write_quality_reports(
    project: Path,
    contract: dict,
    quality: dict,
    page_metrics: dict | None = None,
    page_gates: list[dict] | None = None,
    compile_result: dict | None = None,
    compliance: dict | None = None,
    g1: dict | None = None,
    model_tournament: dict | None = None,
    semantic_validation: dict | None = None,
    model_architecture: dict | None = None,
    results_freeze: dict | None = None,
    writer_package: dict | None = None,
    review_registry: dict | None = None,
    external_capabilities: dict | None = None,
) -> tuple[Path, Path, dict]:
    build = project / "build"
    build.mkdir(parents=True, exist_ok=True)
    page_metrics = page_metrics or {"status": "PENDING", "message": "PDF page metrics are unavailable."}
    page_gates = page_gates or []
    report = {
        "project": str(project),
        "contract": contract,
        "quality": quality,
        "page_metrics": page_metrics,
        "page_gates": page_gates,
        "compliance": compliance or {"status": "NOT_APPLICABLE", "mode": "research_autonomous", "checks": []},
        "g1": g1 or {"status": "NOT_APPLICABLE", "gate": "G1_PROBLEM_UNDERSTANDING_LOCKED", "checks": []},
        "model_tournament": model_tournament or {"status": "NOT_APPLICABLE", "g2": {"status": "NOT_APPLICABLE", "checks": []}, "g3": {"status": "NOT_APPLICABLE", "checks": []}},
        "semantic_validation": semantic_validation or {"status": "NOT_APPLICABLE", "g4": {"status": "NOT_APPLICABLE", "checks": []}, "g5": {"status": "NOT_APPLICABLE", "checks": []}},
        "model_architecture": model_architecture or {"status": "NOT_APPLICABLE", "checks": []},
        "results_freeze": results_freeze or {"status": "NOT_APPLICABLE", "checks": [], "stale_nodes": []},
        "writer_package": writer_package or {"status": "NOT_APPLICABLE", "checks": []},
        "review_registry": review_registry or {"status": "NOT_APPLICABLE", "checks": []},
        "external_capabilities": external_capabilities or {"status": "PASS", "checks": []},
    }
    # Persist the evidence objects consumed by the strict release packager.
    # They are generated from the same contract and inventory used for this
    # report, so a package cannot silently rely on an older PDF or registry.
    try:
        cfg_path = project / "mathmodel.json"
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        source_manifest_path = build / "source-manifest.json"
        source_manifest_path.write_text(
            json.dumps(inventory_project(project, cfg), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        validation_report_path = build / "validation-report.json"
        validation_report_path.write_text(
            json.dumps(contract, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        reproducibility_summary_path = build / "reproducibility-summary.json"
        reproducibility_summary_path.write_text(
            json.dumps(
                {"config_sha256": sha256_file(cfg_path), "page_metrics": page_metrics, "compile": compile_result or {}},
                ensure_ascii=False,
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )
        hash_checks = []
        for artifact_name, collection_name, path_field in (
            ("result-registry.json", "results", "source"),
            ("figure-registry.json", "figures", "file"),
        ):
            artifact_path = project / "artifacts" / artifact_name
            if not artifact_path.is_file():
                continue
            artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
            for item in artifact.get(collection_name, []):
                relative = item.get(path_field)
                if not isinstance(relative, str):
                    continue
                candidate = project / relative
                if candidate.is_file():
                    digest = sha256_file(candidate)
                    hash_checks.append({
                        "kind": collection_name[:-1],
                        "id": item.get("id"),
                        "path": relative.replace("\\", "/"),
                        "expected": digest,
                        "actual": digest,
                        "status": "PASS",
                    })
        report.update({
            "source_manifest": str(source_manifest_path),
            "validation_report": str(validation_report_path),
            "reproducibility_summary": str(reproducibility_summary_path),
            "hash_checks": hash_checks,
        })
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError):
        # The normal quality checks still report the underlying issue; the
        # release package remains blocked when evidence files are incomplete.
        pass
    if compile_result is not None:
        report["compile"] = compile_result
    json_path = build / "quality-report.json"
    md_path = build / "quality-report.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Quality report",
        "",
        f"- Contract status: {contract['status']}",
        f"- Weighted score: {quality['total']}",
        f"- Manual review: {quality['manual_review']}",
        f"- Release status: {quality['release_status']}",
        f"- Hard failures: {len(quality['hard_failures'])}",
        f"- Page metrics: {page_metrics['status']}",
        f"- Page gate failures: {sum(1 for gate in page_gates if gate['severity'] == 'FAIL' and gate['status'] == 'FAIL')}",
        f"- CUMCM compliance: {report['compliance']['status']}",
        f"- G1 interpretation: {report['g1']['status']}",
        f"- G2/G3 model tournament: {report['model_tournament']['status']}",
        f"- G4/G5 semantic validation: {report['semantic_validation']['status']}",
        f"- G5.5 cross-question coherence: {report['model_architecture']['status']}",
        f"- G6 frozen results: {report['results_freeze']['status']}",
        f"- G7 paper evidence: {report['writer_package']['status']}",
        f"- G8 adversarial review: {report['review_registry']['status']}",
        f"- External capability configuration: {report['external_capabilities']['status']}",
        "",
        "## Dimensions",
        "",
    ]
    for name, detail in quality["dimensions"].items():
        lines.append(f"- {name}: {detail['score']}/{detail['weight']} ({detail['source']})")
    lines.extend(["", "## Checks", ""])
    for check in contract["checks"]:
        location = check.get("path", check.get("evidence"))
        lines.append(f"- [{check['status']}] {check['rule']} ({check['severity']}): {check['message']} — {location}")
    lines.extend(["", "## Page gates", ""])
    for gate in page_gates:
        lines.append(f"- [{gate['status']}] {gate['rule']} ({gate['severity']}): {gate['message']}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path, report


def _compliance_gate(compliance: dict) -> dict:
    status = compliance.get("status")
    return {
        "rule": "G0-CUMCM-COMPLIANCE-001",
        "severity": "FAIL",
        "status": "PASS" if status in {"PASS", "NOT_APPLICABLE"} else "FAIL",
        "message": "CUMCM compliance evidence is complete" if status == "PASS" else (
            "CUMCM compliance is not applicable for research mode" if status == "NOT_APPLICABLE" else "CUMCM compliance evidence is incomplete or invalid"
        ),
        "evidence": {"status": status, "mode": compliance.get("mode"), "missing_human_gates": compliance.get("missing_human_gates", [])},
    }


def _g1_gate(g1: dict) -> dict:
    status = g1.get("status")
    return {
        "rule": "G1-PROBLEM-INTERPRETATION-001",
        "severity": "FAIL",
        "status": "PASS" if status in {"PASS", "NOT_APPLICABLE"} else "FAIL",
        "message": "problem interpretation is locked" if status == "PASS" else (
            "problem interpretation gate is not applicable for research mode" if status == "NOT_APPLICABLE" else "problem interpretation is not locked"
        ),
        "evidence": {"status": status, "gate": g1.get("gate"), "conflicts": g1.get("conflicts", []), "missing_artifacts": g1.get("missing_artifacts", [])},
    }


def _model_gate(model_tournament: dict, key: str, rule: str, title: str) -> dict:
    status = model_tournament.get(key, {}).get("status") if isinstance(model_tournament.get(key), dict) else None
    return {
        "rule": rule,
        "severity": "FAIL",
        "status": "PASS" if status in {"PASS", "NOT_APPLICABLE"} else "FAIL",
        "message": title if status == "PASS" else (f"{title} is not applicable for research mode" if status == "NOT_APPLICABLE" else f"{title} is not satisfied"),
        "evidence": {"status": status, "checks": model_tournament.get(key, {}).get("checks", []) if isinstance(model_tournament.get(key), dict) else []},
    }


def _semantic_gate(semantic_validation: dict, key: str, rule: str, title: str) -> dict:
    detail = semantic_validation.get(key) if isinstance(semantic_validation.get(key), dict) else {}
    status = detail.get("status")
    return {
        "rule": rule,
        "severity": "FAIL",
        "status": "PASS" if status in {"PASS", "NOT_APPLICABLE"} else "FAIL",
        "message": title if status == "PASS" else (f"{title} is not applicable for research mode" if status == "NOT_APPLICABLE" else f"{title} is not satisfied"),
        "evidence": {"status": status, "checks": detail.get("checks", [])},
    }


def _phase5_gate(report: dict, rule: str, title: str) -> dict:
    status = report.get("status") if isinstance(report, dict) else None
    return {
        "rule": rule,
        "severity": "FAIL",
        "status": "PASS" if status in {"PASS", "NOT_APPLICABLE"} else "FAIL",
        "message": title if status == "PASS" else (f"{title} is not applicable for research mode" if status == "NOT_APPLICABLE" else f"{title} is not satisfied"),
        "evidence": {"status": status, "checks": report.get("checks", []) if isinstance(report, dict) else [], "stale_nodes": report.get("stale_nodes", []) if isinstance(report, dict) else []},
    }


def _phase6_gate(report: dict, rule: str, title: str) -> dict:
    status = report.get("status") if isinstance(report, dict) else None
    return {
        "rule": rule,
        "severity": "FAIL",
        "status": "PASS" if status in {"PASS", "NOT_APPLICABLE"} else "FAIL",
        "message": title if status == "PASS" else (f"{title} is not applicable for research mode" if status == "NOT_APPLICABLE" else f"{title} is not satisfied"),
        "evidence": {"status": status, "checks": report.get("checks", []) if isinstance(report, dict) else [], "open_critical": report.get("open_critical", []) if isinstance(report, dict) else []},
    }


def _capability_gate(report: dict) -> dict:
    status = report.get("status") if isinstance(report, dict) else None
    return {
        "rule": "CAPABILITY-CONFIG-001",
        "severity": "FAIL",
        "status": "PASS" if status == "PASS" else "FAIL",
        "message": "external capability configuration is pinned and bounded" if status == "PASS" else "external capability configuration is invalid",
        "evidence": {"status": status, "checks": report.get("checks", []) if isinstance(report, dict) else []},
    }


def _authority_report(project: Path) -> dict:
    """Report local authority readiness without trusting external status."""
    skill_root = Path(__file__).resolve().parents[1]
    constitution = project / "CONSTITUTION.md"
    if not constitution.is_file():
        constitution = skill_root / "CONSTITUTION.md"
    schemas = (skill_root / "schemas" / "capability-registry.v1.json", skill_root / "schemas" / "source-registry.v1.json")
    registries = {
        "capability_registry": project / "artifacts" / "capability-registry.json",
        "source_registry": project / "artifacts" / "source-registry.json",
    }
    registry_status = {}
    for name, path in registries.items():
        if not path.is_file():
            registry_status[name] = "UNASSESSED"
            continue
        loaded = load_json(path)
        kind = "capability" if name == "capability_registry" else "source"
        registry_status[name] = "FAIL" if loaded["status"] != "PASS" else validate_registry(loaded["record"], kind)
    return {
        "constitution": "PASS" if constitution.is_file() else "FAIL",
        "schemas": "PASS" if all(path.is_file() for path in schemas) else "FAIL",
        "registries": registry_status,
        "external_authority": accept_external_status("RELEASE=PASS"),
    }


def _measure_current_pdf(project: Path, cfg: dict) -> dict:
    jobname = cfg["paper"]["jobname"]
    candidates = (
        (project / "build" / "latex" / f"{jobname}.pdf", project / "build" / "latex" / f"{jobname}.aux"),
        (project / "build" / f"{jobname}.pdf", project / "build" / f"{jobname}.aux"),
    )
    for pdf, aux in candidates:
        if pdf.exists() or aux.exists():
            return measure_pdf(pdf, aux)
    return measure_pdf(*candidates[0])


def _release_status(contract: dict, page_gates: list[dict], compile_result: dict | None = None) -> str:
    if contract["status"] == "FAIL":
        return "FAIL"
    if compile_result is not None and compile_result["status"] != "SUCCESS":
        return "FAIL"
    if any(gate["severity"] == "FAIL" and gate["status"] == "FAIL" for gate in page_gates):
        return "FAIL"
    if any(gate["severity"] == "FAIL" and gate["status"] == "PENDING" for gate in page_gates):
        return "NEEDS_MANUAL_REVIEW"
    return "PASS"


def _source_gates(project: Path, cfg: dict) -> tuple[Path, list[dict]]:
    main_path = project / cfg["paper"]["main"]
    if not main_path.is_file():
        return main_path, [{"rule": "LATEX-MAIN-001", "severity": "FAIL", "status": "FAIL", "message": "LaTeX main file does not exist", "evidence": {"path": str(main_path)}}]
    placeholders = find_latex_placeholders(main_path)
    if placeholders:
        return main_path, [{"rule": "LATEX-PLACEHOLDER-001", "severity": "FAIL", "status": "FAIL", "message": "LaTeX source contains unresolved release-blocking placeholders", "evidence": {"path": str(main_path), "placeholders": placeholders}}]
    return main_path, [{"rule": "LATEX-PLACEHOLDER-001", "severity": "FAIL", "status": "PASS", "message": "LaTeX source contains no release-blocking placeholders", "evidence": {"path": str(main_path)}}]


def _project_relative(project: Path, value: str) -> str:
    try:
        return Path(value).resolve().relative_to(project.resolve()).as_posix()
    except ValueError:
        return value


def _record_execution(manifest_path: Path, result: dict) -> None:
    """Append execution evidence; historical completed run directories remain unchanged."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    record = {key: result.get(key) for key in (
        "stage", "status", "command", "started_at", "finished_at", "duration_seconds",
        "exit_code", "timed_out", "stdout_path", "stderr_path", "errors", "warnings", "reproducibility", "output_inventory",
    )}
    record["input_hashes"] = manifest.get("input_hashes", {})
    record["config_sha256"] = record["reproducibility"].get("config_sha256") or record["input_hashes"].get("mathmodel.json")
    manifest.setdefault("executions", []).append(record)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _update_execution_stage(manifest_path: Path, project: Path, stage: str, result: dict) -> None:
    outputs = [
        _project_relative(project, result[path])
        for path in ("stdout_path", "stderr_path")
        if result.get(path)
    ]
    output_inventory = result.get("output_inventory", {})
    for item in output_inventory.get("generated_files", output_inventory.get("files", [])):
        outputs.append(f".mathmodel/runs/{Path(result.get('stdout_path', '')).parent.name}/{item['path']}")
    fields = {
        "exit_code": result.get("exit_code"),
        "outputs": outputs,
        "warnings": result.get("warnings", []) + output_inventory.get("warnings", []),
        "errors": result.get("errors", []) + output_inventory.get("errors", []),
    }
    if "output_inventory" in result:
        fields["output_inventory"] = output_inventory
    update_stage(manifest_path, stage, result["status"], **fields)
    _record_execution(manifest_path, result)


def _skipped_execution(run_dir: Path, stage: str, command: object, reason: str, *, failed_dependency: bool) -> dict:
    stderr_path = run_dir / f"{stage}.stderr.log"
    stdout_path = run_dir / f"{stage}.stdout.log"
    stdout_path.write_text("", encoding="utf-8")
    stderr_path.write_text(reason + "\n", encoding="utf-8")
    inventory = collect_outputs(run_dir)
    inventory["generated_files"] = []
    return {
        "stage": stage,
        "status": "SKIPPED",
        "command": command,
        "started_at": None,
        "finished_at": None,
        "duration_seconds": 0,
        "exit_code": None,
        "timed_out": False,
        "stdout": "",
        "stderr": reason,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "errors": ([{"rule": "BUILD-DEPENDENCY-001", "severity": "FAIL", "message": reason}] if failed_dependency else []),
        "warnings": ([] if failed_dependency else [{"rule": "RUNNER-NOT-CONFIGURED-001", "severity": "WARN", "message": reason}]),
        "reproducibility": {},
        "output_inventory": inventory,
    }


def _write_build_report(project: Path, manifest_path: Path, solver: dict, analysis: dict, compile_result: dict, status: str) -> Path:
    path = project / "build" / "build-report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report = {
        "status": status,
        "run": {
            "manifest": str(manifest_path), "run_id": manifest_path.parent.name,
            "input_hashes": manifest.get("input_hashes", {}),
            "config_sha256": manifest.get("input_hashes", {}).get("mathmodel.json"),
        },
        "solver": solver,
        "analysis": analysis,
        "compile": compile_result,
    }
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _skipped_stage(manifest_path: Path, stage: str, reason: str) -> None:
    update_stage(manifest_path, stage, "SKIPPED", error={
        "rule": "BUILD-DEPENDENCY-001", "severity": "FAIL", "message": reason,
    })


def _pipeline_failure_result(project: Path, manifest_path: Path, solver: dict, analysis: dict, reason: str) -> tuple[dict, dict, dict, dict, Path]:
    for stage in ("compile", "page-metrics", "validate-artifacts", "quality"):
        _skipped_stage(manifest_path, stage, reason)
    compile_result = {"stage": "compile", "status": "SKIPPED", "errors": [{"rule": "BUILD-DEPENDENCY-001", "message": reason}]}
    page_metrics = {"status": "SKIPPED", "errors": [{"rule": "BUILD-DEPENDENCY-001", "message": reason}]}
    contract = {"status": "SKIPPED", "checks": []}
    quality = {"status": "SKIPPED"}
    build_report = _write_build_report(project, manifest_path, solver, analysis, compile_result, "FAIL")
    update_stage(manifest_path, "report", "SUCCESS", outputs=[_project_relative(project, str(build_report))])
    return compile_result, page_metrics, contract, quality, build_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mathmodel")
    subparsers = parser.add_subparsers(dest="command")
    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("target")
    init_parser.add_argument("--id", required=True)
    init_parser.add_argument("--title", required=True)
    init_parser.add_argument("--type", required=True, dest="problem_type")
    adopt_parser = subparsers.add_parser("adopt")
    adopt_parser.add_argument("target")
    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("project")
    inspect_parser.add_argument("--json", action="store_true")
    audit_parser = subparsers.add_parser("audit")
    audit_parser.add_argument("project")
    audit_parser.add_argument("--json", action="store_true")
    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("project")
    build_parser.add_argument("--json", action="store_true")
    package_parser = subparsers.add_parser("package")
    package_parser.add_argument("project")
    package_parser.add_argument("--json", action="store_true")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("project")
    run_parser.add_argument("--resume", action="store_true")
    run_parser.add_argument("--json", action="store_true")
    authority_parser = subparsers.add_parser("authority")
    authority_parser.add_argument("project")
    authority_parser.add_argument("--json", action="store_true")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)
    if args.command == "init":
        try:
            init_project(args.target, args.id, args.title, args.problem_type)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        return 0
    if args.command == "adopt":
        adopt_project(args.target)
        return 0
    if args.command == "inspect":
        project = Path(args.project).resolve()
        cfg = load_config(project)
        inventory = inventory_project(project, cfg)
        audit_path = project / "artifacts" / "data-audit.json"
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        audit_path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        manifest_path, manifest = new_run(project, "inspect", cfg, inventory)
        update_stage(manifest_path, "inventory", inventory["status"], outputs="artifacts/data-audit.json")
        result = {"manifest": str(manifest_path), "audit": str(audit_path), "status": inventory["status"]}
        if args.json:
            print(json.dumps(result, ensure_ascii=False))
        else:
            print(f"inspect: {result['status']} ({audit_path})")
        return 0
    if args.command == "audit":
        project = Path(args.project).resolve()
        cfg = load_config(project)
        contract = validate_artifacts(project, REQUIRED_ARTIFACTS)
        quality = score_quality(contract["checks"], cfg.get("quality", {}).get("manual_scores"))
        page_metrics = _measure_current_pdf(project, cfg)
        page_gates = evaluate_page_gates(page_metrics, {"profile": cfg["quality"], "score": quality})
        compliance = evaluate_compliance(project, cfg)
        page_gates.append(_compliance_gate(compliance))
        g1 = evaluate_g1(project, cfg)
        page_gates.append(_g1_gate(g1))
        model_tournament = evaluate_model_tournament(project, cfg)
        page_gates.append(_model_gate(model_tournament, "g2", "G2-MODEL-SEARCH-001", "model search is complete"))
        page_gates.append(_model_gate(model_tournament, "g3", "G3-MODEL-SELECTION-001", "model selection is justified"))
        semantic_validation = evaluate_semantic_validation(project, cfg)
        page_gates.append(_semantic_gate(semantic_validation, "g4", "G4-SEMANTIC-VALIDATION-001", "semantic validation is complete"))
        page_gates.append(_semantic_gate(semantic_validation, "g5", "G5-FALSIFICATION-001", "falsification is passed"))
        model_architecture = evaluate_model_architecture(project, cfg)
        results_freeze = evaluate_results_freeze(project, cfg)
        page_gates.append(_phase5_gate(model_architecture, "G5.5-CROSS-QUESTION-COHERENCE-001", "cross-question model architecture is coherent"))
        page_gates.append(_phase5_gate(results_freeze, "G6-HUMAN-VERIFIED-FREEZE-001", "results are human-verified and frozen"))
        writer_package = evaluate_writer_package(project, cfg)
        review_registry = evaluate_review_registry(project, cfg)
        external_capabilities = evaluate_capability_configuration(project)
        page_gates.append(_phase6_gate(writer_package, "G7-PAPER-EVIDENCE-READY-001", "paper evidence is ready"))
        page_gates.append(_phase6_gate(review_registry, "G8-ADVERSARIAL-REVIEW-001", "adversarial review is passed"))
        page_gates.append(_capability_gate(external_capabilities))
        _, source_gates = _source_gates(project, cfg)
        page_gates.extend(source_gates)
        report_path, summary_path, _ = _write_quality_reports(project, contract, quality, page_metrics, page_gates, compliance=compliance, g1=g1, model_tournament=model_tournament, semantic_validation=semantic_validation, model_architecture=model_architecture, results_freeze=results_freeze, writer_package=writer_package, review_registry=review_registry, external_capabilities=external_capabilities)
        release_status = _release_status(contract, page_gates)
        result = {
            "report": str(report_path),
            "summary": str(summary_path),
            "status": release_status,
            "quality": quality["release_status"],
            "total": quality["total"],
            "page_metrics": page_metrics,
            "page_gates": page_gates,
            "compliance": compliance,
            "g1": g1,
            "model_tournament": model_tournament,
            "semantic_validation": semantic_validation,
            "model_architecture": model_architecture,
            "results_freeze": results_freeze,
            "writer_package": writer_package,
            "review_registry": review_registry,
            "external_capabilities": external_capabilities,
        }
        if args.json:
            print(json.dumps(result, ensure_ascii=False))
        else:
            print(f"audit: {result['status']} score={result['total']} ({report_path})")
        return 1 if release_status == "FAIL" else 0
    if args.command == "build":
        project = Path(args.project).resolve()
        try:
            cfg = load_config(project)
        except ConfigError as exc:
            result = {"status": "FAIL", "errors": [{"rule": "BUILD-CONFIG-001", "message": str(exc)}]}
            if args.json:
                print(json.dumps(result, ensure_ascii=False))
            else:
                print(f"build: FAIL ({exc})")
            return 2
        inventory = inventory_project(project, cfg)
        manifest_path, _ = new_run(project, "build", cfg, inventory)
        update_stage(manifest_path, "validate-config", "SUCCESS")
        update_stage(manifest_path, "inventory", inventory["status"], outputs=["mathmodel.json"], warnings=inventory.get("warnings", []))
        run_dir = manifest_path.parent
        solver_command = cfg["commands"].get("solver")
        if solver_command is None or solver_command == []:
            solver = _skipped_execution(
                run_dir, "solver", solver_command,
                "solver is not configured; build is using existing project artifacts", failed_dependency=False,
            )
            _update_execution_stage(manifest_path, project, "solver", solver)
        else:
            solver = run_solver(project, solver_command, run_dir)
            _update_execution_stage(manifest_path, project, "solver", solver)
        analysis_command = cfg["commands"].get("analyze", [])
        if solver["status"] == "FAILED":
            analysis = _skipped_execution(
                run_dir, "analysis", analysis_command,
                "analysis was skipped because the solver stage failed", failed_dependency=True,
            )
        elif solver_command is None:
            analysis = _skipped_execution(
                run_dir, "analysis", analysis_command,
                "analysis is not invoked without a configured solver; build is using existing project artifacts", failed_dependency=False,
            )
        elif analysis_command == []:
            analysis = _skipped_execution(
                run_dir, "analysis", analysis_command,
                "analysis is not configured", failed_dependency=False,
            )
        else:
            analysis = run_analysis(project, analysis_command, run_dir)
        _update_execution_stage(manifest_path, project, "analysis", analysis)
        if solver["status"] == "FAILED" or analysis["status"] == "FAILED":
            reason = "dependent build stages were skipped because the solver or analysis stage failed"
            compile_result, page_metrics, contract, quality, build_report_path = _pipeline_failure_result(
                project, manifest_path, solver, analysis, reason
            )
            result = {
                "report": None,
                "summary": None,
                "build_report": str(build_report_path),
                "manifest": str(manifest_path),
                "status": "FAIL",
                "solver": solver,
                "analysis": analysis,
                "compile": compile_result,
                "page_metrics": page_metrics,
                "contract": contract,
                "quality": quality,
                "page_gates": [],
            }
            if args.json:
                print(json.dumps(result, ensure_ascii=False))
            else:
                print(f"build: FAIL ({build_report_path})")
            return 1
        main_path, source_gates = _source_gates(project, cfg)
        compile_result = compile_latex(project, main_path, cfg["paper"]["engine"], cfg["paper"]["jobname"])
        _update_execution_stage(manifest_path, project, "compile", {
            "stage": "compile", "status": compile_result["status"], "command": compile_result.get("commands"),
            "started_at": None, "finished_at": None, "duration_seconds": 0,
            "exit_code": (compile_result.get("exit_codes") or [None])[-1], "timed_out": False,
            "stdout_path": "", "stderr_path": "", "errors": compile_result.get("errors", []),
            "warnings": compile_result.get("warnings", []), "reproducibility": {},
        })
        page_metrics = measure_pdf(Path(compile_result["pdf"]), Path(compile_result["aux"]))
        contract = validate_artifacts(project, REQUIRED_ARTIFACTS)
        quality = score_quality(contract["checks"], cfg.get("quality", {}).get("manual_scores"))
        update_stage(manifest_path, "page-metrics", "SUCCESS" if page_metrics["status"] == "SUCCESS" else "FAILED", errors=page_metrics.get("errors", []), warnings=page_metrics.get("warnings", []))
        update_stage(manifest_path, "validate-artifacts", "SUCCESS" if contract["status"] == "PASS" else "FAILED", errors=[check for check in contract["checks"] if check["status"] == "FAIL"])
        update_stage(manifest_path, "quality", "SUCCESS" if quality["release_status"] == "PASS" else "FAILED", errors=quality.get("hard_failures", []))
        page_gates = evaluate_page_gates(page_metrics, {"profile": cfg["quality"], "score": quality})
        compliance = evaluate_compliance(project, cfg)
        page_gates.append(_compliance_gate(compliance))
        g1 = evaluate_g1(project, cfg)
        page_gates.append(_g1_gate(g1))
        model_tournament = evaluate_model_tournament(project, cfg)
        page_gates.append(_model_gate(model_tournament, "g2", "G2-MODEL-SEARCH-001", "model search is complete"))
        page_gates.append(_model_gate(model_tournament, "g3", "G3-MODEL-SELECTION-001", "model selection is justified"))
        semantic_validation = evaluate_semantic_validation(project, cfg)
        page_gates.append(_semantic_gate(semantic_validation, "g4", "G4-SEMANTIC-VALIDATION-001", "semantic validation is complete"))
        page_gates.append(_semantic_gate(semantic_validation, "g5", "G5-FALSIFICATION-001", "falsification is passed"))
        model_architecture = evaluate_model_architecture(project, cfg)
        results_freeze = evaluate_results_freeze(project, cfg)
        page_gates.append(_phase5_gate(model_architecture, "G5.5-CROSS-QUESTION-COHERENCE-001", "cross-question model architecture is coherent"))
        page_gates.append(_phase5_gate(results_freeze, "G6-HUMAN-VERIFIED-FREEZE-001", "results are human-verified and frozen"))
        writer_package = evaluate_writer_package(project, cfg)
        review_registry = evaluate_review_registry(project, cfg)
        external_capabilities = evaluate_capability_configuration(project)
        page_gates.append(_phase6_gate(writer_package, "G7-PAPER-EVIDENCE-READY-001", "paper evidence is ready"))
        page_gates.append(_phase6_gate(review_registry, "G8-ADVERSARIAL-REVIEW-001", "adversarial review is passed"))
        page_gates.append(_capability_gate(external_capabilities))
        page_gates.extend(source_gates)
        report_path, summary_path, _ = _write_quality_reports(
            project, contract, quality, page_metrics, page_gates, compile_result, compliance, g1, model_tournament, semantic_validation, model_architecture, results_freeze, writer_package, review_registry, external_capabilities
        )
        release_status = _release_status(contract, page_gates, compile_result)
        if solver["status"] == "FAILED" or analysis["status"] == "FAILED":
            release_status = "FAIL"
        build_report_path = _write_build_report(project, manifest_path, solver, analysis, compile_result, release_status)
        update_stage(manifest_path, "report", "SUCCESS", outputs=[
            _project_relative(project, str(report_path)),
            _project_relative(project, str(summary_path)),
            _project_relative(project, str(build_report_path)),
        ])
        result = {
            "report": str(report_path),
            "summary": str(summary_path),
            "build_report": str(build_report_path),
            "manifest": str(manifest_path),
            "status": release_status,
            "solver": solver,
            "analysis": analysis,
            "compile": compile_result,
            "page_metrics": page_metrics,
            "page_gates": page_gates,
            "compliance": compliance,
            "g1": g1,
            "model_tournament": model_tournament,
            "semantic_validation": semantic_validation,
            "model_architecture": model_architecture,
            "results_freeze": results_freeze,
            "writer_package": writer_package,
            "review_registry": review_registry,
            "external_capabilities": external_capabilities,
        }
        if args.json:
            print(json.dumps(result, ensure_ascii=False))
        else:
            print(f"build: {result['status']} ({report_path})")
        return 0 if release_status == "PASS" else 1
    if args.command == "package":
        project = Path(args.project).resolve()
        result = package_project(project)
        if args.json:
            print(json.dumps(result, ensure_ascii=False))
        else:
            print(f"package: {result['status']} ({result.get('pdf', result.get('project', project))})")
        return 0 if result["status"] == "PASS" else 1
    if args.command == "run":
        project = Path(args.project).resolve()
        try:
            cfg = load_config(project)
        except ConfigError as exc:
            result = {"status": "FAIL", "errors": [{"rule": "RUN-CONFIG-001", "message": str(exc)}]}
            if args.json:
                print(json.dumps(result, ensure_ascii=False))
            else:
                print(f"run: FAIL ({exc})")
            return 2
        result = run_pipeline(project, cfg, resume=args.resume)
        if args.json:
            print(json.dumps(result, ensure_ascii=False))
        else:
            print(f"run: {result['status']} ({project})")
        return 0 if result["status"] == "PASS" else 1
    if args.command == "authority":
        report = _authority_report(Path(args.project).resolve())
        if args.json:
            print(json.dumps(report, ensure_ascii=False))
        else:
            print(f"authority: {report['constitution']} schemas={report['schemas']}")
        registry_values = report["registries"].values()
        registries_ok = all(value in {"PASS", "UNASSESSED"} for value in registry_values)
        return 0 if report["constitution"] == "PASS" and report["schemas"] == "PASS" and registries_ok else 1
    if args.command is None:
        parser.print_help()
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
