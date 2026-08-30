"""PDF page-boundary measurements and release gates."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any


BOUNDARY_LABELS = (
    "mm:body-start",
    "mm:body-end",
    "mm:references-start",
    "mm:references-end",
    "mm:appendix-start",
    "mm:appendix-end",
)
_LABEL_RE = re.compile(r"\\newlabel\{(?P<label>[^}]+)\}\{\{[^}]*\}\{(?P<page>[^}]+)\}")
_PAGES_RE = re.compile(r"^Pages:\s*(?P<pages>\d+)\s*$", re.MULTILINE)
_PAGE_SIZE_RE = re.compile(r"^Page size:\s*(?P<size>.+)$", re.MULTILINE)


def _record(rule: str, message: str, *, path: Path | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "rule": rule,
        "message": message,
        "path": str(path) if path is not None else None,
        "evidence": {} if evidence is None else evidence,
    }


def _gate(rule: str, severity: str, status: str, message: str, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "rule": rule,
        "severity": severity,
        "status": status,
        "message": message,
        "evidence": {} if evidence is None else evidence,
    }


def _stream_text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value if isinstance(value, str) else ""


def parse_aux_pages(aux: Path, labels: tuple[str, ...]) -> dict[str, int]:
    """Read numeric page numbers for requested ``\\newlabel`` records without raising."""
    requested = set(labels)
    try:
        text = Path(aux).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    pages: dict[str, int] = {}
    for match in _LABEL_RE.finditer(text):
        label = match.group("label")
        if label not in requested:
            continue
        try:
            page = int(match.group("page"))
        except ValueError:
            continue
        if page > 0:
            pages[label] = page
    return pages


def _base_metrics(pdf: Path, aux: Path) -> dict[str, Any]:
    return {
        "status": "PENDING",
        "pdf": str(pdf),
        "aux": str(aux),
        "total_pages": None,
        "body_pages": None,
        "reference_pages": None,
        "appendix_pages": None,
        "appendix_body_ratio": None,
        "labels": {},
        "page_size": None,
        "a4_status": "PENDING",
        "warnings": [],
        "errors": [],
    }


def _valid_boundaries(labels: dict[str, int], total_pages: int) -> bool:
    pages = [labels[label] for label in BOUNDARY_LABELS]
    return pages[0] <= pages[1] < pages[2] <= pages[3] < pages[4] <= pages[5] <= total_pages


def measure_pdf(pdf: Path, aux: Path) -> dict[str, Any]:
    """Measure a PDF using ``pdfinfo`` and the template's AUX boundary labels."""
    pdf_path = Path(pdf)
    aux_path = Path(aux)
    metrics = _base_metrics(pdf_path, aux_path)
    if not pdf_path.is_file():
        metrics["warnings"].append(_record("PDF-FILE-001", "PDF is unavailable for page measurement", path=pdf_path))
        return metrics
    try:
        completed = subprocess.run(
            ["pdfinfo", str(pdf_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            shell=False,
        )
    except FileNotFoundError:
        metrics["warnings"].append(_record("PDFINFO-001", "pdfinfo is unavailable; page metrics require manual retry"))
    except UnicodeDecodeError as exc:
        metrics["warnings"].append(_record("PDFINFO-001", "pdfinfo output could not be decoded; page metrics require manual retry", evidence={"error": str(exc)}))
    except OSError as exc:
        metrics["warnings"].append(_record("PDFINFO-001", "pdfinfo could not be started", evidence={"error": str(exc)}))
    else:
        stdout = _stream_text(completed.stdout)
        stderr = _stream_text(completed.stderr)
        if completed.returncode != 0:
            metrics["errors"].append(_record("PDFINFO-002", "pdfinfo could not inspect the selected PDF", path=pdf_path, evidence={"stderr": stderr, "exit_code": completed.returncode}))
        else:
            page_match = _PAGES_RE.search(stdout)
            if page_match is None:
                metrics["errors"].append(_record("PDFINFO-003", "pdfinfo did not report a total page count", path=pdf_path))
            else:
                metrics["total_pages"] = int(page_match.group("pages"))
            size_match = _PAGE_SIZE_RE.search(stdout)
            if size_match is None:
                metrics["warnings"].append(_record("PDF-A4-001", "pdfinfo did not report page size", path=pdf_path))
            else:
                page_size = size_match.group("size").strip()
                metrics["page_size"] = page_size
                if "a4" in page_size.lower():
                    metrics["a4_status"] = "PASS"
                else:
                    metrics["a4_status"] = "FAIL"
                    metrics["errors"].append(_record("PDF-A4-001", "PDF page size is not A4", path=pdf_path, evidence={"page_size": page_size}))
    if not aux_path.is_file():
        metrics["warnings"].append(_record("PDF-AUX-001", "AUX file is unavailable for page measurement", path=aux_path))
    else:
        labels = parse_aux_pages(aux_path, BOUNDARY_LABELS)
        metrics["labels"] = labels
        missing = [label for label in BOUNDARY_LABELS if label not in labels]
        if missing:
            metrics["errors"].append(_record("PDF-LABEL-001", "PDF boundary labels are missing or malformed", path=aux_path, evidence={"missing": missing}))
        elif metrics["total_pages"] is not None:
            total_pages = metrics["total_pages"]
            if not _valid_boundaries(labels, total_pages):
                metrics["errors"].append(_record("PDF-BOUNDARY-001", "PDF boundary labels are not in a valid page order", path=aux_path, evidence={"labels": labels, "total_pages": total_pages}))
            else:
                metrics["body_pages"] = labels["mm:body-end"] - labels["mm:body-start"] + 1
                metrics["reference_pages"] = labels["mm:references-end"] - labels["mm:references-start"] + 1
                metrics["appendix_pages"] = labels["mm:appendix-end"] - labels["mm:appendix-start"] + 1
                metrics["appendix_body_ratio"] = metrics["appendix_pages"] / metrics["body_pages"]
    if metrics["errors"]:
        metrics["status"] = "FAILED"
    elif metrics["total_pages"] is not None and metrics["a4_status"] == "PASS" and metrics["body_pages"] is not None:
        metrics["status"] = "SUCCESS"
    return metrics


def _profile_and_score(quality: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if isinstance(quality.get("profile"), dict):
        profile = quality["profile"]
        score = quality.get("score") if isinstance(quality.get("score"), dict) else {}
        return profile, score
    return quality, quality


def evaluate_page_gates(metrics: dict, quality: dict) -> list[dict]:
    """Return hard page gates, soft range warnings, and quality-release blockers."""
    profile, score = _profile_and_score(quality)
    gates: list[dict[str, Any]] = []
    metric_status = metrics.get("status", "PENDING")
    if metric_status != "SUCCESS":
        gates.append(
            _gate(
                "PAGE-METRICS-001",
                "FAIL",
                "FAIL" if metric_status == "FAILED" else "PENDING",
                "page metrics are invalid" if metric_status == "FAILED" else "page metrics await required local artifacts or tools",
                {"metrics_status": metric_status},
            )
        )
    else:
        body_pages = metrics.get("body_pages")
        body_range = profile.get("target_body_pages")
        if not isinstance(body_pages, int) or not isinstance(body_range, list) or len(body_range) != 2:
            gates.append(_gate("PAGE-BODY-001", "FAIL", "PENDING", "body-page profile or measurement is unavailable"))
        else:
            minimum, maximum = body_range
            gates.append(
                _gate(
                    "PAGE-BODY-001",
                    "FAIL",
                    "FAIL" if body_pages < minimum else "PASS",
                    "body page count is below the configured minimum" if body_pages < minimum else "body page count meets the configured minimum",
                    {"actual": body_pages, "minimum": minimum},
                )
            )
            if body_pages > maximum:
                gates.append(_gate("PAGE-BODY-002", "WARN", "WARN", "body page count exceeds the configured target", {"actual": body_pages, "maximum": maximum}))
        appendix_pages = metrics.get("appendix_pages")
        ratio = metrics.get("appendix_body_ratio")
        maximum_ratio = profile.get("max_appendix_body_ratio")
        if not isinstance(ratio, (int, float)) or not isinstance(maximum_ratio, (int, float)):
            gates.append(_gate("PAGE-APPENDIX-001", "FAIL", "PENDING", "appendix/body ratio or profile is unavailable"))
        else:
            gates.append(
                _gate(
                    "PAGE-APPENDIX-001",
                    "FAIL",
                    "FAIL" if ratio > maximum_ratio else "PASS",
                    "appendix/body ratio exceeds the configured maximum" if ratio > maximum_ratio else "appendix/body ratio meets the configured maximum",
                    {"appendix_pages": appendix_pages, "ratio": ratio, "maximum": maximum_ratio},
                )
            )
        total_pages = metrics.get("total_pages")
        total_range = profile.get("target_total_pages")
        if not isinstance(total_pages, int) or not isinstance(total_range, list) or len(total_range) != 2:
            gates.append(_gate("PAGE-TOTAL-001", "WARN", "PENDING", "total-page profile or measurement is unavailable"))
        elif not total_range[0] <= total_pages <= total_range[1]:
            gates.append(_gate("PAGE-TOTAL-001", "WARN", "WARN", "total page count is outside the configured target", {"actual": total_pages, "target": total_range}))
        else:
            gates.append(_gate("PAGE-TOTAL-001", "WARN", "PASS", "total page count is within the configured target", {"actual": total_pages, "target": total_range}))
    if metrics.get("a4_status") == "FAIL":
        gates.append(_gate("PAGE-A4-001", "FAIL", "FAIL", "selected PDF is not A4"))
    elif metrics.get("a4_status") == "PENDING" and metric_status == "SUCCESS":
        gates.append(_gate("PAGE-A4-001", "WARN", "PENDING", "A4 verification is unavailable"))

    minimum_score = profile.get("minimum_score")
    observed_score = score.get("total")
    if not isinstance(minimum_score, int) or not isinstance(observed_score, (int, float)):
        gates.append(_gate("QUALITY-SCORE-001", "FAIL", "PENDING", "quality score or configured minimum is unavailable"))
    else:
        gates.append(
            _gate(
                "QUALITY-SCORE-001",
                "FAIL",
                "FAIL" if observed_score < minimum_score else "PASS",
                "quality score is below the configured minimum" if observed_score < minimum_score else "quality score meets the configured minimum",
                {"actual": observed_score, "minimum": minimum_score},
            )
        )
    release_status = score.get("release_status")
    if release_status == "FAIL":
        gates.append(_gate("QUALITY-RELEASE-001", "FAIL", "FAIL", "quality contract blocks release", {"release_status": release_status}))
    elif release_status == "PASS":
        gates.append(_gate("QUALITY-RELEASE-001", "FAIL", "PASS", "quality contract permits release", {"release_status": release_status}))
    else:
        gates.append(_gate("QUALITY-RELEASE-001", "FAIL", "PENDING", "quality release decision is pending", {"release_status": release_status}))
    return gates
