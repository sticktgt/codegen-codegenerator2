from __future__ import annotations

import argparse
import zipfile
from pathlib import Path
from typing import Iterable

from common import write_json


INCLUDE_DIRS = ["input", "output", "logs", "usage", "agent_reports"]
PROMPT_PATTERNS = ["opencode*_prompt.txt"]


def _iter_files(base: Path) -> Iterable[Path]:
    if not base.exists():
        return []
    return (path for path in base.rglob("*") if path.is_file())


def _add_dir(zf: zipfile.ZipFile, run: Path, rel_dir: str, added: set[str]) -> None:
    base = run / rel_dir
    if not base.exists():
        return
    for path in _iter_files(base):
        rel = path.relative_to(run).as_posix()
        if rel in added:
            continue
        zf.write(path, rel)
        added.add(rel)


def export_run_bundle(run: Path, *, include_workspace_io: bool = True) -> dict:
    run = run.resolve()
    dist = run / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    zip_path = dist / "run_diagnostics.zip"
    added: set[str] = set()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel_dir in INCLUDE_DIRS:
            _add_dir(zf, run, rel_dir, added)
        for pattern in PROMPT_PATTERNS:
            for path in run.glob(pattern):
                if path.is_file():
                    rel = path.relative_to(run).as_posix()
                    if rel not in added:
                        zf.write(path, rel)
                        added.add(rel)
        if include_workspace_io:
            for rel_dir in ["workspace/prototype/input", "workspace/prototype/output"]:
                _add_dir(zf, run, rel_dir, added)

    result = {
        "diagnostics_archive": str(zip_path),
        "included_files": sorted(added),
        "included_file_count": len(added),
    }
    write_json(run / "output" / "run_diagnostics_result.json", result)
    print(zip_path)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Export pipeline logs, usage, results, prompts, and agent reports for analysis/archive.")
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--no-workspace-io", action="store_true", help="Do not include workspace/prototype/input and workspace/prototype/output")
    args = parser.parse_args()
    export_run_bundle(args.run, include_workspace_io=not args.no_workspace_io)


if __name__ == "__main__":
    main()
