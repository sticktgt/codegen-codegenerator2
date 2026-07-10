from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common import read_json, write_json


def _requirements_by_id(run: Path) -> dict[str, str | None]:
    path = run / "input" / "requirements.json"
    if not path.exists():
        return {}
    data = read_json(path)
    return {item.get("id"): item.get("text") for item in data.get("requirements", []) if item.get("id")}




def _slice_requirement_ids(run: Path) -> set[str]:
    run_input_path = run / "input" / "run_input.json"
    if run_input_path.exists():
        data = read_json(run_input_path)
        values = (data.get("slice") or {}).get("requirement_ids") or []
        return {str(value) for value in values if value}
    implementation_slice_path = run / "input" / "implementation_slice.json"
    if implementation_slice_path.exists():
        data = read_json(implementation_slice_path)
        values = data.get("requirements") or data.get("requirement_ids") or []
        return {str(value) for value in values if value}
    return set()


def _is_rerun_existing_check(check: dict[str, Any]) -> bool:
    """Return True for validation checks that only re-run preserved behavior.

    These checks prove that an existing behavior still works without requiring
    the related implementation file to be changed. Backend/API regressions use
    ``rerun_existing``; browser/e2e regressions use ``rerun_behavior_test``.
    Treat both as ``validated_unchanged`` candidates in traceability.
    """
    intent = str(check.get("validation_intent") or "").lower()
    return intent in {"rerun_existing", "rerun_behavior_test"}


def _is_functional_check(check: dict[str, Any]) -> bool:
    return str(check.get("type", "")).lower() in {"api", "service", "unit", "integration", "e2e", "browser_e2e", "ui_behavior"}

def _load_trace_plan(run: Path) -> dict[str, Any]:
    file_plan_path = run / "input" / "file_plan.json"
    if not file_plan_path.exists():
        raise SystemExit(f"Missing required file plan for traceability: {file_plan_path}")
    file_plan = read_json(file_plan_path)
    texts = _requirements_by_id(run)
    primary_requirement_ids = _slice_requirement_ids(run)
    by_req: dict[str, dict[str, Any]] = {}

    # Seed traceability from the implementation slice, not only from file_plan.
    # Otherwise a bad plan can silently omit a primary requirement and still
    # produce a green traceability report for the remaining subset.
    for req_id in sorted(primary_requirement_ids):
        by_req.setdefault(req_id, {
            "requirement_id": req_id,
            "text": texts.get(req_id),
            "scheme_elements": [],
            "allowed_files": [],
        })

    for item in file_plan.get("allowed_files", []):
        for req_id in item.get("requirements", []) or []:
            by_req.setdefault(req_id, {
                "requirement_id": req_id,
                "text": texts.get(req_id),
                "scheme_elements": [],
                "allowed_files": [],
            })
            scheme_values = item.get("scheme_elements") or []
            if item.get("scheme_element_id"):
                scheme_values.append(item["scheme_element_id"])
            for scheme in scheme_values:
                if scheme and scheme not in by_req[req_id]["scheme_elements"]:
                    by_req[req_id]["scheme_elements"].append(scheme)
            if item.get("path") and item["path"] not in by_req[req_id]["allowed_files"]:
                by_req[req_id]["allowed_files"].append(item["path"])
    return {"slice_id": file_plan.get("slice_id"), "items": list(by_req.values())}


def _validation_checks(run: Path) -> list[dict[str, Any]]:
    paths = [run / "input" / "validation_plan.json", run / "agent_reports" / "validation_plan_proposal.json"]
    for path in paths:
        if path.exists():
            plan = read_json(path)
            return plan.get("checks", []) or plan.get("validation_checks", []) or []
    return []


def _check_matches_requirement(check: dict[str, Any], requirement_id: str) -> bool:
    values = check.get("requirements") or check.get("requirement_ids") or [check.get("requirement_id")]
    return requirement_id in values


def _planned_paths(plan: dict[str, Any]) -> set[str]:
    paths: set[str] = set()
    for item in plan.get("items", []):
        for path in item.get("allowed_files") or []:
            paths.add(path)
    return paths


