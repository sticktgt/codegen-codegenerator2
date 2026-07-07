from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.common import read_json, write_json

from prototype_pipeline.reports.run_report import write_simple_report
from prototype_pipeline.reports.scenario_result import build_scenario_result

PHASE_ORDER = ["plan", "plan-review", "implementation", "repair-001", "repair-002"]


def usage_phases(run: Path) -> list[dict[str, Any]]:
    usage_dir = run / "usage"
    phases = []
    order = {name: index for index, name in enumerate(PHASE_ORDER)}
    for path in sorted(usage_dir.glob("*.delta.json"), key=lambda p: (order.get(p.stem.replace(".delta", ""), 999), p.name)):
        phases.append(read_json(path))
    return phases


def opencode_results(output: Path) -> list[dict[str, Any]]:
    results = [read_json(path) for path in output.glob("opencode_*_result.json")]
    order = {name: index for index, name in enumerate(PHASE_ORDER)}
    return sorted(results, key=lambda item: (order.get(item.get("phase"), 999), item.get("phase") or ""))


def requested_models(opencode_results_data: list[dict[str, Any]], usage_phases_data: list[dict[str, Any]]) -> list[str]:
    models: list[str] = []
    for item in opencode_results_data:
        model = item.get("model")
        if model and model not in models:
            models.append(model)
    for item in usage_phases_data:
        model = item.get("requested_model")
        if model and model not in models:
            models.append(model)
    return models


def usage_totals(usage_phases_data: list[dict[str, Any]]) -> dict[str, Any]:
    total = {
        "duration_seconds": 0.0,
        "sessions_delta": 0,
        "messages_delta": 0,
        "model_messages_delta": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "cost": 0.0,
    }
    tool_usage: dict[str, int] = {}
    for phase in usage_phases_data:
        total["duration_seconds"] += float(phase.get("duration_seconds") or 0)
        llm = phase.get("llm_usage", {}) or {}
        for key in ["sessions_delta", "messages_delta", "model_messages_delta", "input_tokens", "output_tokens", "total_tokens"]:
            total[key] += int(llm.get(key) or 0)
        total["cost"] += float(llm.get("cost") or 0)
        for tool, count in (phase.get("tool_usage", {}) or {}).items():
            tool_usage[tool] = tool_usage.get(tool, 0) + int(count or 0)
    total["duration_seconds"] = round(total["duration_seconds"], 3)
    total["cost"] = round(total["cost"], 6)
    return {"llm_usage": total, "tool_usage": dict(sorted(tool_usage.items()))}


def boundary_result(run: Path) -> dict[str, Any]:
    path = run / "output" / "changed_files.json"
    if not path.exists():
        return {"status": "not_run"}
    changed = read_json(path)
    return {
        "status": changed.get("boundary_status") or ("failed" if changed.get("unexpected_files") or changed.get("missing_required_files") else "passed"),
        "unexpected_files": changed.get("unexpected_files", []),
        "policy_violations": changed.get("policy_violations", []),
        "missing_required_files": changed.get("missing_required_files", []),
        "missing_required_changes": changed.get("missing_required_changes", []),
        "runtime_mutated_files": changed.get("runtime_mutated_files", []),
        "non_semantic_changes": changed.get("non_semantic_changes", []),
    }


def summarize(run: Path) -> dict[str, Any]:
    output = run / "output"
    usage_phase_data = usage_phases(run)
    validation = read_json(output / "validation_result.json") if (output / "validation_result.json").exists() else {"status": "not_run"}
    changed = read_json(output / "changed_files.json") if (output / "changed_files.json").exists() else None
    boundary = boundary_result(run)
    plan_validation = read_json(output / "plan_validation_result.json") if (output / "plan_validation_result.json").exists() else None
    traceability = read_json(output / "code_traceability.json") if (output / "code_traceability.json").exists() else None
    ui_static = read_json(output / "ui_static_check_result.json") if (output / "ui_static_check_result.json").exists() else None
    opencode_result_data = opencode_results(output)
    model_names = requested_models(opencode_result_data, usage_phase_data)

    final_status = "passed"
    if validation.get("status") == "environment_failed":
        final_status = "environment_failed"
    if plan_validation and plan_validation.get("status") != "passed":
        final_status = "failed"
    if boundary.get("status") == "failed":
        final_status = "failed"
    if validation.get("status") == "failed":
        final_status = "failed"
    if ui_static and ui_static.get("status") == "failed":
        final_status = "failed"
    if any(result.get("status") == "failed" for result in opencode_result_data):
        final_status = "failed"
    traceability_incomplete = []
    traceability_valid_statuses = {"implemented_and_validated", "validated_unchanged"}
    if traceability:
        traceability_incomplete = [
            item for item in traceability.get("items", [])
            if item.get("status") not in traceability_valid_statuses
        ]
        if traceability_incomplete and final_status == "passed":
            final_status = "failed"

    summary = {
        "run": str(run),
        "final_status": final_status,
        "requested_models": model_names,
        "opencode_results": opencode_result_data,
        "usage_phases": usage_phase_data,
        "usage_totals": usage_totals(usage_phase_data),
        "plan_validation": plan_validation,
        "boundary": boundary,
        "changed_files": changed,
        "validation": validation,
        "traceability": traceability,
        "ui_static": ui_static,
        "traceability_incomplete": traceability_incomplete,
        "agent_reports": read_json(output / "agent_reports.json") if (output / "agent_reports.json").exists() else None,
        "sync_run_inputs": read_json(output / "sync_run_inputs_result.json") if (output / "sync_run_inputs_result.json").exists() else None,
        "sync_prompt_files": read_json(output / "sync_prompt_files_result.json") if (output / "sync_prompt_files_result.json").exists() else None,
        "diagnostics": read_json(output / "run_diagnostics_result.json") if (output / "run_diagnostics_result.json").exists() else None,
        "pipeline_events": "output/pipeline_events.jsonl",
        "simple_report": "output/run_report.md",
    }
    summary["scenario_result"] = "output/scenario_result.json"
    write_json(output / "run_summary.json", summary)
    build_scenario_result(run, summary)
    write_simple_report(run, summary)
    return summary
