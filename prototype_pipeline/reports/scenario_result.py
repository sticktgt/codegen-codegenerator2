from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.common import read_json, write_json


SCENARIO_RESULT_VERSION = 1


SUCCESS_TRACEABILITY_STATUSES = {"implemented_and_validated", "validated_unchanged"}


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return read_json(path)


def _rel_to_run(run: Path, path: str | Path | None) -> str | None:
    if path is None:
        return None
    raw = Path(path)
    if not raw.is_absolute():
        raw_text = raw.as_posix()
        run_text = run.as_posix().rstrip("/")
        prefix = run_text + "/"
        if raw_text.startswith(prefix):
            return raw_text[len(prefix):]
        return raw_text
    try:
        return raw.relative_to(run.resolve()).as_posix()
    except ValueError:
        return raw.as_posix()


def _stage_status(summary: dict[str, Any]) -> dict[str, Any]:
    opencode = {item.get("phase"): item.get("status") for item in summary.get("opencode_results") or []}
    return {
        "plan": opencode.get("plan", "not_run"),
        "plan_review": opencode.get("plan-review", "not_run"),
        "implementation": opencode.get("implementation", "not_run"),
        "repair": opencode.get("repair-001", "not_run"),
        "plan_validation": (summary.get("plan_validation") or {}).get("status", "not_run"),
        "boundary": (summary.get("boundary") or {}).get("status", "not_run"),
        "ui_static": (summary.get("ui_static") or {}).get("status", "not_run"),
        "validation": (summary.get("validation") or {}).get("status", "not_run"),
        "traceability": "passed" if not summary.get("traceability_incomplete") else "incomplete",
        "final": summary.get("final_status", "unknown"),
    }


def _slice_info(run: Path, traceability: dict[str, Any]) -> dict[str, Any]:
    run_input = _load_json(run / "input" / "run_input.json", {})
    implementation_slice = _load_json(run / "input" / "implementation_slice.json", {})
    slice_data = run_input.get("slice") or implementation_slice or {}
    return {
        "slice_id": slice_data.get("slice_id") or traceability.get("slice_id"),
        "title": slice_data.get("title"),
        "goal": slice_data.get("goal"),
        "change_type": slice_data.get("change_type"),
        "requirement_ids": slice_data.get("requirement_ids") or slice_data.get("requirements") or traceability.get("primary_requirement_ids") or [],
        "acceptance_criteria": slice_data.get("acceptance_criteria") or [],
        "source": run_input.get("source") or implementation_slice.get("source"),
    }


def _changed_files_summary(changed: dict[str, Any] | None) -> dict[str, Any]:
    changed = changed or {}
    semantic_changed = changed.get("semantic_changed_files")
    if semantic_changed is None:
        non_semantic_paths = {item.get("path") for item in changed.get("non_semantic_changes", [])}
        semantic_changed = [path for path in changed.get("changed_files", []) if path not in non_semantic_paths]
    return {
        "boundary_status": changed.get("boundary_status", "not_run"),
        "semantic_changed_files": semantic_changed,
        "created_files": changed.get("created_files", []),
        "modified_files": changed.get("modified_files", []),
        "deleted_files": changed.get("deleted_files", []),
        "renamed_files": changed.get("renamed_files", []),
        "read_only_unchanged_files": changed.get("unchanged_allowed_files", []),
        "unexpected_files": changed.get("unexpected_files", []),
        "policy_violations": changed.get("policy_violations", []),
        "missing_required_files": changed.get("missing_required_files", []),
        "missing_required_changes": changed.get("missing_required_changes", []),
        "runtime_non_semantic_changes": changed.get("non_semantic_changes", []),
        "counts": {
            "semantic_changed": len(semantic_changed),
            "created": len(changed.get("created_files", [])),
            "modified": len(changed.get("modified_files", [])),
            "deleted": len(changed.get("deleted_files", [])),
            "unexpected": len(changed.get("unexpected_files", [])),
            "policy_violations": len(changed.get("policy_violations", [])),
            "missing_required_files": len(changed.get("missing_required_files", [])),
            "missing_required_changes": len(changed.get("missing_required_changes", [])),
            "runtime_non_semantic": len(changed.get("non_semantic_changes", [])),
        },
    }


def _validation_summary(run: Path, summary: dict[str, Any], traceability: dict[str, Any]) -> dict[str, Any]:
    validation = summary.get("validation") or {}
    ui_static = summary.get("ui_static") or {}
    checks_by_id: dict[str, dict[str, Any]] = {}
    for item in traceability.get("items", []) or []:
        for check in item.get("validation_checks", []) or []:
            check_id = check.get("id")
            if check_id:
                checks_by_id.setdefault(check_id, check)
    checks = []
    for check in checks_by_id.values():
        checks.append({
            "id": check.get("id"),
            "type": check.get("type"),
            "requirement_id": check.get("requirement_id"),
            "scheme_element_id": check.get("scheme_element_id"),
            "description": check.get("description"),
            "validation_intent": check.get("validation_intent"),
            "proposed_file": check.get("proposed_file"),
            "executable": bool(check.get("proposed_file")) and check.get("type") != "ui_static",
        })
    checks.sort(key=lambda item: item.get("id") or "")
    return {
        "status": validation.get("status", "not_run"),
        "task": validation.get("task"),
        "duration_seconds": validation.get("duration_seconds"),
        "environment_issue": validation.get("environment_issue") or traceability.get("validation_environment_issue"),
        "stdout_log": validation.get("stdout_log"),
        "stderr_log": validation.get("stderr_log"),
        "ui_static": {
            "status": ui_static.get("status", "not_run"),
            "warnings": ui_static.get("warnings", []),
            "blockers": ui_static.get("blockers", []),
            "checked_files": ui_static.get("checked_files", []),
        },
        "checks": checks,
    }


