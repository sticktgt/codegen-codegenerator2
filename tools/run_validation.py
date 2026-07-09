from __future__ import annotations

import argparse
import shutil
import time
from pathlib import Path
from typing import Any

from common import write_json
from validation_runner.reporting import detect_environment_issue, print_failure_summary
from validation_runner.stages import (
    downstream_failed_stages,
    root_failed_stages,
    run_legacy_task,
    run_staged_validate,
)
from validation_runner.workspace import (
    merge_restore_results,
    restore_workspace_files,
    semantic_changed_files,
    snapshot_workspace_files,
)


def _write_workspace_result(run: Path, workspace: Path, data: dict[str, Any], stdout: str, stderr: str) -> None:
    workspace_output = workspace / "prototype" / "output"
    workspace_output.mkdir(parents=True, exist_ok=True)
    workspace_stdout_log = workspace_output / "validation.stdout.log"
    workspace_stderr_log = workspace_output / "validation.stderr.log"
    workspace_stdout_log.write_text(stdout, encoding="utf-8")
    workspace_stderr_log.write_text(stderr, encoding="utf-8")

    workspace_data = dict(data)
    workspace_data["stdout_log"] = "prototype/output/validation.stdout.log"
    workspace_data["stderr_log"] = "prototype/output/validation.stderr.log"
    write_json(workspace_output / "validation_result.json", workspace_data)


def _write_results(
    run: Path,
    workspace: Path,
    task: str,
    validation_mode: str,
    exit_code: int,
    duration_seconds: float,
    stdout: str,
    stderr: str,
    stages: list[dict[str, Any]],
    workspace_restore: dict[str, object],
) -> str:
    log_dir = run / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout_log = log_dir / "validation.stdout.log"
    stderr_log = log_dir / "validation.stderr.log"
    stdout_log.write_text(stdout, encoding="utf-8")
    stderr_log.write_text(stderr, encoding="utf-8")

    environment_issue = None
    if exit_code != 0:
        environment_issue = detect_environment_issue(stdout, stderr, workspace=workspace)

    if exit_code == 0:
        status = "passed"
    elif environment_issue:
        status = "environment_failed"
    else:
        status = "failed"

    data: dict[str, Any] = {
        "status": status,
        "task": task,
        "validation_mode": validation_mode,
        "exit_code": exit_code,
        "duration_seconds": round(duration_seconds, 3),
        "stdout_log": str(stdout_log),
        "stderr_log": str(stderr_log),
        "stages": stages,
        "failed_stages": [stage for stage in stages if stage.get("status") == "failed"],
        "root_failed_stages": root_failed_stages(stages),
        "downstream_failed_stages": downstream_failed_stages(stages),
    }
    if environment_issue:
        data["environment_issue"] = environment_issue
    if workspace_restore.get("enabled"):
        data["workspace_restore"] = workspace_restore

    write_json(run / "output" / "validation_result.json", data)
    _write_workspace_result(run, workspace, data, stdout, stderr)

    if status == "passed":
        print("Validation passed")
    else:
        print_failure_summary(status, stdout, stderr, environment_issue, stages)
    return status


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--task", default="validate")
    args = parser.parse_args()

    workspace = args.run / "workspace"
    if shutil.which("task") is None:
        write_json(args.run / "output" / "validation_result.json", {
            "status": "skipped",
            "reason": "Taskfile runner not found in PATH",
            "manual_command": f"cd {workspace} && task {args.task}",
        })
        print("Task runner not found. Wrote output/validation_result.json")
        return

    validation_snapshot = snapshot_workspace_files(workspace, semantic_changed_files(args.run))
    started = time.time()
    if args.task == "validate":
        exit_code, stdout, stderr, stages, stage_restore_results = run_staged_validate(workspace, validation_snapshot)
        validation_mode = "staged"
    else:
        exit_code, stdout, stderr, stages, stage_restore_results = run_legacy_task(workspace, args.task)
        validation_mode = "single_task"
    duration = time.time() - started

    final_restore = restore_workspace_files(workspace, validation_snapshot)
    workspace_restore = merge_restore_results([*stage_restore_results, final_restore])
    _write_results(
        args.run,
        workspace,
        args.task,
        validation_mode,
        exit_code,
        duration,
        stdout,
        stderr,
        stages,
        workspace_restore,
    )


if __name__ == "__main__":
    main()
