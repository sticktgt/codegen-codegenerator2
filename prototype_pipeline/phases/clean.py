from __future__ import annotations

import subprocess
from pathlib import Path


def clean_run(root: Path, py: str, run: Path, *, clean_root_prototype_output: bool, keep_plan_inputs: bool) -> None:
    cmd = [py, "tools/clean_run_artifacts.py", "--run", str(run)]
    if clean_root_prototype_output:
        cmd.append("--clean-root-prototype-output")
    if keep_plan_inputs:
        cmd.append("--keep-plan-inputs")
    subprocess.run(cmd, cwd=root, check=True)
