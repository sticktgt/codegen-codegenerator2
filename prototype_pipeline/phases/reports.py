from __future__ import annotations

from pathlib import Path


def copy_workspace_report_if_exists(run: Path, name: str) -> None:
    src = run / "workspace" / "prototype" / "output" / name
    if src.exists():
        dst = run / "output" / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
