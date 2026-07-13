from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from common import write_json
from usage_metrics import collect_stats, write_usage_delta


def _safe_phase(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in value).strip("-") or "opencode"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _log(message: str) -> None:
    print(f"[{_utc_now()}] {message}", flush=True)


def _stream_pipe(
    pipe,
    log_file: Path,
    label: str,
    *,
    stream: bool,
    interactive_guard_event: threading.Event | None = None,
    diagnostic_guard_event: threading.Event | None = None,
    diagnostic_guard: DiagnosticCommandGuard | None = None,
) -> None:
    with log_file.open("w", encoding="utf-8") as out:
        for line in iter(pipe.readline, ""):
            out.write(line)
            out.flush()
            if interactive_guard_event is not None and INTERACTIVE_PLAYWRIGHT_COMMAND_RE.search(line):
                interactive_guard_event.set()
                guard_line = (
                    "[pipeline-guard] blocked interactive Playwright diagnostic command; "
                    "the OpenCode phase will hand control back to the pipeline for post-repair validation.\n"
                )
                out.write(guard_line)
                out.flush()
                if stream:
                    sys.stdout.write(f"[{_utc_now()}] {label} | {guard_line}")
                    sys.stdout.flush()
            if diagnostic_guard_event is not None and diagnostic_guard is not None:
                budget_message = diagnostic_guard.record_line(line)
                if budget_message:
                    diagnostic_guard_event.set()
                    guard_line = f"[pipeline-guard] {budget_message}\n"
                    out.write(guard_line)
                    out.flush()
                    if stream:
                        sys.stdout.write(f"[{_utc_now()}] {label} | {guard_line}")
                        sys.stdout.flush()
            if stream:
                sys.stdout.write(f"[{_utc_now()}] {label} | {line}")
                sys.stdout.flush()
    pipe.close()


TOOL_FAILURE_PATTERNS = [
    re.compile(r"permission requested: .*auto-rejecting", re.IGNORECASE),
    re.compile(r"The user rejected permission", re.IGNORECASE),
    re.compile(r"^.*✗\s+(Edit|Write)\s+.*\sfailed.*$", re.IGNORECASE),
]


def _detect_failed_tool_calls(*log_paths: Path) -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for path in log_paths:
        if not path.exists():
            continue
        for index, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
            if any(pattern.search(line) for pattern in TOOL_FAILURE_PATTERNS):
                key = (str(path), line.strip())
                if key in seen:
                    continue
                seen.add(key)
                failures.append({
                    "log": str(path),
                    "line_number": str(index),
                    "message": line.strip(),
                })
    return failures



ABS_PATH_RE = re.compile(r"/[^\s`'\"|)]+")


