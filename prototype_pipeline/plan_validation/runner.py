from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.common import read_json

from prototype_pipeline.plan_validation.contract import load_contract, load_rules
from prototype_pipeline.plan_validation.design_delta import load_scheme_model, validate_design_delta
from prototype_pipeline.plan_validation.entries import validate_and_normalize_entries
from prototype_pipeline.plan_validation.policies import extract_plan_entries
from prototype_pipeline.plan_validation.validation_checks import (
    extract_validation_file_entries,
    validation_scheme_element_ids,
)
from prototype_pipeline.plan_validation.utils import as_list


def validate_proposal(run: Path, proposal: dict[str, Any], validation_plan: dict[str, Any] | None = None) -> dict[str, Any]:
    workspace = run / "workspace"
    implementation_slice = _load_implementation_slice(workspace)
    contract = load_contract(workspace)
    roots, forbidden_prefixes, forbidden_exact = load_rules(workspace, contract)
    entries = extract_plan_entries(proposal)
    validation_entries: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    if not contract:
        blockers.append({
            "code": "architecture_contract_missing",
            "message": "architecture-contract.yaml is required. Run tools/sync_run_inputs.py or recreate the run with prepare_incremental_run.py.",
        })

    dropped_validation_check_ids: set[str] = set()
    if validation_plan:
        validation_entries, validation_blockers, validation_warnings, dropped_validation_check_ids = extract_validation_file_entries(validation_plan, workspace, contract)
        blockers.extend(validation_blockers)
        warnings.extend(validation_warnings)

    if not entries and not validation_entries:
        blockers.append({
            "code": "no_file_entries",
            "message": "Plan proposal does not contain file entries. Expected file_plan_draft or allowed_files.",
        })

    normalized, entry_blockers, entry_warnings = validate_and_normalize_entries(
        run,
        entries + validation_entries,
        roots=roots,
        forbidden_prefixes=forbidden_prefixes,
        forbidden_exact=forbidden_exact,
        contract=contract,
    )
    blockers.extend(entry_blockers)
    warnings.extend(entry_warnings)

    scheme_model = load_scheme_model(workspace)
    _enrich_plan_requirement_links(
        normalized=normalized,
        proposal=proposal,
        scheme_model=scheme_model,
        warnings=warnings,
    )

    coverage_blockers, coverage_warnings = _validate_slice_requirement_coverage(
        implementation_slice=implementation_slice,
        normalized=normalized,
        validation_plan=validation_plan,
        dropped_validation_check_ids=dropped_validation_check_ids,
    )
    blockers.extend(coverage_blockers)
    warnings.extend(coverage_warnings)

    design_blockers, design_warnings = validate_design_delta(
        proposal,
        implementation_slice,
        scheme_model,
        normalized,
        workspace,
        contract,
        validation_scheme_element_ids(validation_plan),
    )
    blockers.extend(design_blockers)
    warnings.extend(design_warnings)

    return {
        "status": "passed" if not blockers else "failed",
        "slice_id": proposal.get("slice_id") or implementation_slice.get("slice_id"),
        "blockers": blockers,
        "warnings": warnings,
        "dropped_validation_check_ids": sorted(dropped_validation_check_ids),
        "contract_id": contract.get("id"),
        "normalized_file_plan": _normalized_file_plan(proposal, implementation_slice, contract, normalized),
    }


