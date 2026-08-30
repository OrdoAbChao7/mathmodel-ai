"""Deterministic adapter shared by the Task 8 fixture shapes."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_pdf() -> bytes:
    texts = (b"Body evidence", b"References", b"Appendix")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R 5 0 R 7 0 R] /Count 3 /MediaBox [0 0 595 842] >>",
        b"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 9 0 R >> >> /MediaBox [0 0 595 842] /Contents 4 0 R >>",
        b"stream\nBT /F1 16 Tf 72 760 Td (Body evidence) Tj ET\nendstream",
        b"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 9 0 R >> >> /MediaBox [0 0 595 842] /Contents 6 0 R >>",
        b"stream\nBT /F1 16 Tf 72 760 Td (References) Tj ET\nendstream",
        b"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 9 0 R >> >> /MediaBox [0 0 595 842] /Contents 8 0 R >>",
        b"stream\nBT /F1 16 Tf 72 760 Td (Appendix) Tj ET\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    for index in (3, 5, 7):
        stream = objects[index]
        body = stream[len(b"stream\n"):-len(b"\nendstream")]
        objects[index] = b"<< /Length " + str(len(body)).encode() + b" >>\n" + stream
    content = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, value in enumerate(objects, 1):
        offsets.append(len(content)); content.extend(f"{number} 0 obj\n".encode()); content.extend(value); content.extend(b"\nendobj\n")
    xref = len(content); content.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]: content.extend(f"{offset:010d} 00000 n \n".encode())
    content.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(content)


def compile_fixture(arguments: list[str]) -> None:
    output = next((Path(arg.split("=", 1)[1]) for arg in arguments if arg.startswith("-output-directory=")), None); jobname = next((arg.split("=", 1)[1] for arg in arguments if arg.startswith("-jobname=")), "fixture")
    if output is None: raise SystemExit("missing compiler output directory")
    output.mkdir(parents=True, exist_ok=True); (output / f"{jobname}.pdf").write_bytes(make_pdf())
    (output / f"{jobname}.aux").write_text("\\newlabel{mm:body-start}{{}{1}}\n\\newlabel{mm:body-end}{{}{1}}\n\\newlabel{mm:references-start}{{}{2}}\n\\newlabel{mm:references-end}{{}{2}}\n\\newlabel{mm:appendix-start}{{}{3}}\n\\newlabel{mm:appendix-end}{{}{3}}\n", encoding="utf-8")
    (output / f"{jobname}.log").write_text("Deterministic fixture compiler completed.\n", encoding="utf-8")


def validate_forecast_input(observations: list[dict], holdout: int) -> None:
    if not isinstance(holdout, int) or isinstance(holdout, bool) or not 0 < holdout < len(observations):
        raise ValueError("holdout must split the fixture observations")
    times = [item["time"] for item in observations]
    if times != sorted(times) or len(set(times)) != len(times):
        raise ValueError("forecast observations must be strictly chronological")
    train, test = observations[:-holdout], observations[-holdout:]
    if max(item["time"] for item in train) >= min(item["time"] for item in test):
        raise ValueError("forecast training data must precede the holdout")


def validate_evaluation_input(weights: dict, alternatives: list[dict], directions: dict[str, str]) -> None:
    if set(weights) != set(directions) or any(isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0 for value in weights.values()) or abs(sum(weights.values()) - 1.0) > 1e-9:
        raise ValueError("evaluation weights must be non-negative and sum to one")
    if any(min(row[name] for row in alternatives) == max(row[name] for row in alternatives) for name in directions):
        raise ValueError("evaluation normalization requires a non-constant indicator range")


def solve(kind: str, raw: dict) -> tuple[dict, dict, list[dict], str]:
    if kind == "optimization":
        profit, constraints = raw["profit"], raw["constraints"]; feasible = [(x, y) for x in range(5) for y in range(5) if all(row["x"] * x + row["y"] * y <= row["limit"] for row in constraints)]; x, y = max(feasible, key=lambda pair: profit["x"] * pair[0] + profit["y"] * pair[1]); objective = profit["x"] * x + profit["y"] * y
        return ({"objective_value": objective, "allocation": {"x": x, "y": y}, "feasible_points": len(feasible)}, {"id": "M-OPT", "method": "exhaustive integer enumeration", "objective": "max 5x+4y", "constraints": constraints, "seed": 0, "limitation": "two-variable teaching instance"}, [{"id": "V-OPT-HAND", "method": "enumerate all nonnegative integer candidates", "metric": "maximum constraint violation", "threshold": 0, "result": 0, "status": "PASS"}, {"id": "V-OPT-SCENARIO", "method": "reduce first capacity from 4 to 3", "metric": "feasibility", "threshold": "feasible", "result": "feasible", "status": "PASS"}], "The exhaustive search identifies x=2 and y=2 with objective 18 for the stated constraints.")
    if kind == "forecasting":
        observations, holdout = raw["observations"], raw["holdout"]; validate_forecast_input(observations, holdout); train, test = observations[:-holdout], observations[-holdout:]; slope = (train[-1]["value"] - train[0]["value"]) / (train[-1]["time"] - train[0]["time"]); intercept = train[0]["value"] - slope * train[0]["time"]; predictions = [slope * item["time"] + intercept for item in test]; mae = sum(abs(prediction - item["value"]) for prediction, item in zip(predictions, test)) / len(test); baseline_mae = sum(abs(train[-1]["value"] - item["value"]) for item in test) / len(test)
        return ({"slope": slope, "intercept": intercept, "holdout_predictions": predictions, "holdout_actual": [item["value"] for item in test], "holdout_mae": mae, "persistence_baseline_mae": baseline_mae}, {"id": "M-FOR", "method": "ordinary least-squares linear trend", "train_end_time": train[-1]["time"], "holdout": holdout, "seed": 0, "limitation": "linear trend only"}, [{"id": "V-FOR-HOLDOUT", "method": "chronological final holdout", "metric": "MAE", "threshold": 0.01, "result": mae, "status": "PASS"}, {"id": "V-FOR-BASELINE", "method": "persistence baseline on same holdout", "metric": "MAE improvement", "threshold": "> 0", "result": baseline_mae - mae, "status": "PASS"}], "The time-ordered linear forecast has holdout MAE 0.0 and improves on persistence by 3.0 units.")
    weights, alternatives = raw["weights"], raw["alternatives"]; directions = {"cost": "min", "benefit": "max", "reliability": "max"}; validate_evaluation_input(weights, alternatives, directions); ranges = {name: (min(row[name] for row in alternatives), max(row[name] for row in alternatives)) for name in directions}; normalized = {row["id"]: {name: ((ranges[name][1] - row[name]) if directions[name] == "min" else (row[name] - ranges[name][0])) / (ranges[name][1] - ranges[name][0]) for name in directions} for row in alternatives}; scores = {key: sum(weights[name] * value for name, value in values.items()) for key, values in normalized.items()}; ranking = [key for key, _ in sorted(scores.items(), key=lambda item: (-item[1], item[0]))]; sensitivity_weights = {"cost": 0.4, "benefit": 0.3, "reliability": 0.3}; sensitivity = [key for key, _ in sorted(((key, sum(sensitivity_weights[name] * value for name, value in values.items())) for key, values in normalized.items()), key=lambda item: (-item[1], item[0]))]
    return ({"weights": weights, "normalized": normalized, "scores": scores, "ranking": ranking, "sensitivity_ranking": sensitivity}, {"id": "M-EVAL", "method": "direction-aware min-max weighted score", "weights": weights, "directions": directions, "seed": 0, "limitation": "weights are illustrative policy weights"}, [{"id": "V-EVAL-NORM", "method": "check all normalized scores lie in [0,1]", "metric": "range violations", "threshold": 0, "result": 0, "status": "PASS"}, {"id": "V-EVAL-SENS", "method": "increase cost weight to 0.4", "metric": "ranking agreement", "threshold": "identical", "result": ranking == sensitivity, "status": "PASS"}], "Alternative A ranks first under the stated weights and remains first under the documented weight perturbation.")


def run() -> None:
    config = json.loads((ROOT / "mathmodel.json").read_text(encoding="utf-8")); kind = config["problem_type"]; raw_path = ROOT / "data" / "raw" / "input.json"; raw = json.loads(raw_path.read_text(encoding="utf-8")); result, model, validations, claim = solve(kind, raw); result_path = ROOT / "analysis" / "results.json"; write_json(result_path, result)
    figures = []
    for role in ("data", "method", "result", "validation"):
        path = ROOT / "paper" / "figures" / f"{role}.svg"; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="320" height="120"><text x="12" y="60">{kind} {role} evidence</text></svg>\n', encoding="utf-8"); figures.append({"id": f"F-{role.upper()}", "role": role, "file": path.relative_to(ROOT).as_posix(), "source_data": "data/raw/input.json", "script": "analysis/run.py", "label": f"fig:{kind}-{role}", "claim_ids": ["C-MAIN"], "source_sha256": digest(path), "readability": "text label remains readable in monochrome"})
    validation_ids = [item["id"] for item in validations]
    for item in validations: item["question_id"] = "Q1"; item["failure_case"] = "outside the small fixture domain"
    write_json(ROOT / "artifacts" / "data-audit.json", {"status": "SUCCESS", "files": [{"path": "data/raw/input.json", "sha256": digest(raw_path), "units": "fixture units", "missingness": 0, "preprocessing": "none"}]}); write_json(ROOT / "artifacts" / "problem-map.json", {"questions": [{"id": "Q1", "objective": config["title"], "inputs": ["data/raw/input.json"], "outputs": ["R-MAIN"], "method": model["method"], "validation": validation_ids, "section": "body", "model_ids": [model["id"]], "result_ids": ["R-MAIN"], "validation_ids": validation_ids, "claim_ids": ["C-MAIN"]}]}); model["question_id"] = "Q1"; write_json(ROOT / "artifacts" / "model-registry.json", {"models": [model]}); write_json(ROOT / "artifacts" / "result-registry.json", {"results": [{"id": "R-MAIN", "value": result, "unit": "fixture units", "precision": 6, "source": "analysis/results.json", "source_sha256": digest(result_path), "field": "all", "question_id": "Q1", "model_id": model["id"], "validation_ids": validation_ids}]}); write_json(ROOT / "artifacts" / "claim-registry.json", {"claims": [{"id": "C-MAIN", "body": claim, "result_ids": ["R-MAIN"], "validation_ids": validation_ids, "scope": "small deterministic fixture", "failure_case": model["limitation"], "section": "body"}]}); write_json(ROOT / "artifacts" / "figure-registry.json", {"figures": figures}); write_json(ROOT / "artifacts" / "validation.json", {"validations": validations})
    if (ROOT / "analysis" / "tamper-output.flag").exists(): result_path.write_text(result_path.read_text(encoding="utf-8") + "tampered\n", encoding="utf-8")


if __name__ == "__main__":
    compile_fixture(sys.argv[sys.argv.index("--compile") + 1:]) if "--compile" in sys.argv else run()
