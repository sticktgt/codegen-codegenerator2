from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.common import read_json

from prototype_pipeline.plan_validation.contract import planner_output_contract
from prototype_pipeline.plan_validation.utils import as_list


def load_scheme_model(workspace: Path) -> dict[str, Any]:
    path = workspace / "prototype" / "input" / "scheme_model.json"
    if not path.exists():
        return {}
    data = read_json(path)
    return data if isinstance(data, dict) else {}


def validate_design_delta(
    proposal: dict[str, Any],
    implementation_slice: dict[str, Any],
    scheme_model: dict[str, Any],
    normalized_entries: list[dict[str, Any]],
    workspace: Path,
    contract: dict[str, Any],
    validation_scheme_ids: set[str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Validate planner-owned design_delta as a formal plan contract.

    This deliberately avoids static code semantics. Architecture decisions belong
    in prompts/kit instructions; this function only checks that the model wrote
    the canonical design planning fields needed for review and traceability.
    """
    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    design = proposal.get("design_delta")
    output_contract = planner_output_contract(contract)

    if not isinstance(design, dict) or not design:
        blockers.append({
            "code": "design_delta_missing",
            "message": "plan_proposal.json must include canonical design_delta. Do not use scheme_delta as a substitute.",
        })
        return blockers, warnings

    existing_ids = _scheme_element_ids(scheme_model)
    selected_existing = {str(item) for item in as_list(implementation_slice.get("selected_existing_elements")) if item}
    slice_change_type = str(implementation_slice.get("change_type") or design.get("change_type") or "")
    preserve_default = bool(implementation_slice.get("preserve_existing_behavior_by_default"))

    resolved_existing = _design_delta_ids(design.get("resolved_existing_elements"))
    proposed_new = _design_delta_ids(design.get("proposed_new_elements"))
    decisions = _preservation_decisions(design)

    _validate_change_type(slice_change_type, design, warnings)
    _validate_selected_existing(selected_existing, resolved_existing, warnings)
    _validate_existing_new_classification(
        design,
        existing_ids,
        selected_existing,
        resolved_existing,
        proposed_new,
        warnings,
    )
    _validate_proposed_new_shape(design, output_contract, blockers, warnings)
    _validate_referenced_scheme_elements(
        existing_ids,
        resolved_existing,
        proposed_new,
        normalized_entries,
        validation_scheme_ids or set(),
        blockers,
        warnings,
    )
    _validate_preservation_decisions(
        preserve_default,
        slice_change_type,
        normalized_entries,
        workspace,
        decisions,
        blockers,
        warnings,
    )
    return blockers, warnings


def _validate_change_type(slice_change_type: str, design: dict[str, Any], warnings: list[dict[str, Any]]) -> None:
    if slice_change_type and slice_change_type != str(design.get("change_type") or slice_change_type):
        warnings.append({
            "code": "design_delta_change_type_mismatch",
            "slice_change_type": slice_change_type,
            "design_delta_change_type": design.get("change_type"),
            "message": "Planner design_delta change_type does not match implementation_slice change_type.",
        })


def _validate_selected_existing(selected_existing: set[str], resolved_existing: set[str], warnings: list[dict[str, Any]]) -> None:
    if selected_existing and not selected_existing.issubset(resolved_existing):
        warnings.append({
            "code": "selected_existing_elements_not_resolved",
            "selected_existing_elements": sorted(selected_existing),
            "resolved_existing_elements": sorted(resolved_existing),
            "message": "The plan should resolve user-selected existing elements or explain why they are not affected.",
        })


def _validate_existing_new_classification(
    design: dict[str, Any],
    existing_ids: set[str],
    selected_existing: set[str],
    resolved_existing: set[str],
    proposed_new: set[str],
    warnings: list[dict[str, Any]],
) -> None:
    """Warn about design_delta classification drift without blocking safe plans.

    This is planner-output hygiene, not code semantics. The reviewer may use
    these warnings, but implementation can still proceed when the file plan is
    safe and formal boundaries passed.
    """
    duplicated = sorted(resolved_existing & proposed_new)
    if duplicated:
        warnings.append({
            "code": "design_delta_existing_new_overlap",
            "scheme_element_ids": duplicated,
            "message": "Element ids should not appear in both resolved_existing_elements and proposed_new_elements.",
        })

    proposed_already_existing = sorted(proposed_new & existing_ids)
    if proposed_already_existing:
        warnings.append({
            "code": "design_delta_proposed_new_already_exists",
            "scheme_element_ids": proposed_already_existing,
            "message": "proposed_new_elements should contain only ids not present in scheme_model.json.",
        })

    for item in as_list(design.get("resolved_existing_elements")):
        if not isinstance(item, dict) or not item.get("id"):
            continue
        element_id = str(item["id"])
        if element_id not in existing_ids and element_id not in selected_existing:
            warnings.append({
                "code": "design_delta_resolved_existing_not_in_current_scheme",
                "scheme_element_id": element_id,
                "source": item.get("source"),
                "message": (
                    "resolved_existing_elements references an id absent from the current scheme_model.json "
                    "and implementation_slice.selected_existing_elements. This is allowed for workspace/baseline "
                    "discovered elements, but should be treated as a schema gap/update candidate."
                ),
            })
        if item.get("source") == "selected_by_user" and element_id not in selected_existing:
            warnings.append({
                "code": "design_delta_invalid_selected_by_user_source",
                "scheme_element_id": element_id,
                "message": "source=selected_by_user is valid only for ids explicitly listed in implementation_slice.selected_existing_elements.",
            })


def _validate_proposed_new_shape(
    design: dict[str, Any],
    output_contract: dict[str, Any],
    blockers: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> None:
    modes = set(output_contract.get("new_element_implementation_modes") or [])
    for item in as_list(design.get("proposed_new_elements")):
        if not isinstance(item, dict):
            blockers.append({"code": "invalid_proposed_new_element", "item": item})
            continue
        if not item.get("id") or not item.get("type") or not item.get("reason"):
            blockers.append({"code": "incomplete_proposed_new_element", "item": item})
        mode = item.get("implementation_mode")
        if not mode:
            blockers.append({
                "code": "missing_new_element_implementation_mode",
                "id": item.get("id"),
                "message": "Each proposed_new_element must declare implementation_mode from the kit planner_output contract.",
            })
        elif modes and str(mode) not in modes:
            blockers.append({
                "code": "unknown_new_element_implementation_mode",
                "id": item.get("id"),
                "implementation_mode": mode,
                "allowed_modes": sorted(modes),
            })
        if mode == "screen_internal" and not item.get("owning_artifact"):
            blockers.append({
                "code": "screen_internal_element_missing_owner",
                "id": item.get("id"),
                "message": "screen_internal proposed elements must name owning_artifact.",
            })
        if mode == "separate_artifact" and not (item.get("artifact") or item.get("planned_artifact")):
            warnings.append({
                "code": "separate_artifact_without_named_artifact",
                "id": item.get("id"),
                "message": "Separate-artifact elements should name the planned artifact path when known.",
            })


def _validate_referenced_scheme_elements(
    existing_ids: set[str],
    resolved_existing: set[str],
    proposed_new: set[str],
    normalized_entries: list[dict[str, Any]],
    validation_scheme_ids: set[str],
    blockers: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> None:
    """Validate scheme element references without treating scheme_model as complete.

    ``scheme_model.json`` is analyst/design context and may be partial in
    incremental runs. A plan may legitimately reference an existing element that
    the planner discovered from the current workspace or previous baseline
    context and classified in ``design_delta.resolved_existing_elements``. Such
    references are schema gaps, not blockers. A blocker is reserved for an
    element that is referenced by file/validation plans but is neither known in
    the current scheme, nor resolved as existing, nor proposed as new.
    """
    referenced: set[str] = set(validation_scheme_ids)
    for entry in normalized_entries:
        referenced.update(_entry_scheme_ids(entry))

    known = existing_ids | resolved_existing | proposed_new
    missing = sorted(s for s in referenced if s not in known)
    if missing:
        blockers.append({
            "code": "new_scheme_elements_not_in_design_delta",
            "scheme_element_ids": missing,
            "message": (
                "Scheme elements referenced by file_plan or validation_plan must be "
                "present in scheme_model.json, resolved in design_delta.resolved_existing_elements, "
                "or introduced in design_delta.proposed_new_elements."
            ),
        })

    schema_gaps = sorted(s for s in referenced if s in resolved_existing and s not in existing_ids)
    if schema_gaps:
        warnings.append({
            "code": "referenced_existing_elements_missing_from_current_scheme",
            "scheme_element_ids": schema_gaps,
            "message": (
                "Referenced elements were resolved as existing by the planner but are absent from "
                "the current scheme_model.json. Treat this as a schema gap/update candidate, not "
                "as a new implementation element."
            ),
        })


def _validate_preservation_decisions(
    preserve_default: bool,
    slice_change_type: str,
    normalized_entries: list[dict[str, Any]],
    workspace: Path,
    decisions: list[dict[str, Any]],
    blockers: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> None:
    if slice_change_type == "create_new":
        return
    if not (preserve_default or slice_change_type == "extend_existing_behavior"):
        return
    decision_elements = {str(item.get("existing_element_id")) for item in decisions if item.get("existing_element_id")}
    decision_artifacts = {str(item.get("artifact")) for item in decisions if item.get("artifact")}
    for entry in _modified_existing_entries(normalized_entries, workspace):
        path = str(entry.get("path"))
        schemes = _entry_scheme_ids(entry)
        if not ((schemes & decision_elements) or path in decision_artifacts):
            warnings.append({
                "code": "modified_existing_artifact_without_preservation_decision",
                "path": path,
                "scheme_elements": sorted(schemes),
                "message": "For extend_existing_behavior, modifications to existing artifacts should be justified in design_delta.preservation_decisions.",
            })
    for item in decisions:
        if str(item.get("decision") or "") == "replace":
            blockers.append({
                "code": "replace_decision_requires_explicit_requirement",
                "existing_element_id": item.get("existing_element_id"),
                "artifact": item.get("artifact"),
                "message": "The slice preserves existing behavior by default. A replace decision needs an explicit requirement-level reason.",
            })


def _scheme_element_ids(scheme_model: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    for item in scheme_model.get("elements") or []:
        if isinstance(item, dict) and item.get("id"):
            result.add(str(item["id"]))
    return result


def _design_delta_ids(items: Any) -> set[str]:
    result: set[str] = set()
    for item in as_list(items):
        if isinstance(item, dict) and item.get("id"):
            result.add(str(item["id"]))
        elif isinstance(item, str):
            result.add(item)
    return result


def _preservation_decisions(design_delta: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in as_list(design_delta.get("preservation_decisions")) if isinstance(item, dict)]


def _entry_scheme_ids(entry: dict[str, Any]) -> set[str]:
    schemes = {str(item) for item in entry.get("scheme_elements") or [] if item}
    if entry.get("scheme_element_id"):
        schemes.add(str(entry["scheme_element_id"]))
    return schemes


def _modified_existing_entries(normalized_entries: list[dict[str, Any]], workspace: Path) -> list[dict[str, Any]]:
    return [
        entry for entry in normalized_entries
        if entry.get("operation") == "modify" and (workspace / str(entry.get("path"))).exists()
    ]
