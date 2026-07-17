from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from common import copytree_clean, run_cmd
from kit_runtime import copy_kit_runtime

INPUT_FILES = [
    "scheme_model.json",
    "requirements.json",
    "data_sources.json",
    "mock_plan.json",
    "implementation_slice.json",
]

OPTIONAL_INPUT_FILES = [
    "run_input.json",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kit", required=True, type=Path)
    parser.add_argument("--sample", required=True, type=Path)
    parser.add_argument("--run", required=True, type=Path)
    args = parser.parse_args()

    workspace = args.run / "workspace"
    input_dir = args.run / "input"
    output_dir = args.run / "output"
    log_dir = args.run / "logs"

    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    copytree_clean(args.kit / "template", workspace)

    # Runtime instructions, prompts, agents, and skills are overlaid separately
    # from template/. This keeps greenfield and incremental workspaces aligned.
    copy_kit_runtime(args.kit, workspace)

    # Keep a compatibility mirror for markdown instructions under
    # prototype/input. The prompt-facing canonical path is still
    # workspace-root instructions/; this mirror prevents noisy failed reads
    # from models that probe prototype/input/instructions.
    instructions_src = workspace / "instructions"
    if instructions_src.exists():
        instructions_input_dst = workspace / "prototype" / "input" / "instructions"
        if instructions_input_dst.exists():
            shutil.rmtree(instructions_input_dst)
        shutil.copytree(instructions_src, instructions_input_dst)

    shutil.copy2(args.kit / "generation-rules.yaml", workspace / "prototype" / "input" / "generation-rules.yaml")
    shutil.copy2(args.kit / "kit.yaml", workspace / "prototype" / "input" / "kit.yaml")
    contract = args.kit / "architecture-contract.yaml"
    if contract.exists():
        shutil.copy2(contract, workspace / "prototype" / "input" / "architecture-contract.yaml")
        shutil.copy2(contract, input_dir / "architecture-contract.yaml")

    for name in INPUT_FILES:
        shutil.copy2(args.sample / name, input_dir / name)
        shutil.copy2(args.sample / name, workspace / "prototype" / "input" / name)

    for name in OPTIONAL_INPUT_FILES:
        src = args.sample / name
        if src.exists():
            shutil.copy2(src, input_dir / name)
            shutil.copy2(src, workspace / "prototype" / "input" / name)

    for name in ["file_plan.json", "validation_plan.json"]:
        src = input_dir / name
        if src.exists():
            shutil.copy2(src, workspace / "prototype" / "input" / name)

    # Initialize git baseline for change collection.
    run_cmd(["git", "init"], cwd=workspace)
    run_cmd(["git", "config", "user.email", "prototype@example.local"], cwd=workspace)
    run_cmd(["git", "config", "user.name", "Prototype Runner"], cwd=workspace)
    run_cmd(["git", "add", "."], cwd=workspace)
    run_cmd(["git", "commit", "-m", "baseline"], cwd=workspace)

    print(f"Workspace prepared: {workspace}")


if __name__ == "__main__":
    main()
