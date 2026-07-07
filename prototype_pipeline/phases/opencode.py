from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class OpenCodeOptions:
    run: Path
    model: str | None = None
    no_stream: bool = False
    fail_on_workspace_leak: bool = False


def phase_args(py: str, phase: str, prompt_file: Path, options: OpenCodeOptions) -> list[str]:
    result = [
        py,
        "tools/run_opencode_phase.py",
        "--run",
        str(options.run),
        "--phase",
        phase,
        "--prompt-file",
        str(prompt_file),
    ]
    if options.model:
        result.extend(["--model", options.model])
    if options.no_stream:
        result.append("--no-stream")
    if options.fail_on_workspace_leak:
        result.append("--fail-on-workspace-leak")
    return result
