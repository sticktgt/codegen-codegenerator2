from __future__ import annotations

import subprocess
from pathlib import Path

from prototype_pipeline.events import PipelineLogger


SYNCED_KIT_INPUTS = [
    "prototype/input/kit.yaml",
    "prototype/input/generation-rules.yaml",
    "prototype/input/architecture-contract.yaml",
    "prototype/input/instructions",
]

SYNCED_KIT_RUNTIME = [
    "AGENTS.md",
    "opencode.json",
    "Taskfile.yml",
    "agents",
    "instructions",
    "examples",
    "prompts",
    ".opencode",
]

PLAN_INPUTS = [
    "prototype/input/file_plan.json",
    "prototype/input/validation_plan.json",
]


def commit_workspace_files(run: Path, logger: PipelineLogger, rel_paths: list[str], message: str, log_message: str) -> None:
    workspace = run / "workspace"
    if not (workspace / ".git").exists():
        return
    paths = [rel for rel in rel_paths if (workspace / rel).exists()]
    if not paths:
        return
    subprocess.run(["git", "add", *paths], cwd=workspace)
    status = subprocess.run(
        ["git", "status", "--porcelain", *paths],
        cwd=workspace,
        text=True,
        stdout=subprocess.PIPE,
    )
    if status.stdout.strip():
        logger.log(log_message)
        subprocess.run(["git", "commit", "-m", message], cwd=workspace)


def commit_synced_kit_inputs(run: Path, logger: PipelineLogger) -> None:
    """Make kit-level input sync part of the clean baseline.

    Existing runs can be older than the current kit and receive files such as
    architecture-contract.yaml or the instruction compatibility mirror via
    sync_run_inputs.py. If those files remain untracked, collect_changes treats
    them as implementation drift and repair may even delete them.
    """
    workspace = run / "workspace"
    commit_workspace_files(
        run=run,
        logger=logger,
        rel_paths=SYNCED_KIT_INPUTS + SYNCED_KIT_RUNTIME,
        message="synced kit input artifacts",
        log_message="Committing synced kit input artifacts to the workspace baseline",
    )


def commit_plan_inputs(run: Path, logger: PipelineLogger) -> None:
    commit_workspace_files(
        run=run,
        logger=logger,
        rel_paths=PLAN_INPUTS,
        message="approved plan input artifacts",
        log_message="Committing approved plan input artifacts to the workspace baseline",
    )