def _detect_workspace_access_violations(workspace: Path, project_root: Path, run: Path, *log_paths: Path) -> list[dict[str, str]]:
    """Detect reads/globs of project files outside the active workspace.

    This is a log-level guard, not a sandbox. It catches accidental access to
    sibling runs, samples, root prototype/output, .venv, node_modules, etc.
    """
    workspace = workspace.resolve()
    project_root = project_root.resolve()
    run = run.resolve()
    ignored_inside_workspace = (
        workspace / ".git",
        workspace / ".venv",
        workspace / "frontend" / "node_modules",
        workspace / "frontend" / "dist",
        workspace / "dist",
    )
    violations: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()

    def classify(path: Path) -> str | None:
        try:
            resolved = path.resolve(strict=False)
        except Exception:
            resolved = path
        try:
            resolved.relative_to(workspace)
            for ignored in ignored_inside_workspace:
                try:
                    resolved.relative_to(ignored)
                    return "workspace_runtime_directory"
                except ValueError:
                    pass
            return None
        except ValueError:
            pass
        # Validation logs and run-level output are intentionally outside the workspace,
        # but repair should normally read the copies under prototype/output.
        for allowed in (run / "logs", run / "output", run / "usage"):
            try:
                resolved.relative_to(allowed.resolve(strict=False))
                return "run_artifact_outside_workspace"
            except ValueError:
                pass
        try:
            resolved.relative_to(project_root)
        except ValueError:
            return None
        return "project_file_outside_workspace"

    for log_path in log_paths:
        if not log_path.exists():
            continue
        for index, line in enumerate(log_path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
            if not any(token in line for token in ("→ Read", "✱ Glob", "find ", "cat ", "ls ")):
                continue
            for match in ABS_PATH_RE.finditer(line):
                raw = match.group(0).rstrip(".,:;]")
                path = Path(raw)
                reason = classify(path)
                if not reason:
                    continue
                key = (str(log_path), str(index), raw)
                if key in seen:
                    continue
                seen.add(key)
                violations.append({
                    "log": str(log_path),
                    "line_number": str(index),
                    "path": raw,
                    "reason": reason,
                    "message": line.strip(),
                })
    return violations



INTERACTIVE_PLAYWRIGHT_ARGS = {"--debug", "--ui", "--headed", "show-trace", "codegen"}
INTERACTIVE_PLAYWRIGHT_COMMAND_RE = re.compile(
    r"\$\s+.*(?:npx\s+playwright|npm\s+run\s+[^&|;]*playwright|playwright)\b.*(?:--debug|--ui|--headed|show-trace|codegen)",
    re.IGNORECASE,
)

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")
DIAGNOSTIC_COMMAND_PATTERNS = {
    "frontend_e2e": re.compile(r"\$\s+.*(?:npm\s+run\s+test:e2e|npx\s+playwright\s+test|\bplaywright\s+test\b)", re.IGNORECASE),
    "backend_pytest": re.compile(r"\$\s+.*\bpytest\b", re.IGNORECASE),
}
DEFAULT_REPAIR_DIAGNOSTIC_COMMAND_LIMITS = {
    # Repair should use existing pipeline diagnostics and make a targeted fix.
    # The official post-repair validation runs immediately after the phase, so
    # repeated full e2e/pytest cycles inside OpenCode mostly add time and can
    # lead to local, overfit test rewrites.
    "frontend_e2e": 2,
    "backend_pytest": 3,
}


class DiagnosticCommandGuard:
    def __init__(self, limits: dict[str, int]):
        self.limits = limits
        self.counts = {name: 0 for name in limits}
        self.violations: list[dict[str, str]] = []
        self._triggered = False
        self._lock = threading.Lock()

    def record_line(self, line: str) -> str | None:
        plain = ANSI_ESCAPE_RE.sub("", line).strip()
        if not plain.startswith("$"):
            return None
        with self._lock:
            for kind, pattern in DIAGNOSTIC_COMMAND_PATTERNS.items():
                if kind not in self.limits or not pattern.search(plain):
                    continue
                self.counts[kind] += 1
                if self.counts[kind] <= self.limits[kind] or self._triggered:
                    return None
                self._triggered = True
                message = (
                    f"diagnostic command budget exceeded for {kind}: "
                    f"{self.counts[kind]} > {self.limits[kind]}; "
                    "the OpenCode phase will hand control back to the pipeline and official post-phase validation should decide the result."
                )
                self.violations.append({
                    "kind": kind,
                    "count": str(self.counts[kind]),
                    "limit": str(self.limits[kind]),
                    "command": plain,
                    "message": message,
                })
                return message
        return None

    @property
    def triggered(self) -> bool:
        with self._lock:
            return self._triggered


def _prepare_opencode_tool_shims(workspace: Path) -> Path:
    """Create workspace-local wrappers that block interactive Playwright diagnostics.

    OpenCode occasionally tries `npx playwright test --debug` or
    `npx playwright show-trace` during repair. Those commands open browser
    windows / inspectors and can hang an automated pipeline. The wrappers are
    intentionally workspace-local and ignored by git, so they do not affect the
    generated prototype boundary.
    """
    shim_dir = workspace / ".opencode-shims"
    shim_dir.mkdir(parents=True, exist_ok=True)
    shim_template = """#!/usr/bin/env bash
set -euo pipefail
for arg in "$@"; do
  case "$arg" in
    --debug|--ui|--headed|show-trace|codegen)
      echo "Blocked interactive Playwright diagnostic argument: $arg" >&2
      echo "Use non-interactive diagnostics only; the pipeline runs official validation after the phase." >&2
      exit 65
      ;;
  esac
done
exec "__REAL_TOOL__" "$@"
"""
    for tool_name in ("npm", "npx", "playwright"):
        real_tool = shutil.which(tool_name)
        if not real_tool:
            continue
        shim = shim_dir / tool_name
        shim.write_text(shim_template.replace("__REAL_TOOL__", real_tool), encoding="utf-8")
        shim.chmod(0o755)
    return shim_dir


def _run_opencode_streamed(
    prompt: str,
    *,
    cwd: Path,
    run: Path,
    project_root: Path,
    stdout_log: Path,
    stderr_log: Path,
    stream: bool,
    model: str | None = None,
    diagnostic_command_limits: dict[str, int] | None = None,
) -> tuple[int, bool, bool, list[dict[str, str]]]:
    cwd = cwd.resolve()
    run = run.resolve()
    project_root = project_root.resolve()
    prompt_prefix = (
        f"Current workspace root: {cwd}\n"
        f"Current run directory: {run}\n"
        "Use the workspace root as the ONLY project root for source reads and writes.\n"
        "Use relative paths from the workspace whenever possible.\n"
        f"Valid prototype input directory: {cwd / 'prototype' / 'input'}\n"
        f"Valid prototype output directory: {cwd / 'prototype' / 'output'}\n"
        f"Valid instruction directory: {cwd / 'instructions'}\n"
        f"Invalid path pattern: {run / 'prototype'} (do not read or write this path; it is not the workspace).\n"
        f"Invalid path pattern: {project_root / 'prototype'} (root scratch area; do not use it as current run input/output).\n"
        f"Invalid path pattern: {project_root / 'instructions'} (repository-root instructions are not current run instructions).\n"
        f"Invalid path pattern: {project_root / 'prototype-kits'} (source kit copies are not current run workspace context).\n"
        "Do not construct absolute paths by dropping '/workspace' from the workspace root.\n"
        "If a relative read accidentally resolves outside the workspace, retry with a path under the Current workspace root.\n"
        "Do not use sibling runs, baselines, samples, .venv, node_modules, build output, or source kit files as sources for the current run.\n"
        "Use prototype/input/architecture-contract.yaml for architecture rules when it exists.\n"
        "Do not run interactive Playwright diagnostics such as --debug, --ui, --headed, codegen, or show-trace.\n\n"
    )
    command = ["opencode", "run"]
    if model:
        command.extend(["--model", model])
    command.append(prompt_prefix + prompt)
    env = os.environ.copy()
    env.setdefault("CI", "1")
    env["PWDEBUG"] = "0"
    env.setdefault("PLAYWRIGHT_HEADLESS", "1")
    shim_dir = _prepare_opencode_tool_shims(cwd)
    env["PATH"] = f"{shim_dir}{os.pathsep}{env.get('PATH', '')}"
    process = subprocess.Popen(
        command,
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
        env=env,
    )
    assert process.stdout is not None
    assert process.stderr is not None
    interactive_guard_event = threading.Event()
    diagnostic_guard_event = threading.Event()
    diagnostic_guard = DiagnosticCommandGuard(diagnostic_command_limits) if diagnostic_command_limits else None
    stdout_thread = threading.Thread(
        target=_stream_pipe,
        args=(process.stdout, stdout_log, "opencode:stdout"),
        kwargs={
            "stream": stream,
            "interactive_guard_event": interactive_guard_event,
            "diagnostic_guard_event": diagnostic_guard_event,
            "diagnostic_guard": diagnostic_guard,
        },
    )
    stderr_thread = threading.Thread(
        target=_stream_pipe,
        args=(process.stderr, stderr_log, "opencode:stderr"),
        kwargs={
            "stream": stream,
            "interactive_guard_event": interactive_guard_event,
            "diagnostic_guard_event": diagnostic_guard_event,
            "diagnostic_guard": diagnostic_guard,
        },
    )
    stdout_thread.start()
    stderr_thread.start()
    while process.poll() is None:
        if interactive_guard_event.is_set() or diagnostic_guard_event.is_set():
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            break
        time.sleep(0.1)
    returncode = process.wait()
    stdout_thread.join()
    stderr_thread.join()
    return returncode, interactive_guard_event.is_set(), diagnostic_guard_event.is_set(), (diagnostic_guard.violations if diagnostic_guard else [])



EXPECTED_PHASE_OUTPUTS = {
    "plan": ["plan_proposal.json", "validation_plan_proposal.json"],
    "plan-review": ["plan_review.json"],
    "implementation": ["implementation_report.json", "change_manifest.json"],
}


def _expected_outputs_for_phase(phase: str) -> list[str]:
    if phase.startswith("repair-"):
        return ["repair_report.json"]
    return EXPECTED_PHASE_OUTPUTS.get(phase, [])


def _missing_expected_outputs(workspace: Path, phase: str) -> list[str]:
    output = workspace / "prototype" / "output"
    return [name for name in _expected_outputs_for_phase(phase) if not (output / name).exists()]


def _workspace_has_git_changes(workspace: Path) -> bool:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(workspace),
            text=True,
            capture_output=True,
            check=False,
        )
    except Exception:
        return False
    return bool(result.stdout.strip())


