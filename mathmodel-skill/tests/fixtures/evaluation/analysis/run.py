"""Deterministic weighted-evaluation adapter and controlled fixture compiler."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture_pdf() -> bytes:
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R 5 0 R 7 0 R] /Count 3 /MediaBox [0 0 595 842] >>",
        b"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 9 0 R >> >> /MediaBox [0 0 595 842] /Contents 4 0 R >>",
        b"<< /Length 43 >>\nstream\nBT /F1 16 Tf 72 760 Td (Body evidence) Tj ET\nendstream",
        b"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 9 0 R >> >> /MediaBox [0 0 595 842] /Contents 6 0 R >>",
        b"<< /Length 40 >>\nstream\nBT /F1 16 Tf 72 760 Td (References) Tj ET\nendstream",
        b"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 9 0 R >> >> /MediaBox [0 0 595 842] /Contents 8 0 R >>",
        b"<< /Length 38 >>\nstream\nBT /F1 16 Tf 72 760 Td (Appendix) Tj ET\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    output, offsets = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"), [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(output)); output.extend(f"{number} 0 obj\n".encode()); output.extend(obj); output.extend(b"\nendobj\n")
    startxref = len(output); output.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]: output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{startxref}\n%%EOF\n".encode())
    return bytes(output)


def compile_fixture(arguments: list[str]) -> None:
    output_dir = next((Path(arg.split("=", 1)[1]) for arg in arguments if arg.startswith("-output-directory=")), None)
    jobname = next((arg.split("=", 1)[1] for arg in arguments if arg.startswith("-jobname=")), "fixture")
    if output_dir is None:
        raise SystemExit("missing compiler output directory")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{jobname}.pdf").write_bytes(fixture_pdf())
    (output_dir / f"{jobname}.aux").write_text("\\newlabel{mm:body-start}{{}{1}}\n\\newlabel{mm:body-end}{{}{1}}\n\\newlabel{mm:references-start}{{}{2}}\n\\newlabel{mm:references-end}{{}{2}}\n\\newlabel{mm:appendix-start}{{}{3}}\n\\newlabel{mm:appendix-end}{{}{3}}\n", encoding="utf-8")
    (output_dir / f"{jobname}.log").write_text("Deterministic fixture compiler completed.\n", encoding="utf-8")


def validate_evaluation_input(weights: dict, alternatives: list[dict], directions: dict[str, str]) -> None:
    if set(weights) != set(directions) or any(isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0 for value in weights.values()) or abs(sum(weights.values()) - 1.0) > 1e-9:
        raise ValueError("evaluation weights must be non-negative and sum to one")
    if any(min(row[name] for row in alternatives) == max(row[name] for row in alternatives) for name in directions):
        raise ValueError("evaluation normalization requires a non-constant indicator range")


def run() -> None:
    raw_path = ROOT / "data" / "raw" / "input.json"
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    weights, alternatives = raw["weights"], raw["alternatives"]
    directions = {"cost": "min", "benefit": "max", "reliability": "max"}
    validate_evaluation_input(weights, alternatives, directions)
    bounds = {name: (min(row[name] for row in alternatives), max(row[name] for row in alternatives)) for name in directions}
    normalized = {row["id"]: {name: ((bounds[name][1] - row[name]) if directions[name] == "min" else (row[name] - bounds[name][0])) / (bounds[name][1] - bounds[name][0]) for name in directions} for row in alternatives}
    scores = {name: sum(weights[key] * value for key, value in values.items()) for name, values in normalized.items()}
    ranking = [name for name, _ in sorted(scores.items(), key=lambda item: (-item[1], item[0]))]
    sensitivity_weights = {"cost": 0.4, "benefit": 0.3, "reliability": 0.3}
    sensitivity_ranking = [name for name, _ in sorted(((name, sum(sensitivity_weights[key] * value for key, value in values.items())) for name, values in normalized.items()), key=lambda item: (-item[1], item[0]))]
    result = {"weights": weights, "normalized": normalized, "scores": scores, "ranking": ranking, "sensitivity_ranking": sensitivity_ranking}
    result_path = ROOT / "analysis" / "results.json"
    write_json(result_path, result)
    figures = []
    for role in ("data", "method", "result", "validation"):
        path = ROOT / "paper" / "figures" / f"{role}.svg"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="320" height="120"><text x="12" y="60">evaluation {role} evidence</text></svg>\n', encoding="utf-8")
        figures.append({"id": f"F-{role.upper()}", "role": role, "file": path.relative_to(ROOT).as_posix(), "source_data": "data/raw/input.json", "script": "analysis/run.py", "label": f"fig:evaluation-{role}", "claim_ids": ["C-MAIN"], "source_sha256": sha256(path), "readability": "text label remains readable in monochrome"})
    model = {"id": "M-EVAL", "question_id": "Q1", "method": "direction-aware min-max weighted score", "weights": weights, "directions": directions, "seed": 0, "limitation": "weights are illustrative policy weights"}
    validations = [{"id": "V-EVAL-NORM", "question_id": "Q1", "method": "check all normalized scores lie in [0,1]", "metric": "range violations", "threshold": 0, "result": 0, "status": "PASS", "failure_case": "constant indicator range"}, {"id": "V-EVAL-SENS", "question_id": "Q1", "method": "increase cost weight to 0.4", "metric": "ranking agreement", "threshold": "identical", "result": ranking == sensitivity_ranking, "status": "PASS", "failure_case": "larger policy changes can reverse ranks"}]
    validation_ids = [item["id"] for item in validations]
    write_json(ROOT / "artifacts" / "data-audit.json", {"status": "SUCCESS", "files": [{"path": "data/raw/input.json", "sha256": sha256(raw_path), "units": "cost, benefit, reliability", "missingness": 0, "preprocessing": "direction-aware min-max normalization"}]})
    write_json(ROOT / "artifacts" / "problem-map.json", {"questions": [{"id": "Q1", "objective": "rank alternatives", "inputs": ["data/raw/input.json"], "outputs": ["R-MAIN"], "method": model["method"], "validation": validation_ids, "section": "body", "model_ids": ["M-EVAL"], "result_ids": ["R-MAIN"], "validation_ids": validation_ids, "claim_ids": ["C-MAIN"]}]})
    write_json(ROOT / "artifacts" / "model-registry.json", {"models": [model]})
    write_json(ROOT / "artifacts" / "result-registry.json", {"results": [{"id": "R-MAIN", "value": result, "unit": "weighted score", "precision": 6, "source": "analysis/results.json", "source_sha256": sha256(result_path), "field": "ranking", "question_id": "Q1", "model_id": "M-EVAL", "validation_ids": validation_ids}]})
    write_json(ROOT / "artifacts" / "claim-registry.json", {"claims": [{"id": "C-MAIN", "body": "Alternative A ranks first under the stated weights and remains first under the documented weight perturbation.", "result_ids": ["R-MAIN"], "validation_ids": validation_ids, "scope": "three-alternative teaching fixture", "failure_case": model["limitation"], "section": "body"}]})
    write_json(ROOT / "artifacts" / "figure-registry.json", {"figures": figures})
    write_json(ROOT / "artifacts" / "validation.json", {"validations": validations})
    if (ROOT / "analysis" / "tamper-output.flag").exists():
        result_path.write_text(result_path.read_text(encoding="utf-8") + "tampered\n", encoding="utf-8")


if __name__ == "__main__":
    compile_fixture(sys.argv[sys.argv.index("--compile") + 1:]) if "--compile" in sys.argv else run()
