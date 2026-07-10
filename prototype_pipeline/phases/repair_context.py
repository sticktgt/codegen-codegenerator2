from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from tools.common import write_json


MAX_TAIL_LINES = 80
MAX_RELEVANT_PATHS = 60


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"_read_error": f"failed to parse {path}"}
    return data if isinstance(data, dict) else {"value": data}


def _tail(path: Path, *, lines: int = MAX_TAIL_LINES) -> list[str]:
    if not path.exists():
        return []
    try:
        content = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return []
    return content[-lines:]


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    return [value]


def _compact_boundary(changed_files: dict[str, Any]) -> dict[str, Any]:
    boundary_status = changed_files.get("boundary_status") or changed_files.get("status")
    return {
        "status": boundary_status,
        "unexpected_files": _as_list(changed_files.get("unexpected_files")),
        "policy_violations": _as_list(changed_files.get("policy_violations")),
        "missing_required_files": _as_list(changed_files.get("missing_required_files")),
        "missing_required_changes": _as_list(changed_files.get("missing_required_changes")),
        "non_semantic": _as_list(changed_files.get("non_semantic"))[:20],
    }


def _compact_ui_static(ui_static: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": ui_static.get("status"),
        "blockers": _as_list(ui_static.get("blockers")),
        "warnings": _as_list(ui_static.get("warnings")),
    }


def _compact_stage(stage: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": stage.get("name") or stage.get("stage"),
        "status": stage.get("status"),
        "exit_code": stage.get("exit_code"),
        "duration_seconds": stage.get("duration_seconds"),
        "blocked_by_failed_stages": _as_list(stage.get("blocked_by_failed_stages")),
        "diagnostic_reliability": stage.get("diagnostic_reliability"),
        "repair_priority": stage.get("repair_priority"),
    }


def _compact_validation(validation: dict[str, Any]) -> dict[str, Any]:
    stages = _as_list(validation.get("stages"))
    return {
        "status": validation.get("status"),
        "failed_stages": _as_list(validation.get("failed_stages")),
        "root_failed_stages": _as_list(validation.get("root_failed_stages")),
        "downstream_failed_stages": _as_list(validation.get("downstream_failed_stages")),
        "stages": [_compact_stage(stage) for stage in stages if isinstance(stage, dict)],
    }


_PATH_RE = re.compile(r"\b(?:backend|frontend|prototype)/(?:[\w@./:+-]+)")


def _collect_paths_from_object(value: Any, paths: set[str]) -> None:
    if isinstance(value, dict):
        for item in value.values():
            _collect_paths_from_object(item, paths)
    elif isinstance(value, list):
        for item in value:
            _collect_paths_from_object(item, paths)
    elif isinstance(value, str):
        for match in _PATH_RE.finditer(value):
            path = match.group(0).rstrip(".,:;])}")
            if not any(part in path for part in ("node_modules", "__pycache__", "test-results", "dist/")):
                paths.add(path)


def _previous_repair_summaries(run: Path, current_attempt: int) -> list[dict[str, Any]]:
    output_dir = run / "output"
    workspace_output = run / "workspace" / "prototype" / "output"
    summaries: list[dict[str, Any]] = []
    for attempt in range(1, current_attempt):
        phase = f"repair-{attempt:03d}"
        result = _read_json(output_dir / f"opencode_{phase}_result.json")
        report = _read_json(workspace_output / "repair_report.json") if attempt == current_attempt - 1 else {}
        summaries.append({
            "phase": phase,
            "status": result.get("status"),
            "completion_mode": result.get("completion_mode"),
            "diagnostic_command_guard_triggered": result.get("diagnostic_command_guard_triggered"),
            "interactive_playwright_guard_triggered": result.get("interactive_playwright_guard_triggered"),
            "tool_failures_count": len(_as_list(result.get("tool_failures"))),
            "tolerated_tool_failures_count": len(_as_list(result.get("tolerated_tool_failures"))),
            "repair_report_status": report.get("status"),
            "repair_report_summary": report.get("summary"),
        })
    return summaries


def write_repair_context(run: Path, *, attempt: int, max_attempts: int) -> Path:
    """Write a compact, repair-oriented context file into run and workspace output.

    The context is not a validator. It summarizes already-collected diagnostics so
    the repair agent can make a targeted fix and then hand control back to the
    pipeline for official post-repair checks.
    """
    output_dir = run / "output"
    workspace_output = run / "workspace" / "prototype" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    workspace_output.mkdir(parents=True, exist_ok=True)

    changed_files = _read_json(output_dir / "changed_files.json")
    ui_static = _read_json(output_dir / "ui_static_check_result.json")
    validation = _read_json(output_dir / "validation_result.json")

    relevant_paths: set[str] = set()
    for obj in (changed_files, ui_static, validation):
        _collect_paths_from_object(obj, relevant_paths)

    context = {
        "version": 1,
        "attempt": attempt,
        "max_attempts": max_attempts,
        "purpose": (
            "Repair context for the next OpenCode repair phase. Use it to make a targeted fix; "
            "the pipeline will run official collect_changes, ui_static, validation, and traceability after the phase."
        ),
        "repair_strategy": [
            "Fix root failures first: boundary violations, ui_static blockers, then validation root_failed_stages.",
            "Make one coherent targeted change set; do not broaden scope or add new requirements.",
            "Use file_plan.json as the writable-file contract.",
            "Avoid an internal loop of full e2e/pytest reruns. A narrow check is acceptable, but official validation runs after repair.",
            "If more failures remain, the next repair attempt will receive an updated repair_context.json.",
        ],
        "source_files": {
            "repair_context": "prototype/output/repair_context.json",
            "changed_files": "prototype/output/changed_files.json",
            "ui_static": "prototype/output/ui_static_check_result.json",
            "validation_result": "prototype/output/validation_result.json",
            "validation_stdout_log": "prototype/output/validation.stdout.log",
            "validation_stderr_log": "prototype/output/validation.stderr.log",
            "file_plan": "prototype/input/file_plan.json",
        },
        "boundary": _compact_boundary(changed_files),
        "ui_static": _compact_ui_static(ui_static),
        "validation": _compact_validation(validation),
        "previous_repairs": _previous_repair_summaries(run, attempt),
        "relevant_workspace_paths": sorted(relevant_paths)[:MAX_RELEVANT_PATHS],
        "validation_log_tails": {
            "stdout": _tail(output_dir / "validation.stdout.log"),
            "stderr": _tail(output_dir / "validation.stderr.log"),
        },
    }

    workspace_path = workspace_output / "repair_context.json"
    run_path = output_dir / "repair_context.json"
    write_json(workspace_path, context)
    write_json(run_path, context)
    return workspace_path
