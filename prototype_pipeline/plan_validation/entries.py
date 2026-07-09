from __future__ import annotations

from pathlib import Path
from typing import Any

from prototype_pipeline.plan_validation.contract import (
    artifact_matches_path,
    contract_artifact_types,
    infer_artifact_type,
)
from prototype_pipeline.plan_validation.policies import (
    READ_ONLY_POLICIES,
    WRITE_POLICIES,
    normalize_policy,
    operation_for,
)
from prototype_pipeline.plan_validation.utils import as_list


def validate_and_normalize_entries(
    run: Path,
    entries: list[dict[str, Any]],
    *,
    roots: tuple[str, ...],
    forbidden_prefixes: tuple[str, ...],
    forbidden_exact: set[str],
    contract: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    workspace = run / "workspace"
    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    normalized: list[dict[str, Any]] = []
    seen_paths: dict[str, dict[str, Any]] = {}
    artifact_types = contract_artifact_types(contract)

    for entry in entries:
        path = entry.get("path")
        policy = normalize_policy(entry.get("policy") or entry.get("change_policy") or "may_modify")
        operation = operation_for(policy, entry)
        if not isinstance(path, str) or not path.strip():
            blockers.append({"code": "missing_path", "entry": entry})
            continue
        path = path.replace("\\", "/")
        path_blocker = _path_blocker(path, roots, forbidden_prefixes, forbidden_exact)
        if path_blocker:
            blockers.append(path_blocker)
            continue

        artifact_type = _resolve_artifact_type(entry, path, contract, warnings)
        _validate_artifact_type(path, artifact_type, artifact_types, contract, operation, blockers, warnings)
        _validate_path_state(workspace, path, policy, blockers, warnings)
        _validate_metadata(entry, path, warnings)

        item = _normalized_item(entry, path, policy, operation, artifact_type)
        _merge_or_append(normalized, seen_paths, item)
    return normalized, blockers, warnings


def _path_blocker(path: str, roots: tuple[str, ...], forbidden_prefixes: tuple[str, ...], forbidden_exact: set[str]) -> dict[str, Any] | None:
    if not _is_relative_safe(path):
        return {"code": "unsafe_path", "path": path}
    reason = _is_forbidden(path, forbidden_prefixes, forbidden_exact)
    if reason:
        return {"code": "forbidden_path", "path": path, "reason": reason}
    if not _allowed_root(path, roots):
        return {"code": "outside_allowed_roots", "path": path, "allowed_roots": list(roots)}
    return None


def _resolve_artifact_type(entry: dict[str, Any], path: str, contract: dict[str, Any], warnings: list[dict[str, Any]]) -> str | None:
    artifact_type = entry.get("artifact_type") or entry.get("kind_type")
    if artifact_type:
        return str(artifact_type)
    inferred, candidates = infer_artifact_type(path, contract)
    if inferred:
        warnings.append({"code": "inferred_artifact_type", "path": path, "artifact_type": inferred})
    elif candidates:
        warnings.append({"code": "ambiguous_artifact_type", "path": path, "candidates": candidates})
    return inferred



def _validate_artifact_type(
    path: str,
    artifact_type: str | None,
    artifact_types: dict[str, dict[str, Any]],
    contract: dict[str, Any],
    operation: str,
    blockers: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> None:
    if not artifact_type:
        warnings.append({"code": "missing_artifact_type", "path": path})
        return
    if artifact_type not in artifact_types:
        blockers.append({"code": "unknown_artifact_type", "path": path, "artifact_type": artifact_type})
        return
    if not artifact_matches_path(path, artifact_type, contract):
        blockers.append({
            "code": "path_does_not_match_artifact_type",
            "path": path,
            "artifact_type": artifact_type,
            "path_templates": artifact_types[artifact_type].get("path_templates") or [],
            "allowed_roots": artifact_types[artifact_type].get("allowed_roots") or [],
        })
        return
    allowed_operations = artifact_types[artifact_type].get("allowed_operations") or []
    if allowed_operations and operation not in allowed_operations:
        blockers.append({
            "code": "operation_not_allowed_for_artifact_type",
            "path": path,
            "artifact_type": artifact_type,
            "operation": operation,
            "allowed_operations": allowed_operations,
        })


def _validate_path_state(workspace: Path, path: str, policy: str, blockers: list[dict[str, Any]], warnings: list[dict[str, Any]]) -> None:
    if policy in {"must_create"} and (workspace / path).exists():
        blockers.append({"code": "create_path_already_exists", "path": path})
    if policy in {"may_modify", "must_modify", "modify_allowed", "allowed_change", "may_read", "no_change", "read_only"} and not (workspace / path).exists():
        item = {"code": "target_file_missing", "path": path, "policy": policy}
        if policy == "must_modify":
            blockers.append(item)
        else:
            warnings.append(item)


def _validate_metadata(entry: dict[str, Any], path: str, warnings: list[dict[str, Any]]) -> None:
    if not entry.get("scheme_element_id") and not entry.get("scheme_element_ids") and not entry.get("scheme_elements"):
        warnings.append({"code": "missing_scheme_element_id", "path": path})
    if not entry.get("requirement_id") and not entry.get("requirement_ids") and not entry.get("requirements"):
        warnings.append({"code": "missing_requirement_reference", "path": path})


def _normalized_item(entry: dict[str, Any], path: str, policy: str, operation: str, artifact_type: str | None) -> dict[str, Any]:
    requirements = entry.get("requirements") or as_list(entry.get("requirement_id")) or as_list(entry.get("requirement_ids"))
    scheme_elements = entry.get("scheme_elements") or as_list(entry.get("scheme_element_id")) or as_list(entry.get("scheme_element_ids"))
    return {
        "path": path,
        "policy": policy,
        "operation": operation,
        "kind": entry.get("kind") or "implementation",
        "artifact_type": artifact_type,
        "scheme_element_id": scheme_elements[0] if scheme_elements else None,
        "scheme_elements": scheme_elements,
        "scheme_element_type": entry.get("scheme_element_type"),
        "requirements": requirements,
        "reason": entry.get("reason") or entry.get("description"),
        "validation_check_id": entry.get("validation_check_id"),
        "validation_check_type": entry.get("validation_check_type"),
        "validation_intent": entry.get("validation_intent"),
        "executable_validation": bool(entry.get("executable_validation")),
        "source": entry.get("source") or "planner_proposal",
    }


def _merge_or_append(normalized: list[dict[str, Any]], seen_paths: dict[str, dict[str, Any]], item: dict[str, Any]) -> None:
    path = str(item.get("path"))
    if path not in seen_paths:
        seen_paths[path] = item
        normalized.append(item)
        return
    existing = seen_paths[path]
    if existing.get("policy") in READ_ONLY_POLICIES and item.get("policy") in WRITE_POLICIES:
        existing["policy"] = item.get("policy")
        existing["operation"] = item.get("operation")
    for req in item.get("requirements") or []:
        if req and req not in existing.setdefault("requirements", []):
            existing["requirements"].append(req)
    for scheme in item.get("scheme_elements") or []:
        if scheme and scheme not in existing.setdefault("scheme_elements", []):
            existing["scheme_elements"].append(scheme)
    if item.get("validation_check_id"):
        existing.setdefault("validation_check_ids", []).append(item["validation_check_id"])
    if item.get("validation_intent"):
        existing.setdefault("validation_intents", [])
        if item["validation_intent"] not in existing["validation_intents"]:
            existing["validation_intents"].append(item["validation_intent"])


def _is_relative_safe(path: str) -> bool:
    p = Path(path)
    return not p.is_absolute() and ".." not in p.parts and path.strip() == path and bool(path.strip())


def _is_forbidden(path: str, forbidden_prefixes: tuple[str, ...], forbidden_exact: set[str]) -> str | None:
    normalized = path.replace("\\", "/")
    if normalized in forbidden_exact:
        return f"forbidden exact path: {normalized}"
    for prefix in forbidden_prefixes:
        if normalized == prefix.rstrip("/") or normalized.startswith(prefix):
            return f"forbidden path prefix: {prefix}"
    return None


def _allowed_root(path: str, roots: tuple[str, ...]) -> bool:
    normalized = path.replace("\\", "/")
    return any(normalized.startswith(root) for root in roots)
