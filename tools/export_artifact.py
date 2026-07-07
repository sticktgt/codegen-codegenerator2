from __future__ import annotations

import argparse
import zipfile
from pathlib import Path
from common import write_json

EXCLUDE_PREFIXES = (
    ".git/",
    ".venv/",
    "node_modules/",
    "frontend/node_modules/",
    "dist/",
    "frontend/dist/",
    "frontend/playwright-report/",
    "frontend/test-results/",
    "playwright-report/",
    "test-results/",
    "backend/.pytest_cache/",
    ".pytest_cache/",
)
EXCLUDE_NAMES = {"__pycache__"}
EXCLUDE_SUFFIXES = (".pyc", ".pyo")


def _include(path: Path, workspace: Path) -> bool:
    rel = path.relative_to(workspace).as_posix()
    if any(rel == prefix.rstrip("/") or rel.startswith(prefix) for prefix in EXCLUDE_PREFIXES):
        return False
    if any(part in EXCLUDE_NAMES for part in path.relative_to(workspace).parts):
        return False
    if rel.endswith(EXCLUDE_SUFFIXES):
        return False
    return path.is_file()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, type=Path)
    args = parser.parse_args()

    workspace = args.run / "workspace"
    dist = args.run / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    zip_path = dist / "prototype_artifact.zip"

    added = 0
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(workspace.rglob("*")):
            if _include(path, workspace):
                zf.write(path, path.relative_to(workspace).as_posix())
                added += 1

    write_json(args.run / "output" / "export_result.json", {"artifact": str(zip_path), "included_file_count": added})
    print(zip_path)


if __name__ == "__main__":
    main()
