from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from common import copytree_clean, run_cmd
from prepare_workspace import INPUT_FILES, OPTIONAL_INPUT_FILES

RUNTIME_DIRS = [
    ".git",
    ".venv",
    "node_modules",
    "frontend/node_modules",
    "dist",
    "frontend/dist",
    "backend/.pytest_cache",
    ".pytest_cache",
    "frontend/playwright-report",
    "frontend/test-results",
    "playwright-report",
    "test-results",
]

# Files owned by the kit validation/runtime harness. Overlay these from the
# current kit when preparing an incremental run, so baseline dependency fixes
# such as TestClient support are applied before the git baseline commit and do
# not appear as generated implementation changes.
KIT_BASELINE_OVERLAY_FILES = [
    "backend/requirements.txt",
    # Optional frontend/runtime harness files are baseline kit files.
    # They must be overlaid when switching an incremental run to a kit
    # variant that enables browser/e2e validation, otherwise package/config
    # changes would appear as generated implementation drift.
    "frontend/package.json",
    "frontend/vite.config.js",
    "frontend/playwright.config.js",
]


BASELINE_CONTEXT_FILES = [
    "run_summary.json",
    "scenario_result.json",
    "code_traceability.json",
    "changed_files.json",
    "change_manifest.json",
    "file_plan.json",
    "validation_plan.json",
    "validation_result.json",
    "ui_static_check_result.json",
]


def _remove_runtime(workspace: Path) -> None:
    for rel in RUNTIME_DIRS:
        path = workspace / rel
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
    for pycache in workspace.rglob("__pycache__"):
        shutil.rmtree(pycache, ignore_errors=True)
    for pyc in workspace.rglob("*.pyc"):
        pyc.unlink(missing_ok=True)


def _copy_kit_runtime(kit: Path, workspace: Path) -> None:
    for name in ["AGENTS.md", "opencode.json", "Taskfile.yml"]:
        src = kit / name
        if src.exists():
            shutil.copy2(src, workspace / name)
    for folder in ["agents", "instructions", "examples", "prompts"]:
        src = kit / folder
        if src.exists():
            dst = workspace / folder
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
    for rel in KIT_BASELINE_OVERLAY_FILES:
        src = kit / "template" / rel
        dst = workspace / rel
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def _copy_baseline_context(from_run: Path, input_dir: Path, workspace_input: Path) -> None:
    """Expose previous successful run outputs as read-only planning context.

    Incremental workspaces already contain the previous source tree, so OpenCode
    can inspect code directly. These artifacts add semantic context that is not
    always obvious from code alone: previous traceability, accepted file plans,
    change manifests, and validation summaries. Missing files are fine because
    older runs may not have produced every artifact.
    """
    candidates = [from_run / "output", from_run / "workspace" / "prototype" / "output"]
    copied: list[str] = []
    for source_dir in candidates:
        if not source_dir.exists():
            continue
        for name in BASELINE_CONTEXT_FILES:
            src = source_dir / name
            if not src.exists() or name in copied:
                continue
            for root in [input_dir, workspace_input]:
                dst = root / "baseline_context" / name
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            copied.append(name)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-run", required=True, type=Path, help="Successful previous run to use as baseline")
    parser.add_argument("--sample", required=True, type=Path, help="Input artifacts for the new slice")
    parser.add_argument("--run", required=True, type=Path, help="New run directory")
    parser.add_argument("--kit", required=True, type=Path)
    args = parser.parse_args()

    source_workspace = args.from_run / "workspace"
    if not source_workspace.exists():
        raise SystemExit(f"Source workspace does not exist: {source_workspace}")

    workspace = args.run / "workspace"
    input_dir = args.run / "input"
    output_dir = args.run / "output"
    log_dir = args.run / "logs"
    for folder in [input_dir, output_dir, log_dir, args.run / "dist", args.run / "usage", args.run / "agent_reports"]:
        folder.mkdir(parents=True, exist_ok=True)

    copytree_clean(source_workspace, workspace)
    _remove_runtime(workspace)
    _copy_kit_runtime(args.kit, workspace)

    workspace_input = workspace / "prototype" / "input"
    workspace_output = workspace / "prototype" / "output"
    if workspace_input.exists():
        shutil.rmtree(workspace_input)
    if workspace_output.exists():
        shutil.rmtree(workspace_output)
    workspace_input.mkdir(parents=True, exist_ok=True)
    workspace_output.mkdir(parents=True, exist_ok=True)
    (workspace_output / ".gitkeep").touch()

    shutil.copy2(args.kit / "generation-rules.yaml", workspace_input / "generation-rules.yaml")
    shutil.copy2(args.kit / "kit.yaml", workspace_input / "kit.yaml")
    contract = args.kit / "architecture-contract.yaml"
    if contract.exists():
        shutil.copy2(contract, workspace_input / "architecture-contract.yaml")
        shutil.copy2(contract, input_dir / "architecture-contract.yaml")
    for name in INPUT_FILES:
        shutil.copy2(args.sample / name, input_dir / name)
        shutil.copy2(args.sample / name, workspace_input / name)

    for name in OPTIONAL_INPUT_FILES:
        src = args.sample / name
        if src.exists():
            shutil.copy2(src, input_dir / name)
            shutil.copy2(src, workspace_input / name)

    _copy_baseline_context(args.from_run, input_dir, workspace_input)

    # Optional input artifacts prepared by a previous phase can be carried in.
    for name in ["file_plan.json", "validation_plan.json"]:
        src = input_dir / name
        if src.exists():
            shutil.copy2(src, workspace_input / name)

    run_cmd(["git", "init"], cwd=workspace)
    run_cmd(["git", "config", "user.email", "prototype@example.local"], cwd=workspace)
    run_cmd(["git", "config", "user.name", "Prototype Runner"], cwd=workspace)
    run_cmd(["git", "add", "."], cwd=workspace)
    run_cmd(["git", "commit", "-m", "baseline"], cwd=workspace)

    print(f"Incremental workspace prepared: {workspace}")


if __name__ == "__main__":
    main()
