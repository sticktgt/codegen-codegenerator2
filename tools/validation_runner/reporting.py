from __future__ import annotations

from pathlib import Path
from typing import Any

TAIL_LINES = 80


def tail(text: str, *, limit: int = TAIL_LINES) -> str:
    lines = text.splitlines()
    if len(lines) <= limit:
        return "\n".join(lines)
    return "\n".join([f"... truncated to last {limit} lines ...", *lines[-limit:]])


def detect_environment_issue(stdout: str, stderr: str, *, workspace: Path) -> dict[str, Any] | None:
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
            "suggested_commands": [f"cd {frontend} && npx playwright install --with-deps chromium"],
        }

    if "Executable doesn't exist" in combined and "playwright" in combined.lower():
        return {
            "code": "playwright_browser_not_installed",
            "tool": "playwright",
            "message": "Playwright browser binaries are not installed for this environment.",
            "suggested_commands": [f"cd {frontend} && npx playwright install chromium"],
        }

    return None


def format_stage_block(name: str, status: str, exit_code: int | None, duration: float | None, text: str) -> str:
    header = f"===== VALIDATION STAGE: {name} ({status}"
    if exit_code is not None:
        header += f", exit_code={exit_code}"
    if duration is not None:
        header += f", duration={duration:.3f}s"
    header += ") ====="
    if text.strip():
        return f"{header}\n{text.rstrip()}\n"
    return f"{header}\n(no output)\n"


def print_failure_summary(
    status: str,
    stdout: str,
    stderr: str,
    environment_issue: dict[str, Any] | None,
    stages: list[dict[str, Any]] | None = None,
) -> None:
    print(f"Validation {status}")
    failed_stages = [stage for stage in stages or [] if stage.get("status") == "failed"]
    if failed_stages:
        print("Failed validation stages:")
        for stage in failed_stages:
            blocked_by = stage.get("blocked_by_failed_stages") or []
            suffix = f"; possibly downstream of {','.join(blocked_by)}" if blocked_by else ""
            print(f"  - {stage.get('name')}: exit_code={stage.get('exit_code')}{suffix}")
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
        print(tail(stdout))
    if stderr.strip():
        print("----- VALIDATION STDERR (tail) -----")
        print(tail(stderr))
