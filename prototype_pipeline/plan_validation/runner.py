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

    design_blockers, design_warnings = validate_design_delta(
        proposal,
        implementation_slice,
        load_scheme_model(workspace),
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
            "File names and targets come from agent-generated plan and validation plan proposals.",
            "This validator checks formal architecture-contract boundaries and metadata; it does not infer feature semantics.",
            "Validation test file names are copied from validation_plan_proposal.json; they are not generated statically.",
        ],
    }