def _write_fallback_repair_report(workspace: Path, phase: str, stdout_log: Path, stderr_log: Path) -> None:
    report_path = workspace / "prototype" / "output" / "repair_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(report_path, {
        "status": "fallback_generated_by_pipeline",
        "phase": phase,
        "summary": (
            "OpenCode exited without writing repair_report.json. "
            "The pipeline generated this fallback report because the repair phase left workspace changes; "
            "post-repair boundary checks and validation remain the source of truth."
        ),
        "changed_files": [],
        "notes": [
            "This fallback report is not an agent-authored repair summary.",
            "Inspect changed_files.json, validation_result.json, and the OpenCode logs for detailed repair context.",
        ],
        "source_logs": {
            "stdout_log": str(stdout_log),
            "stderr_log": str(stderr_log),
        },
    })

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--phase", required=True, help="plan, plan-review, implementation, repair-001, ...")
    parser.add_argument("--prompt-file", type=Path)
    parser.add_argument("--prompt")
    parser.add_argument("--stats-days", type=int, default=1)
    parser.add_argument("--stats-models", type=int, default=10)
    parser.add_argument("--no-stream", action="store_true", help="Do not mirror OpenCode stdout/stderr to the pipeline console")
    parser.add_argument("--model", help="Explicit OpenCode model, e.g. ollama-cloud/qwen3-coder-next")
    parser.add_argument("--fail-on-workspace-leak", action="store_true", help="Fail the phase if OpenCode reads/globs project files outside the active workspace")
    args = parser.parse_args()

    phase = _safe_phase(args.phase)
    if args.prompt_file:
        prompt = args.prompt_file.read_text(encoding="utf-8")
    elif args.prompt:
        prompt = args.prompt
    else:
        raise SystemExit("Provide --prompt-file or --prompt")

    workspace = args.run / "workspace"
    log_dir = args.run / "logs"
    output_dir = args.run / "output"
    usage_dir = args.run / "usage"
    log_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    usage_dir.mkdir(parents=True, exist_ok=True)

    started_at = _utc_now()
    _log(f"OpenCode phase '{phase}' starting")
    _, usage_before = collect_stats(days=args.stats_days, models=args.stats_models)

    stdout_log = log_dir / f"opencode.{phase}.stdout.log"
    stderr_log = log_dir / f"opencode.{phase}.stderr.log"

    if shutil.which("opencode") is None:
        _, usage_after = collect_stats(days=args.stats_days, models=args.stats_models)
        delta_path = write_usage_delta(args.run, phase, usage_before, usage_after, duration_seconds=0)
        write_json(output_dir / f"opencode_{phase}_result.json", {
            "status": "skipped",
            "phase": phase,
            "reason": "opencode CLI not found in PATH",
            "started_at": started_at,
            "ended_at": _utc_now(),
            "duration_seconds": 0,
            "manual_command": f"cd {workspace} && opencode run {'--model ' + args.model + ' ' if args.model else ''}{prompt!r}",
            "model": args.model,
            "usage_delta": f"usage/{phase}.delta.json",
        })
        _log(f"OpenCode phase '{phase}' skipped: CLI not found")
        return

    started = time.time()
    project_root = Path(__file__).resolve().parents[1]
    returncode, interactive_guard_triggered, diagnostic_command_guard_triggered, diagnostic_command_violations = _run_opencode_streamed(
        prompt,
        cwd=workspace,
        run=args.run,
        project_root=project_root,
        stdout_log=stdout_log,
        stderr_log=stderr_log,
        stream=not args.no_stream,
        model=args.model,
        diagnostic_command_limits=DEFAULT_REPAIR_DIAGNOSTIC_COMMAND_LIMITS if phase.startswith("repair-") else None,
    )
    duration = time.time() - started
    ended_at = _utc_now()

    _, usage_after = collect_stats(days=args.stats_days, models=args.stats_models)
    delta_path = write_usage_delta(args.run, phase, usage_before, usage_after, duration_seconds=duration, requested_model=args.model)

    tool_failures = _detect_failed_tool_calls(stdout_log, stderr_log)
    workspace_access_violations = _detect_workspace_access_violations(workspace, project_root, args.run, stdout_log, stderr_log)
    hard_workspace_violations = [item for item in workspace_access_violations if item.get("reason") == "project_file_outside_workspace"]
    has_workspace_changes = _workspace_has_git_changes(workspace)
    handoff_guard_triggered = interactive_guard_triggered or diagnostic_command_guard_triggered
    completion_mode = "normal"
    if phase.startswith("repair-") and has_workspace_changes and handoff_guard_triggered:
        completion_mode = "guarded_handoff"
    returncode_ok = returncode == 0 or (
        phase.startswith("repair-")
        and has_workspace_changes
        and handoff_guard_triggered
    )
    tolerated_tool_failures: list[dict[str, str]] = []
    hard_tool_failures = tool_failures
    if phase.startswith("repair-") and returncode_ok and has_workspace_changes and tool_failures:
        # Repair is validated by the pipeline immediately after the phase.
        # Treat failed diagnostic/read/permission tool calls as warnings when
        # the agent produced workspace changes; post-repair boundary checks and
        # validation decide whether those changes are acceptable.
        tolerated_tool_failures = tool_failures
        hard_tool_failures = []
    missing_expected_outputs = _missing_expected_outputs(workspace, phase)
    auto_created_expected_outputs: list[str] = []
    if (
        phase.startswith("repair-")
        and returncode_ok
        and "repair_report.json" in missing_expected_outputs
        and has_workspace_changes
    ):
        _write_fallback_repair_report(workspace, phase, stdout_log, stderr_log)
        auto_created_expected_outputs.append("repair_report.json")
        missing_expected_outputs = _missing_expected_outputs(workspace, phase)

    status = "passed" if (
        returncode_ok
        and not hard_tool_failures
        and not missing_expected_outputs
        and not (args.fail_on_workspace_leak and hard_workspace_violations)
    ) else "failed"
    result_payload = {
        "status": status,
        "phase": phase,
        "returncode": returncode,
        "completion_mode": completion_mode,
        "handoff_to_pipeline": completion_mode == "guarded_handoff",
        "interactive_playwright_guard_triggered": interactive_guard_triggered,
        "diagnostic_command_guard_triggered": diagnostic_command_guard_triggered,
        "diagnostic_command_violations": diagnostic_command_violations,
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_seconds": round(duration, 3),
        "model": args.model,
        "stdout_log": str(stdout_log),
        "stderr_log": str(stderr_log),
        "usage_delta": str(delta_path.relative_to(args.run)),
        "tool_failures": hard_tool_failures,
        "tolerated_tool_failures": tolerated_tool_failures,
        "workspace_access_violations": workspace_access_violations,
        "missing_expected_outputs": missing_expected_outputs,
        "auto_created_expected_outputs": auto_created_expected_outputs,
    }
    failure_reasons = []
    if returncode != 0 and not returncode_ok:
        failure_reasons.append("opencode_returncode_nonzero")
    if hard_tool_failures:
        failure_reasons.append("failed_tool_calls_detected")
    if missing_expected_outputs:
        failure_reasons.append("missing_expected_phase_outputs")
    if args.fail_on_workspace_leak and hard_workspace_violations:
        failure_reasons.append("workspace_access_violation_detected")
    if failure_reasons:
        result_payload["failure_reason"] = ",".join(failure_reasons)
    write_json(output_dir / f"opencode_{phase}_result.json", result_payload)
    _log(f"OpenCode phase '{phase}' {status} in {duration:.1f}s")
    if hard_tool_failures:
        _log(f"OpenCode phase '{phase}' failed: detected {len(hard_tool_failures)} failed tool call(s)")
    if interactive_guard_triggered:
        _log(f"OpenCode phase '{phase}' handed off after an interactive Playwright diagnostic command")
    if diagnostic_command_guard_triggered:
        _log(f"OpenCode phase '{phase}' handed off after repeated expensive diagnostic command(s)")
    if completion_mode == "guarded_handoff":
        _log(f"OpenCode phase '{phase}' returned control to the pipeline; official post-repair checks remain authoritative")
    if tolerated_tool_failures:
        _log(f"OpenCode phase '{phase}' tolerated {len(tolerated_tool_failures)} failed diagnostic tool call(s); post-repair validation remains authoritative")
    if auto_created_expected_outputs:
        _log(f"OpenCode phase '{phase}' auto-created fallback output(s): {', '.join(auto_created_expected_outputs)}")
    if missing_expected_outputs:
        _log(f"OpenCode phase '{phase}' failed: missing expected workspace output(s): {', '.join(missing_expected_outputs)}")
    if workspace_access_violations:
        _log(f"OpenCode phase '{phase}' workspace access warnings: {len(workspace_access_violations)}")
    if status != "passed":
        raise SystemExit(returncode or 2)


if __name__ == "__main__":
    main()
