from __future__ import annotations

import shutil
from pathlib import Path

from common import read_json

# Files under these roots are part of the generated prototype source/test
# surface. Validation stages may mutate planned files or accidentally create
# additional semantic files (for example because a test resolves a relative
# JSON storage path from the wrong working directory). The validation runner
# snapshots these roots before validation and restores them after every stage.
SEMANTIC_SNAPSHOT_ROOTS = (
    "backend",
    "frontend/src",
    "frontend/e2e",
)

# Runtime artifacts under semantic roots should not be treated as durable source
# files. They may be safely removed by validation restore.
IGNORED_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "test-results",
    "playwright-report",
}
IGNORED_SUFFIXES = {".pyc", ".pyo"}


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


def _is_ignored_runtime_path(rel: str) -> bool:
    path = Path(rel)
    if any(part in IGNORED_PARTS for part in path.parts):
        return True
    return path.suffix in IGNORED_SUFFIXES


def _is_semantic_snapshot_path(rel: str) -> bool:
    if rel.startswith(("prototype/output/", "frontend/test-results/", "frontend/playwright-report/")):
        return False
    if _is_ignored_runtime_path(rel):
        return False
    return rel.startswith(SEMANTIC_SNAPSHOT_ROOTS)


def _safe_rel_files(root: Path, workspace: Path) -> list[str]:
    if not root.exists():
        return []
    workspace_root = workspace.resolve()
    results: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            rel = path.resolve().relative_to(workspace_root).as_posix()
        except Exception:
            continue
        if _is_semantic_snapshot_path(rel):
            results.append(rel)
    return results


def _snapshot_rel_paths(workspace: Path, rel_paths: list[str]) -> list[str]:
    paths: set[str] = {rel for rel in rel_paths if _is_semantic_snapshot_path(rel)}
    for root in SEMANTIC_SNAPSHOT_ROOTS:
        paths.update(_safe_rel_files(workspace / root, workspace))
    return sorted(paths)


def snapshot_workspace_files(workspace: Path, rel_paths: list[str]) -> dict[str, dict[str, object]]:
    snapshot: dict[str, dict[str, object]] = {}
    workspace_root = workspace.resolve()
    for rel in _snapshot_rel_paths(workspace, rel_paths):
        # Keep restore inside the active workspace. Validation commonly mutates
        # local JSON mock storage; those changes must not leak into repair or
        # later validation stages.
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


def _remove_new_semantic_files(workspace: Path, snapshot: dict[str, dict[str, object]]) -> list[str]:
    removed: list[str] = []
    known_paths = set(snapshot)
    for root in SEMANTIC_SNAPSHOT_ROOTS:
        for rel in _safe_rel_files(workspace / root, workspace):
            if rel in known_paths:
                continue
            path = workspace / rel
            try:
                path.unlink()
                removed.append(rel)
            except FileNotFoundError:
                continue
    # Clean empty directories that may have been created only by a bad relative
    # path during validation, without touching the semantic root directories.
    for root in SEMANTIC_SNAPSHOT_ROOTS:
        root_path = workspace / root
        if not root_path.exists():
            continue
        for directory in sorted((p for p in root_path.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
            try:
                directory.rmdir()
            except OSError:
                pass
    return removed


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
    for rel in _remove_new_semantic_files(workspace, snapshot):
        if rel not in removed:
            removed.append(rel)
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
