from __future__ import annotations

import argparse
import shutil
import time
from pathlib import Path
from common import run_cmd, write_json


TAIL_LINES = 80


def _tail(text: str, *, limit: int = TAIL_LINES) -> str:
    lines = text.splitlines()
    if len(lines) <= limit:
        return "\n".join(lines)
    return "\n".join([f"... truncated to last {limit} lines ...", *lines[-limit:]])


def _detect_environment_issue(stdout: str, stderr: str, *, workspace: Path) -> dict | None:
    combined = f"{stdout}\n{stderr}"
    frontend = workspace / "frontend"

    if "libasound.so.2" in combined:
        return {
            "code": "playwright_missing_system_dependency",
            "tool": "playwright",
            "message": "Playwright Chromium could not start because the host is missing libasound.so.2.",
            "missing_dependency": "libasound.so.2",
            "suggested_commands": [
                f"cd {frontend} && npx playwright install --with-deps chromium",
                "sudo apt-get update && sudo apt-get install -y libasound2",
            ],
        }

    if "Host system is missing dependencies to run browsers" in combined:
        return {
            "code": "playwright_missing_system_dependencies",
            "tool": "playwright",
            "message": "Playwright reported missing host system dependencies for browser execution.",
            "suggested_commands": [
                f"cd {frontend} && npx playwright install --with-deps chromium",
            ],
        }

    if "Executable doesn't exist" in combined and "playwright" in combined.lower():
        return {
            "code": "playwright_browser_not_installed",
            "tool": "playwright",
            "message": "Playwright browser binaries are not installed for this environment.",
            "suggested_commands": [
                f"cd {frontend} && npx playwright install chromium",
            ],
        }

    return None


def _print_failure_summary(status: str, stdout: str, stderr: str, environment_issue: dict | None) -> None:
    print(f"Validation {status}")
    if environment_issue:
        print("Validation environment issue:")
        print(f"  {environment_issue.get('message')}")
        commands = environment_issue.get("suggested_commands") or []
        if commands:
            print("Suggested setup commands:")
            for command in commands:
                print(f"  {command}")

    if stdout.strip():
        print("----- VALIDATION STDOUT (tail) -----")
        print(_tail(stdout))
    if stderr.strip():
        print("----- VALIDATION STDERR (tail) -----")
        print(_tail(stderr))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--task", default="validate")
    args = parser.parse_args()

    workspace = args.run / "workspace"
    log_dir = args.run / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    if shutil.which("task") is None:
        write_json(args.run / "output" / "validation_result.json", {
            "status": "skipped",
            "reason": "Taskfile runner not found in PATH",
            "manual_command": f"cd {workspace} && task {args.task}",
        })
        print("Task runner not found. Wrote output/validation_result.json")
        return

    started = time.time()
    result = run_cmd(["task", args.task], cwd=workspace)
    duration = time.time() - started
    stdout_log = log_dir / "validation.stdout.log"
    stderr_log = log_dir / "validation.stderr.log"
    stdout_log.write_text(result.stdout, encoding="utf-8")
    stderr_log.write_text(result.stderr, encoding="utf-8")

    environment_issue = None
    if result.returncode != 0:
        environment_issue = _detect_environment_issue(result.stdout, result.stderr, workspace=workspace)

    if result.returncode == 0:
        status = "passed"
    elif environment_issue:
        status = "environment_failed"
    else:
        status = "failed"

    data = {
        "status": status,
        "task": args.task,
        "exit_code": result.returncode,
        "duration_seconds": round(duration, 3),
        "stdout_log": str(stdout_log),
        "stderr_log": str(stderr_log),
    }
    if environment_issue:
        data["environment_issue"] = environment_issue

    write_json(args.run / "output" / "validation_result.json", data)
    # Also copy into workspace for OpenCode repair agent. Keep log copies next
    # to validation_result.json so repair prompts can read them via workspace
    # relative paths without searching sibling run directories.
    workspace_output = workspace / "prototype" / "output"
    workspace_output.mkdir(parents=True, exist_ok=True)
    workspace_stdout_log = workspace_output / "validation.stdout.log"
    workspace_stderr_log = workspace_output / "validation.stderr.log"
    workspace_stdout_log.write_text(result.stdout, encoding="utf-8")
    workspace_stderr_log.write_text(result.stderr, encoding="utf-8")
    workspace_data = dict(data)
    workspace_data["stdout_log"] = "prototype/output/validation.stdout.log"
    workspace_data["stderr_log"] = "prototype/output/validation.stderr.log"
    write_json(workspace_output / "validation_result.json", workspace_data)

    if status == "passed":
        print("Validation passed")
    else:
        _print_failure_summary(status, result.stdout, result.stderr, environment_issue)


if __name__ == "__main__":
    main()