def _hunks_for(path: str, hunks_by_file: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    locations = []
    for hunk in hunks_by_file.get(path, []):
        locations.append({
            "file": path,
            "type": hunk.get("type", "diff_hunk"),
            "old_start": hunk.get("old_start"),
            "old_lines": hunk.get("old_lines"),
            "new_start": hunk.get("new_start"),
            "new_lines": hunk.get("new_lines"),
            "added_preview": hunk.get("added_preview", []),
            "removed_preview": hunk.get("removed_preview", []),
        })
    return locations


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, type=Path)
    args = parser.parse_args()

    plan = _load_trace_plan(args.run)
    changed = read_json(args.run / "output" / "changed_files.json") if (args.run / "output" / "changed_files.json").exists() else {"changed_files": []}
    validation = read_json(args.run / "output" / "validation_result.json") if (args.run / "output" / "validation_result.json").exists() else {"status": "not_run"}
    ui_static = read_json(args.run / "output" / "ui_static_check_result.json") if (args.run / "output" / "ui_static_check_result.json").exists() else {"status": "not_run"}
    validation_checks = _validation_checks(args.run)
    primary_requirement_ids = _slice_requirement_ids(args.run)

    changed_set = set(changed.get("changed_files", []))
    missing_required_by_path = {item.get("path"): item for item in changed.get("missing_required_changes", [])}
    hunks_by_file: dict[str, list[dict[str, Any]]] = {}
    for hunk in changed.get("diff_hunks", []):
        if hunk.get("file"):
            hunks_by_file.setdefault(hunk["file"], []).append(hunk)

    items = []
    for item in plan.get("items", []):
        requirement_id = item["requirement_id"]
        allowed_files = item.get("allowed_files") or []
        touched = [path for path in allowed_files if path in changed_set]
        locations = []
        for path in touched:
            locations.extend(_hunks_for(path, hunks_by_file))
        existing_or_touched = bool(touched)
        missing_required_changes = [missing_required_by_path[path] for path in allowed_files if path in missing_required_by_path]
        boundary_ok = changed.get("boundary_status") != "failed"
        executable_checks = [
            check for check in validation_checks
            if _check_matches_requirement(check, requirement_id)
            and (check.get("executable_validation") or check.get("proposed_file"))
        ]
        functional_executable_checks = [
            check for check in executable_checks
            if _is_functional_check(check)
        ]
        # A lightweight web UI kit may not have browser/e2e tests yet. When the
        # planner explicitly proposes a ui_static check and the UI static phase
        # passes, treat it as a functional static validation for UI-control
        # traceability. It proves anchors/control linkage, not full browser
        # behavior; the check remains separately visible as ui_static.
        ui_static_checks = [
            check for check in validation_checks
            if _check_matches_requirement(check, requirement_id)
            and str(check.get("type", "")).lower() in {"ui_static"}
        ]
        if ui_static.get("status") == "passed":
            functional_executable_checks.extend(ui_static_checks)
        supporting_checks = [
            check for check in validation_checks
            if _check_matches_requirement(check, requirement_id)
            and str(check.get("type", "")).lower() in {"build", "smoke", "static", "ui_static"}
        ]
        validation_ok = validation.get("status") == "passed" and boundary_ok and ui_static.get("status") != "failed"
        is_primary_requirement = not primary_requirement_ids or requirement_id in primary_requirement_ids
        is_rerun_only = bool(functional_executable_checks) and all(_is_rerun_existing_check(check) for check in functional_executable_checks)
        role = "primary" if is_primary_requirement else "supporting_regression"
        if missing_required_changes:
            status = "planned_changes_missing"
        elif validation_ok and existing_or_touched and functional_executable_checks:
            status = "implemented_and_validated"
        elif validation_ok and not existing_or_touched and is_rerun_only:
            status = "validated_unchanged"
        elif existing_or_touched:
            status = "implemented_not_validated"
        else:
            status = "not_changed"
        items.append({
            "requirement_id": requirement_id,
            "role": role,
            "primary_requirement": is_primary_requirement,
            "text": item.get("text"),
            "scheme_elements": item.get("scheme_elements", []),
            "allowed_files": allowed_files,
            "changed_files": touched,
            "locations": locations,
            "validation_checks": [check for check in validation_checks if _check_matches_requirement(check, requirement_id)],
            "executable_validation_checks": executable_checks,
            "functional_executable_validation_checks": functional_executable_checks,
            "supporting_validation_checks": supporting_checks,
            "missing_required_changes": missing_required_changes,
            "status": status,
        })

    planned_paths = _planned_paths(plan)
    unplanned_changes = []
    non_semantic_by_path = {item.get("path"): item for item in changed.get("non_semantic_changes", [])}
    policy_by_path = {item.get("path"): item for item in changed.get("policy_violations", [])}
    unexpected_set = set(changed.get("unexpected_files", []))
    for path in changed.get("changed_files", []):
        if path in planned_paths and path not in unexpected_set and path not in policy_by_path:
            continue
        status = "unexpected" if path in unexpected_set else "unplanned"
        if path in policy_by_path:
            status = "policy_violation"
        if path in non_semantic_by_path:
            status = "non_semantic_runtime_change"
        unplanned_changes.append({
            "file": path,
            "status": status,
            "policy_violation": policy_by_path.get(path),
            "non_semantic_change": non_semantic_by_path.get(path),
            "locations": _hunks_for(path, hunks_by_file),
        })

    traceability = {
        "slice_id": plan.get("slice_id"),
        "primary_requirement_ids": sorted(primary_requirement_ids),
        "validation_status": validation.get("status"),
        "validation_environment_issue": validation.get("environment_issue"),
        "ui_static_status": ui_static.get("status"),
        "boundary_status": changed.get("boundary_status"),
        "items": items,
        "unplanned_changes": unplanned_changes,
        "unexpected_files": changed.get("unexpected_files", []),
        "policy_violations": changed.get("policy_violations", []),
        "missing_required_changes": changed.get("missing_required_changes", []),
        "runtime_mutated_files": changed.get("runtime_mutated_files", []),
        "non_semantic_changes": changed.get("non_semantic_changes", []),
        "missing_required_files": changed.get("missing_required_files", []),
        "created_files": changed.get("created_files", []),
        "modified_files": changed.get("modified_files", []),
        "deleted_files": changed.get("deleted_files", []),
    }
    write_json(args.run / "output" / "code_traceability.json", traceability)

    valid_statuses = {"implemented_and_validated", "validated_unchanged"}
    status_counts: dict[str, int] = {}
    for item in items:
        status = str(item.get("status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

    gaps = [item for item in items if item.get("status") not in valid_statuses]
    primary_count = len([item for item in items if item.get("primary_requirement")])
    supporting_count = len(items) - primary_count
    counts_text = ", ".join(f"{status}={count}" for status, count in sorted(status_counts.items())) or "none"

    print("Wrote code_traceability.json")
    print(
        "Traceability summary: "
        f"slice={traceability.get('slice_id') or 'unknown'}, "
        f"primary={primary_count}, supporting={supporting_count}, "
        f"validation={validation.get('status')}, ui_static={ui_static.get('status')}, "
        f"boundary={changed.get('boundary_status')}, gaps={len(gaps)}, {counts_text}"
    )
    for item in items:
        checks = item.get("functional_executable_validation_checks") or []
        intents = sorted({str(check.get("validation_intent") or "none") for check in checks})
        changed_files = item.get("changed_files") or []
        print(
            f"- {item.get('requirement_id')} "
            f"[{item.get('role')}]: {item.get('status')}; "
            f"changed_files={len(changed_files)}; "
            f"functional_checks={len(checks)}; "
            f"intents={','.join(intents) if intents else 'none'}"
        )
    if gaps:
        print("Traceability coverage gaps:")
        for item in gaps:
            print(
                f"- {item.get('requirement_id')} "
                f"[{item.get('role')}]: {item.get('status')}; "
                f"allowed_files={item.get('allowed_files') or []}; "
                f"changed_files={item.get('changed_files') or []}"
            )


if __name__ == "__main__":
    main()