def find_default_proposal(run: Path) -> Path:
    candidates = [
        run / "workspace" / "prototype" / "output" / "plan_proposal.json",
        run / "output" / "plan_proposal.json",
        run / "agent_reports" / "plan_proposal.json",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def find_default_validation_plan(run: Path) -> Path | None:
    candidates = [
        run / "workspace" / "prototype" / "output" / "validation_plan_proposal.json",
        run / "agent_reports" / "validation_plan_proposal.json",
        run / "output" / "validation_plan_proposal.json",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None




def _scheme_requirements_by_id(scheme_model: dict[str, Any]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for element in scheme_model.get("elements") or []:
        if not isinstance(element, dict) or not element.get("id"):
            continue
        values = element.get("requirements") or element.get("requirement_ids") or as_list(element.get("requirement_id"))
        reqs: list[str] = []
        for value in values:
            req_id = str(value).strip()
            if req_id and req_id not in reqs:
                reqs.append(req_id)
        result[str(element["id"])] = reqs
    return result


def _append_unique(values: list[str], additions: list[str]) -> bool:
    changed = False
    for value in additions:
        if value and value not in values:
            values.append(value)
            changed = True
    return changed


def _design_elements(design: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for key in ("proposed_new_elements", "resolved_existing_elements"):
        for item in as_list(design.get(key)):
            if isinstance(item, dict):
                result.append(item)
    return result


def _entry_matches_owner(item: dict[str, Any], owner: str) -> bool:
    if not owner:
        return False
    owner = owner.replace("\\", "/")
    if str(item.get("path") or "") == owner:
        return True
    return owner in {str(value) for value in item.get("scheme_elements") or []}


def _enrich_plan_requirement_links(
    *,
    normalized: list[dict[str, Any]],
    proposal: dict[str, Any],
    scheme_model: dict[str, Any],
    warnings: list[dict[str, Any]],
) -> None:
    """Derive requirement links from scheme metadata and screen-internal ownership.

    The planner may correctly express a UI action as ``screen_internal``: there
    is no dedicated action file, and the owning screen file implements the
    action. Earlier coverage validation looked only at each file entry's direct
    ``requirements`` list, so such plans could fail even when ``design_delta``
    clearly named the screen as the action owner.

    This enrichment keeps the boundary strict about paths while avoiding false
    coverage blockers: requirement ids may be derived from referenced scheme
    elements and from screen-internal elements whose owner is a planned file.
    """
    scheme_requirements = _scheme_requirements_by_id(scheme_model)
    enriched_paths: list[str] = []

    for item in normalized:
        requirements = item.setdefault("requirements", [])
        before = list(requirements)
        for scheme_id in item.get("scheme_elements") or []:
            _append_unique(requirements, scheme_requirements.get(str(scheme_id), []))
        if requirements != before and item.get("path"):
            enriched_paths.append(str(item["path"]))

    design = proposal.get("design_delta") if isinstance(proposal.get("design_delta"), dict) else {}
    for element in _design_elements(design):
        if str(element.get("implementation_mode") or "") != "screen_internal":
            continue
        element_id = str(element.get("id") or "").strip()
        owner = str(element.get("owning_artifact") or element.get("owner") or "").strip()
        reqs = []
        req_values = element.get("requirements") or element.get("requirement_ids") or as_list(element.get("requirement_id"))
        for value in as_list(req_values):
            req_id = str(value).strip()
            if req_id and req_id not in reqs:
                reqs.append(req_id)
        _append_unique(reqs, scheme_requirements.get(element_id, []))
        if not owner or not reqs:
            continue
        for item in normalized:
            if item.get("kind") == "validation_test" or item.get("policy") == "read_only":
                continue
            if not _entry_matches_owner(item, owner):
                continue
            changed = _append_unique(item.setdefault("requirements", []), reqs)
            if element_id:
                _append_unique(item.setdefault("scheme_elements", []), [element_id])
            if changed and item.get("path"):
                enriched_paths.append(str(item["path"]))

    if enriched_paths:
        warnings.append({
            "code": "requirement_links_enriched_from_scheme",
            "paths": sorted(set(enriched_paths)),
            "message": "Some file-plan requirement links were inferred from scheme_model requirements or screen-internal design_delta ownership.",
        })

def _slice_requirement_ids(implementation_slice: dict[str, Any]) -> list[str]:
    values = implementation_slice.get("requirements") or implementation_slice.get("requirement_ids") or []
    result: list[str] = []
    for value in values:
        req_id = str(value).strip()
        if req_id and req_id not in result:
            result.append(req_id)
    return result


def _check_requirement_ids(check: dict[str, Any]) -> list[str]:
    values = check.get("requirements") or check.get("requirement_ids") or as_list(check.get("requirement_id"))
    result: list[str] = []
    for value in values:
        req_id = str(value).strip()
        if req_id and req_id not in result:
            result.append(req_id)
    return result


def _validate_slice_requirement_coverage(
    *,
    implementation_slice: dict[str, Any],
    normalized: list[dict[str, Any]],
    validation_plan: dict[str, Any] | None,
    dropped_validation_check_ids: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Ensure primary slice requirements do not disappear from the plan.

    Plan validation previously accepted plans that covered only a subset of
    ``implementation_slice.requirements``. Traceability then reported a green
    result for the covered subset and silently omitted the missing requirement.
    This is a core pipeline contract issue, not a style preference: every
    primary requirement in the slice must be linked to at least one planned
    implementation file and at least one validation check.
    """
    required_ids = _slice_requirement_ids(implementation_slice)
    if not required_ids:
        return [], []

    implementation_covered: set[str] = set()
    for item in normalized:
        if item.get("kind") == "validation_test":
            continue
        if item.get("policy") == "read_only":
            continue
        for req_id in item.get("requirements") or []:
            implementation_covered.add(str(req_id))

    validation_covered: set[str] = set()
    checks = (validation_plan or {}).get("checks") or (validation_plan or {}).get("validation_checks") or []
    for check in checks:
        if not isinstance(check, dict):
            continue
        check_id = str(check.get("id") or "")
        if check_id and check_id in dropped_validation_check_ids:
            continue
        for req_id in _check_requirement_ids(check):
            validation_covered.add(req_id)

    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for req_id in required_ids:
        if req_id not in implementation_covered:
            blockers.append({
                "code": "slice_requirement_missing_implementation_coverage",
                "requirement_id": req_id,
                "message": "Every requirement in implementation_slice must be linked to at least one planned implementation file.",
            })
        if req_id not in validation_covered:
            blockers.append({
                "code": "slice_requirement_missing_validation_coverage",
                "requirement_id": req_id,
                "message": "Every requirement in implementation_slice must be linked to at least one validation check.",
            })
    return blockers, warnings

def _load_implementation_slice(workspace: Path) -> dict[str, Any]:
    path = workspace / "prototype" / "input" / "implementation_slice.json"
    if not path.exists():
        return {}
    data = read_json(path)
    return data if isinstance(data, dict) else {}


def _normalized_file_plan(
    proposal: dict[str, Any],
    implementation_slice: dict[str, Any],
    contract: dict[str, Any],
    normalized: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "slice_id": proposal.get("slice_id") or implementation_slice.get("slice_id"),
        "source": "plan_proposal",
        "architecture_contract": contract.get("id"),
        "allowed_files": normalized,
        "forbidden_policy": "deny_all_not_listed",
        "notes": [
            "File names, targets, artifact types, and file operations come from agent-generated plan and validation plan proposals.",
            "This validator checks format and machine-readable safety boundaries from the architecture contract; it does not repair or reinterpret the plan's architectural meaning.",
            "Validation test file names are copied from validation_plan_proposal.json; they are not generated statically.",
        ],
    }