def _traceability_summary(summary: dict[str, Any], traceability: dict[str, Any]) -> dict[str, Any]:
    items = []
    primary_requirements = []
    supporting_regressions = []
    gaps = []
    for item in traceability.get("items", []) or []:
        compact = {
            "requirement_id": item.get("requirement_id"),
            "role": item.get("role"),
            "status": item.get("status"),
            "primary_requirement": item.get("primary_requirement"),
            "changed_files": item.get("changed_files", []),
            "allowed_files": item.get("allowed_files", []),
            "scheme_elements": item.get("scheme_elements", []),
            "validation_check_ids": [check.get("id") for check in item.get("validation_checks", []) or [] if check.get("id")],
            "functional_check_ids": [check.get("id") for check in item.get("functional_executable_validation_checks", []) or [] if check.get("id")],
        }
        items.append(compact)
        if compact["role"] == "primary":
            primary_requirements.append(compact)
        else:
            supporting_regressions.append(compact)
        if compact["status"] not in SUCCESS_TRACEABILITY_STATUSES:
            gaps.append(compact)
    return {
        "status": "passed" if not gaps else "incomplete",
        "primary_requirement_ids": traceability.get("primary_requirement_ids", []),
        "validation_status": traceability.get("validation_status"),
        "ui_static_status": traceability.get("ui_static_status"),
        "boundary_status": traceability.get("boundary_status"),
        "items": items,
        "primary_requirements": primary_requirements,
        "supporting_regressions": supporting_regressions,
        "gaps": gaps,
        "counts": {
            "primary": len(primary_requirements),
            "supporting_regressions": len(supporting_regressions),
            "gaps": len(gaps),
        },
    }


def _repair_summary(summary: dict[str, Any]) -> dict[str, Any]:
    repairs = [item for item in summary.get("opencode_results") or [] if str(item.get("phase") or "").startswith("repair")]
    return {
        "used": bool(repairs),
        "phases": [
            {
                "phase": item.get("phase"),
                "status": item.get("status"),
                "duration_seconds": item.get("duration_seconds"),
                "missing_expected_outputs": item.get("missing_expected_outputs", []),
                "tool_failures": item.get("tool_failures", []),
            }
            for item in repairs
        ],
    }


def _artifact_summary(run: Path, summary: dict[str, Any]) -> dict[str, Any]:
    export_result = _load_json(run / "output" / "export_result.json", {})
    diagnostics = summary.get("diagnostics") or _load_json(run / "output" / "run_diagnostics_result.json", {})
    return {
        "prototype_artifact": _rel_to_run(run, export_result.get("artifact")),
        "diagnostics_archive": _rel_to_run(run, diagnostics.get("diagnostics_archive")),
        "run_report": "output/run_report.md",
        "run_summary": "output/run_summary.json",
        "scenario_result": "output/scenario_result.json",
        "code_traceability": "output/code_traceability.json",
        "workspace_diff": "output/workspace.diff" if (run / "output" / "workspace.diff").exists() else None,
    }


def build_scenario_result(run: Path, summary: dict[str, Any]) -> dict[str, Any]:
    output = run / "output"
    traceability = summary.get("traceability") or _load_json(output / "code_traceability.json", {})
    changed = summary.get("changed_files")
    result = {
        "scenario_result_version": SCENARIO_RESULT_VERSION,
        "run": str(run),
        "slice": _slice_info(run, traceability),
        "final_status": summary.get("final_status"),
        "stage_status": _stage_status(summary),
        "changed_files": _changed_files_summary(changed),
        "validation": _validation_summary(run, summary, traceability),
        "traceability": _traceability_summary(summary, traceability),
        "repair": _repair_summary(summary),
        "artifacts": _artifact_summary(run, summary),
        "usage": {
            "requested_models": summary.get("requested_models", []),
            "totals": summary.get("usage_totals", {}),
            "phases": [
                {
                    "phase": item.get("phase"),
                    "duration_seconds": item.get("duration_seconds"),
                    "requested_model": item.get("requested_model"),
                    "llm_usage": item.get("llm_usage", {}),
                }
                for item in summary.get("usage_phases") or []
            ],
        },
        "inputs": {
            "run_input": "input/run_input.json" if (run / "input" / "run_input.json").exists() else None,
            "implementation_slice": "input/implementation_slice.json" if (run / "input" / "implementation_slice.json").exists() else None,
            "file_plan": "input/file_plan.json" if (run / "input" / "file_plan.json").exists() else None,
            "validation_plan": "input/validation_plan.json" if (run / "input" / "validation_plan.json").exists() else None,
        },
    }
    write_json(output / "scenario_result.json", result)
    return result
