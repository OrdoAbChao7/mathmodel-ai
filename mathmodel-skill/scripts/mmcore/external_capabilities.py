"""Pinned, least-authority external capability adapters for MathModel-AI."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml


_PIN = re.compile(r"^[0-9a-f]{40}$")
_REPOSITORY = re.compile(r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/?$")
_MODES = {"ABSTRACT_INSPIRED", "EXTERNAL_ADAPTER", "REIMPLEMENTED"}
_ADAPTER_AUTHORITY = {"xiaoma": "lazy_load", "ars": "findings_only", "automcm": "abstract_inspired", "zhnnky": "abstract_inspired"}
_LOCAL_PROVIDERS = {"local", "local_review_system", "local_method_judge", "local_validation_engine", "local_g9"}


def _read_yaml(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        return None, str(exc)
    return (value, None) if isinstance(value, dict) else (None, "registry root must be an object")


def _load(project: Path, name: str) -> tuple[dict[str, Any] | None, str | None]:
    project_path = Path(project).resolve() / "config" / name
    if project_path.is_file():
        return _read_yaml(project_path)
    bundled = Path(__file__).resolve().parents[2] / "config" / name
    return _read_yaml(bundled)


def _check(rule: str, status: str, message: str, **evidence: Any) -> dict[str, Any]:
    return {"rule": rule, "status": status, "message": message, "evidence": evidence}


def _valid_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def evaluate_capability_configuration(project: Path) -> dict[str, Any]:
    """Validate pinned sources, provider links, and local decision authority."""
    root = Path(project).resolve()
    capabilities, cap_error = _load(root, "capability-registry.yaml")
    sources, source_error = _load(root, "external-sources.yaml")
    checks: list[dict[str, Any]] = []
    if cap_error or source_error:
        return {"status": "FAIL", "checks": [_check("CAPABILITY-EVIDENCE-001", "FAIL", "capability and source registries are required", capability_error=cap_error, source_error=source_error)]}
    if capabilities.get("schema_version") != 1 or sources.get("schema_version") != 1:
        checks.append(_check("CAPABILITY-SCHEMA-001", "FAIL", "capability and source registries must use schema_version 1"))
    raw_capabilities = capabilities.get("capabilities")
    raw_sources = sources.get("sources")
    if not isinstance(raw_capabilities, list) or not raw_capabilities or any(not isinstance(item, dict) for item in raw_capabilities):
        checks.append(_check("CAPABILITY-SHAPE-001", "FAIL", "capabilities must be a non-empty array of objects"))
        raw_capabilities = []
    if not isinstance(raw_sources, list) or not raw_sources or any(not isinstance(item, dict) for item in raw_sources):
        checks.append(_check("SOURCE-SHAPE-001", "FAIL", "sources must be a non-empty array of objects"))
        raw_sources = []
    source_ids = [item.get("id") for item in raw_sources]
    source_map = {item.get("id"): item for item in raw_sources if _valid_text(item.get("id"))}
    if len(source_ids) != len(source_map) or any(not _valid_text(item.get("id")) for item in raw_sources):
        checks.append(_check("SOURCE-ID-001", "FAIL", "source IDs must be unique non-empty strings"))
    for source in raw_sources:
        valid = (_valid_text(source.get("id")) and isinstance(source.get("repository"), str) and _REPOSITORY.fullmatch(source.get("repository", "")) is not None and _valid_text(source.get("license"))
                 and isinstance(source.get("pinned_commit"), str) and _PIN.fullmatch(source.get("pinned_commit", "")) is not None and isinstance(source.get("integration_mode"), str) and source.get("integration_mode") in _MODES
                 and isinstance(source.get("capabilities"), list) and all(_valid_text(item) for item in source.get("capabilities"))
                 and _valid_text(source.get("authority")) and _valid_text(source.get("attribution")))
        checks.append(_check("SOURCE-CONTRACT-001", "PASS" if valid else "FAIL", "source is pinned and attributable" if valid else "source contract is incomplete or floating", source_id=source.get("id")))
    capability_ids = [item.get("id") for item in raw_capabilities]
    if len(capability_ids) != len({item for item in capability_ids if _valid_text(item)}) or any(not _valid_text(item.get("id")) for item in raw_capabilities):
        checks.append(_check("CAPABILITY-ID-001", "FAIL", "capability IDs must be unique non-empty strings"))
    for capability in raw_capabilities:
        providers = capability.get("providers")
        valid = (_valid_text(capability.get("id")) and isinstance(capability.get("owner"), str) and capability.get("owner") in _LOCAL_PROVIDERS and isinstance(providers, list) and bool(providers)
                 and all(_valid_text(item) for item in providers) and capability.get("external_decision_allowed") is False)
        provider_sources = [source_map.get(provider) for provider in providers if isinstance(providers, list)] if valid else []
        if valid and any(source is None and provider not in _LOCAL_PROVIDERS for provider, source in zip(providers, provider_sources)):
            valid = False
        if valid and any(source is not None and capability["id"] not in source.get("capabilities", []) for source in provider_sources):
            valid = False
        if valid and capability.get("owner") in providers and capability.get("owner") not in _LOCAL_PROVIDERS:
            valid = False
        checks.append(_check("CAPABILITY-AUTHORITY-001", "PASS" if valid else "FAIL", "capability has local owner and linked providers" if valid else "capability authority or provider link is unsafe", capability_id=capability.get("id")))
    status = "PASS" if checks and all(item["status"] == "PASS" for item in checks) else "FAIL"
    return {"status": status, "checks": checks, "capabilities": capability_ids, "sources": list(source_map)}


def resolve_adapter(project: Path, capability_id: str, provider_id: str) -> dict[str, Any]:
    """Resolve an adapter without executing external code or granting gate authority."""
    report = evaluate_capability_configuration(project)
    if report["status"] != "PASS":
        return {"status": "FAIL", "checks": report["checks"]}
    capabilities, _ = _load(Path(project), "capability-registry.yaml")
    sources, _ = _load(Path(project), "external-sources.yaml")
    capability = next((item for item in capabilities.get("capabilities", []) if item.get("id") == capability_id), None)
    source = next((item for item in sources.get("sources", []) if item.get("id") == provider_id), None)
    if not isinstance(capability, dict) or not isinstance(source, dict) or provider_id not in capability.get("providers", []):
        return {"status": "FAIL", "checks": [_check("ADAPTER-RESOLVE-001", "FAIL", "requested adapter is not registered")]}
    authority = _ADAPTER_AUTHORITY.get(provider_id, "read_only")
    return {
        "status": "PASS",
        "capability": capability_id,
        "provider": provider_id,
        "pinned_commit": source["pinned_commit"],
        "integration_mode": source["integration_mode"],
        "authority": authority,
        "external_decision_allowed": False,
        "input_contract": "local evidence context only",
        "output_contract": "advisory artifacts/findings; local gates decide PASS/FAIL",
        "gate_authority": [],
    }
