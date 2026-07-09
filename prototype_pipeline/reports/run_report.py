from __future__ import annotations

from pathlib import Path
from typing import Any


def format_int(value: Any) -> str:
    try:
        return f"{int(value):,}".replace(",", " ")
    except Exception:
        return str(value)


def write_simple_report(run: Path, summary: dict[str, Any]) -> None:
    lines = []
    lines.append("# Pipeline run report")
    lines.append("")
    lines.append(f"Run: `{summary.get('run')}`")
    models = summary.get("requested_models") or []
    if models:
        lines.append(f"Model: `{', '.join(models)}`")
    lines.append(f"Final status: **{summary.get('final_status')}**")
    lines.append(f"Scenario result: `{summary.get('scenario_result', 'output/scenario_result.json')}`")
    validation = summary.get("validation") or {}
    boundary = summary.get("boundary") or {}
    lines.append(f"Validation: `{validation.get('status', 'not_run')}`")
    environment_issue = validation.get("environment_issue") or {}
    if environment_issue:
        lines.append(f"Validation environment issue: `{environment_issue.get('code')}`")
    failed_stages = [stage for stage in validation.get("stages", []) if stage.get("status") == "failed"]
    root_failed = validation.get("root_failed_stages") or [
        stage for stage in failed_stages if not stage.get("blocked_by_failed_stages")
    ]
    downstream_failed = validation.get("downstream_failed_stages") or [
        stage for stage in failed_stages if stage.get("blocked_by_failed_stages")
    ]
    if failed_stages:
        lines.append("Validation failed stages: " + ", ".join(f"`{stage.get('name')}`" for stage in failed_stages))
    if root_failed:
        lines.append("Root failed stages: " + ", ".join(f"`{stage.get('name')}`" for stage in root_failed))
    if downstream_failed:
        lines.append("Downstream/context failed stages: " + ", ".join(f"`{stage.get('name')}`" for stage in downstream_failed))
    lines.append(f"File boundary: `{boundary.get('status', 'not_run')}`")
    incomplete = summary.get("traceability_incomplete") or []
    if incomplete:
        lines.append(f"Traceability coverage: `incomplete ({len(incomplete)})`")
    lines.append("")
    lines.append("## Steps")
    lines.append("")
    lines.append("| Step | Status | Duration | Input tokens | Output tokens | Messages | Tool calls |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    usage_by_phase = {item.get("phase"): item for item in summary.get("usage_phases", [])}
    for result in summary.get("opencode_results", []):
        phase = result.get("phase")
        usage = usage_by_phase.get(phase, {})
        llm = usage.get("llm_usage", {}) or {}
        tools = usage.get("tool_usage", {}) or {}
        lines.append(
            f"| {phase} | {result.get('status')} | {result.get('duration_seconds', 0)}s | "
            f"{format_int(llm.get('input_tokens', 0))} | {format_int(llm.get('output_tokens', 0))} | "
            f"{format_int(llm.get('messages_delta', 0))} | {format_int(sum(int(v or 0) for v in tools.values()))} |"
        )
    totals = summary.get("usage_totals", {}).get("llm_usage", {})
    tool_total = sum(int(v or 0) for v in summary.get("usage_totals", {}).get("tool_usage", {}).values())
    lines.append(
        f"| **Total OpenCode** |  | {totals.get('duration_seconds', 0)}s | "
        f"{format_int(totals.get('input_tokens', 0))} | {format_int(totals.get('output_tokens', 0))} | "
        f"{format_int(totals.get('messages_delta', 0))} | {format_int(tool_total)} |"
    )
    unreliable_usage = [
        item for item in summary.get("usage_phases", [])
        if (item.get("quality") or {}).get("status") == "unreliable"
    ]
    if unreliable_usage:
        lines.append("")
        lines.append("Usage metrics warnings:")
        for item in unreliable_usage:
            quality = item.get("quality") or {}
            lines.append(
                f"- `{item.get('phase')}`: {quality.get('message', 'usage metrics are approximate')}"
            )
    lines.append("")
    changed = summary.get("changed_files") or {}
    lines.append("## Files")
    lines.append("")
    semantic_changed = changed.get("semantic_changed_files")
    if semantic_changed is None:
        non_semantic_paths = {item.get("path") for item in changed.get("non_semantic_changes", [])}
        semantic_changed = [path for path in changed.get("changed_files", []) if path not in non_semantic_paths]
    lines.append(f"Semantic changed: `{len(semantic_changed)}`")
    lines.append(f"Total changed including runtime/non-semantic: `{len(changed.get('changed_files', []))}`")
    lines.append(f"Created: `{len(changed.get('created_files', []))}`")
    lines.append(f"Modified: `{len(changed.get('modified_files', []))}`")
    lines.append(f"Unexpected: `{len(changed.get('unexpected_files', []))}`")
    lines.append(f"Policy violations: `{len(changed.get('policy_violations', []))}`")
    lines.append(f"Missing required files: `{len(changed.get('missing_required_files', []))}`")
    lines.append(f"Missing required changes: `{len(changed.get('missing_required_changes', []))}`")
    lines.append(f"Runtime/non-semantic changes: `{len(changed.get('non_semantic_changes', []))}`")
    if changed.get("unexpected_files"):
        lines.append("")
        lines.append("Unexpected files:")
        for path in changed.get("unexpected_files", []):
            lines.append(f"- `{path}`")
    if changed.get("policy_violations"):
        lines.append("")
        lines.append("Policy violations:")
        for item in changed.get("policy_violations", []):
            lines.append(f"- `{item.get('path')}`: {item.get('reason')} ({item.get('policy')})")
    if changed.get("missing_required_files"):
        lines.append("")
        lines.append("Missing required files:")
        for path in changed.get("missing_required_files", []):
            lines.append(f"- `{path}`")
    if changed.get("missing_required_changes"):
        lines.append("")
        lines.append("Missing required changes:")
        for item in changed.get("missing_required_changes", []):
            lines.append(f"- `{item.get('path')}`: {item.get('reason')} ({item.get('policy')})")

    stages = validation.get("stages") or []
    if stages:
        lines.append("")
        lines.append("## Validation stages")
        lines.append("")
        lines.append("| Stage | Status | Exit code | Duration | Blocked by | Repair priority |")
        lines.append("|---|---:|---:|---:|---|---|")
        for stage in stages:
            exit_code = stage.get("exit_code")
            blocked_by = ", ".join(str(value) for value in (stage.get("blocked_by_failed_stages") or []))
            lines.append(
                f"| {stage.get('name')} | {stage.get('status')} | "
                f"{'' if exit_code is None else exit_code} | {stage.get('duration_seconds', 0)}s | "
                f"{blocked_by} | {stage.get('repair_priority', '')} |"
            )

    if environment_issue:
        lines.append("")
        lines.append("## Validation environment issue")
        lines.append("")
        lines.append(f"Code: `{environment_issue.get('code')}`")
        if environment_issue.get("message"):
            lines.append(f"Message: {environment_issue.get('message')}")
        if environment_issue.get("missing_dependency"):
            lines.append(f"Missing dependency: `{environment_issue.get('missing_dependency')}`")
        if environment_issue.get("suggested_commands"):
            lines.append("")
            lines.append("Suggested setup commands:")
            for command in environment_issue.get("suggested_commands", []):
                lines.append(f"- `{command}`")
        if validation.get("stdout_log") or validation.get("stderr_log"):
            lines.append("")
            lines.append(f"Logs: `{validation.get('stdout_log')}`, `{validation.get('stderr_log')}`")


    diagnostics = summary.get("diagnostics") or {}
    if diagnostics.get("diagnostics_archive"):
        lines.append("")
        lines.append("## Diagnostics archive")
        lines.append("")
        lines.append(f"Archive: `{diagnostics.get('diagnostics_archive')}`")
        lines.append(f"Included files: `{diagnostics.get('included_file_count', 0)}`")

    sync = summary.get("sync_run_inputs") or {}
    if sync.get("warnings"):
        lines.append("")
        lines.append("Run input sync warnings:")
        for warning in sync.get("warnings", []):
            lines.append(f"- `{warning.get('code')}`: {warning.get('path') or warning.get('message')}")

    prompt_sync = summary.get("sync_prompt_files") or {}
    if prompt_sync:
        lines.append("")
        lines.append("## Prompt snapshots")
        lines.append("")
        lines.append(f"Sync requested: `{prompt_sync.get('sync_requested')}`")
        lines.append("")
        lines.append("| Phase | Status | Managed | Action | Prompt file |")
        lines.append("|---|---:|---:|---:|---|")
        for item in prompt_sync.get("prompts", []):
            if item.get("prompt_file") is None:
                continue
            lines.append(
                f"| {item.get('phase')} | {item.get('status')} | {item.get('managed_snapshot')} | "
                f"{item.get('action')} | `{item.get('prompt_file')}` |"
            )
        if prompt_sync.get("warnings"):
            lines.append("")
            lines.append("Prompt sync warnings:")
            for warning in prompt_sync.get("warnings", []):
                lines.append(
                    f"- `{warning.get('code')}` for `{warning.get('phase')}`: "
                    f"{warning.get('message')}"
                )
    ui_static = summary.get("ui_static") or {}
    if ui_static:
        lines.append("")
        lines.append("## UI static checks")
        lines.append("")
        lines.append(f"Status: `{ui_static.get('status')}`")
        lines.append(f"Warnings: `{len(ui_static.get('warnings', []))}`")
        lines.append(f"Blockers: `{len(ui_static.get('blockers', []))}`")
        for warning in ui_static.get("warnings", [])[:10]:
            lines.append(f"- `{warning.get('path')}`: {warning.get('message')} ({warning.get('code')})")
        for blocker in ui_static.get("blockers", [])[:10]:
            lines.append(f"- BLOCKER `{blocker.get('path')}`: {blocker.get('message')} ({blocker.get('code')})")

    workspace_restore = validation.get("workspace_restore") or {}
    if isinstance(workspace_restore, dict) and workspace_restore.get("enabled"):
        lines.append("")
        lines.append("## Validation workspace restore")
        lines.append("")
        lines.append(f"Tracked semantic files: `{workspace_restore.get('tracked_files', 0)}`")
        lines.append(f"Restored after validation: `{len(workspace_restore.get('restored_files') or [])}`")
        restore_errors = workspace_restore.get("errors") or []
        if restore_errors:
            lines.append(f"Restore errors: `{len(restore_errors)}`")

    tool_failures = [
        (result.get("phase"), failure)
        for result in summary.get("opencode_results", [])
        for failure in result.get("tool_failures", []) or []
    ]
    if tool_failures:
        lines.append("")
        lines.append("OpenCode tool failures:")
        for phase, failure in tool_failures:
            lines.append(f"- `{phase}`: {failure.get('message')}")

    missing_phase_outputs = [
        (result.get("phase"), name)
        for result in summary.get("opencode_results", [])
        for name in result.get("missing_expected_outputs", []) or []
    ]
    if missing_phase_outputs:
        lines.append("")
        lines.append("OpenCode missing phase outputs:")
        for phase, name in missing_phase_outputs:
            lines.append(f"- `{phase}`: `{name}` was not written under `workspace/prototype/output`")

    workspace_violations = [
        (result.get("phase"), violation)
        for result in summary.get("opencode_results", [])
        for violation in result.get("workspace_access_violations", []) or []
    ]
    if workspace_violations:
        lines.append("")
        lines.append("Workspace access warnings:")
        for phase, violation in workspace_violations[:20]:
            lines.append(f"- `{phase}`: `{violation.get('path')}` — {violation.get('reason')}")

    if summary.get("traceability_incomplete"):
        lines.append("")
        lines.append("Traceability coverage gaps:")
        for item in summary.get("traceability_incomplete", []):
            lines.append(f"- `{item.get('requirement_id')}`: {item.get('status')}")
    if changed.get("non_semantic_changes"):
        lines.append("")
        lines.append("Runtime/non-semantic changes:")
        for item in changed.get("non_semantic_changes", []):
            lines.append(f"- `{item.get('path')}`: {item.get('reason')} ({item.get('policy')})")
    lines.append("")
    (run / "output" / "run_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
