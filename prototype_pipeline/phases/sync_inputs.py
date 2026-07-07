from __future__ import annotations

import subprocess
from pathlib import Path


def sync_run_inputs(root: Path, py: str, run: Path, kit: Path | None) -> None:
    cmd = [py, "tools/sync_run_inputs.py", "--run", str(run)]
    if kit:
        cmd.extend(["--kit", str(kit)])
    subprocess.run(cmd, cwd=root, check=False)
