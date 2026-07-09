from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from common import run_cmd
from validation_runner.reporting import format_stage_block
from validation_runner.workspace import restore_workspace_files

VALIDATE_STAGES = ["install", "smoke", "test", "build", "frontend-behavior"]
STAGE_DEPENDENCIES = {
    "install": [],
    "smoke": ["install"],
    "test": ["install", "smoke"],
    "build": ["install"],
    "frontend-behavior": ["install", "smoke", "test", "build"],
}


def annotate_stage_dependencies(stages: list[dict[str, Any]]) -> None:
    """Mark downstream stages whose diagnostics may be consequences of earlier failures."""

    status_by_name = {str(stage.get("name")): str(stage.get("status")) for stage in stages}
    for stage in stages:
        name = str(stage.get("name"))
        deps = STAGE_DEPENDENCIES.get(name, [])
        failed_dependencies = [dep for dep in deps if status_by_name.get(dep) == "failed"]
        stage["depends_on"] = deps
        stage["blocked_by_failed_stages"] = failed_dependencies
        if failed_dependencies:
            stage["diagnostic_reliability"] = "possibly_downstream"
            stage["repair_priority"] = "secondary_context"
        else:
            stage["diagnostic_reliability"] = "root_or_independent"
            stage["repair_priority"] = "primary"


def root_failed_stages(stages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        stage for stage in stages
        if stage.get("status") == "failed" and not stage.get("blocked_by_failed_stages")
    ]


def downstream_failed_stages(stages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        stage for stage in stages
        if stage.get("status") == "failed" and stage.get("blocked_by_failed_stages")
    ]


def run_single_task(workspace: Path, task: str) -> tuple[dict[str, Any], str, str]:
    started = time.time()
    result = run_cmd(["task", task], cwd=workspace)
    duration = time.time() - started
    status = "passed" if result.returncode == 0 else "failed"
    stage = {
        "name": task,
        "status": status,
        "exit_code": result.returncode,
        "duration_seconds": round(duration, 3),
    }
    return stage, result.stdout, result.stderr


def run_legacy_task(workspace: Path, task: str) -> tuple[int, str, str, list[dict[str, Any]], list[dict[str, object]]]:
    stage, stdout, stderr = run_single_task(workspace, task)
    stages = [stage]
    annotate_stage_dependencies(stages)
    return int(stage["exit_code"] or 0), stdout, stderr, stages, []


def run_staged_validate(
    workspace: Path,
    snapshot: dict[str, dict[str, object]],
) -> tuple[int, str, str, list[dict[str, Any]], list[dict[str, object]]]:
    stdout_parts: list[str] = []
    stderr_parts: list[str] = []
    stages: list[dict[str, Any]] = []
    restore_results: list[dict[str, object]] = []
    first_failure = 0
    install_failed = False

    for task in VALIDATE_STAGES:
        if install_failed:
            stage = {
                "name": task,
                "status": "skipped",
                "exit_code": None,
                "duration_seconds": 0,
                "reason": "install_failed",
            }
            stages.append(stage)
            block = format_stage_block(task, "skipped", None, 0, "Skipped because install failed.")
            stdout_parts.append(block)
            stderr_parts.append(block)
            continue

        stage, stdout, stderr = run_single_task(workspace, task)
        stages.append(stage)
        stdout_parts.append(format_stage_block(
            task,
            str(stage["status"]),
            int(stage["exit_code"]),
            float(stage["duration_seconds"]),
            stdout,
        ))
        stderr_parts.append(format_stage_block(
            task,
            str(stage["status"]),
            int(stage["exit_code"]),
            float(stage["duration_seconds"]),
            stderr,
        ))

        if stage["status"] == "failed" and first_failure == 0:
            first_failure = int(stage["exit_code"] or 1)
        if task == "install" and stage["status"] == "failed":
            install_failed = True

        # Keep validation stages isolated from each other. Backend pytest and
        # browser tests often mutate JSON mock storage; later stages should see
        # the implementation as generated, not the previous stage's runtime data.
        restore_results.append(restore_workspace_files(workspace, snapshot))

    annotate_stage_dependencies(stages)
    return first_failure, "\n".join(stdout_parts), "\n".join(stderr_parts), stages, restore_results
