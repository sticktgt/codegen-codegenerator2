from __future__ import annotations

import shutil
from pathlib import Path

from common import read_json


def semantic_changed_files(run: Path) -> list[str]:
    changed_path = run / "output" / "changed_files.json"
    if not changed_path.exists():
        return []
    try:
        data = read_json(changed_path)
    except Exception:
        return []
    values = data.get("semantic_changed_files") or []
    return [str(value) for value in values if value]


def snapshot_workspace_files(workspace: Path, rel_paths: list[str]) -> dict[str, dict[str, object]]:
    snapshot: dict[str, dict[str, object]] = {}
    workspace_root = workspace.resolve()
    for rel in sorted(set(rel_paths)):
        # Keep restore inside the active workspace and avoid touching runtime
        # output/log directories. Validation commonly mutates local JSON mock
        # storage; those changes must not leak into repair or later stages.
        if rel.startswith(("prototype/output/", "frontend/test-results/", "frontend/playwright-report/")):
            continue
        path = workspace / rel
        try:
            path.resolve().relative_to(workspace_root)
        except Exception:
            continue
        if path.exists() and path.is_file():
            snapshot[rel] = {"exists": True, "content": path.read_bytes()}
        elif not path.exists():
            snapshot[rel] = {"exists": False, "content": None}
    return snapshot


def restore_workspace_files(workspace: Path, snapshot: dict[str, dict[str, object]]) -> dict[str, object]:
    restored: list[str] = []
    removed: list[str] = []
    errors: list[dict[str, str]] = []
    for rel, item in sorted(snapshot.items()):
        path = workspace / rel
        try:
            if item.get("exists"):
                content = item.get("content")
                if not isinstance(content, (bytes, bytearray)):
                    continue
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(bytes(content))
                restored.append(rel)
            elif path.exists():
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
                removed.append(rel)
        except Exception as exc:  # pragma: no cover - surfaced in validation_result.json
            errors.append({"path": rel, "error": str(exc)})
    return {
        "enabled": bool(snapshot),
        "tracked_files": len(snapshot),
        "restored_files": restored,
        "removed_files": removed,
        "errors": errors,
    }


def merge_restore_results(results: list[dict[str, object]]) -> dict[str, object]:
    if not results:
        return {"enabled": False, "tracked_files": 0, "restored_files": [], "removed_files": [], "errors": []}

    restored: list[str] = []
    removed: list[str] = []
    errors: list[dict[str, str]] = []
    tracked_files = 0
    for result in results:
        tracked_files = max(tracked_files, int(result.get("tracked_files") or 0))
        for value in result.get("restored_files") or []:
            if value not in restored:
                restored.append(str(value))
        for value in result.get("removed_files") or []:
            if value not in removed:
                removed.append(str(value))
        for value in result.get("errors") or []:
            if isinstance(value, dict):
                errors.append(value)  # type: ignore[arg-type]

    return {
        "enabled": any(bool(result.get("enabled")) for result in results),
        "tracked_files": tracked_files,
        "restored_files": restored,
        "removed_files": removed,
        "errors": errors,
    }
