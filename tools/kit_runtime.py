from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from common import read_yaml

KIT_RUNTIME_FILES = (
    "AGENTS.md",
    "opencode.json",
    "Taskfile.yml",
)

KIT_DIRECT_RUNTIME_DIRS = (
    # The kit owns only the prompt composition manifest here. Prompt source
    # modules remain repository-level shared files and are composed into run
    # snapshots by prompt_sync.py.
    "prompts",
)

RUNTIME_MANIFEST_DEFAULT = "runtime/manifest.yaml"
RUNTIME_GROUP_TARGETS = {
    "agents": "agents",
    "instructions": "instructions",
    "examples": "examples",
    "opencode": ".opencode",
}


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = read_yaml(path)
    return data if isinstance(data, dict) else {}


def _runtime_manifest_path(kit: Path) -> Path:
    kit_data = _load_yaml(kit / "kit.yaml")
    configured = kit_data.get("runtime_manifest")
    if configured:
        candidate = Path(str(configured))
        return candidate if candidate.is_absolute() else kit / candidate
    return kit / RUNTIME_MANIFEST_DEFAULT


def _resolve_manifest_source(
    *,
    repository_root: Path,
    kit: Path,
    manifest_path: Path,
    path_base: str,
    source: str,
) -> Path:
    source_path = Path(source)
    if source_path.is_absolute():
        return source_path
    if path_base == "repository":
        return repository_root / source_path
    if path_base == "kit":
        return kit / source_path
    if path_base == "manifest":
        return manifest_path.parent / source_path
    raise ValueError(f"Unsupported runtime manifest path_base: {path_base}")


def _safe_target(base: Path, target: str) -> Path:
    target_path = Path(target)
    if target_path.is_absolute():
        raise ValueError(f"Runtime manifest target must be relative: {target}")
    resolved_base = base.resolve()
    resolved_target = (base / target_path).resolve()
    if resolved_target != resolved_base and resolved_base not in resolved_target.parents:
        raise ValueError(f"Runtime manifest target escapes destination directory: {target}")
    return base / target_path


def _copy_manifest_item(src: Path, dst: Path) -> None:
    if not src.exists():
        raise FileNotFoundError(f"Runtime manifest source does not exist: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        shutil.copy2(src, dst)


def _materialize_runtime_manifest(kit: Path, workspace: Path) -> list[str]:
    manifest_path = _runtime_manifest_path(kit)
    if not manifest_path.exists():
        raise FileNotFoundError(f"Kit runtime manifest does not exist: {manifest_path}")

    manifest = _load_yaml(manifest_path)
    if manifest.get("version") != 1:
        raise ValueError(f"Unsupported kit runtime manifest version: {manifest_path}")

    runtime = manifest.get("runtime")
    if not isinstance(runtime, dict):
        raise ValueError(f"Kit runtime manifest must define object field runtime: {manifest_path}")

    repository_root = kit.resolve().parents[1]
    path_base = str(manifest.get("path_base", "manifest"))
    copied: list[str] = []

    # Clean all manifest-managed destination groups first. Multiple source
    # modules may merge into the same destination group afterwards.
    for group_name, destination_name in RUNTIME_GROUP_TARGETS.items():
        destination = workspace / destination_name
        if destination.exists():
            shutil.rmtree(destination)

        items = runtime.get(group_name, [])
        if items is None:
            items = []
        if not isinstance(items, list):
            raise ValueError(f"Runtime manifest group must be a list: {group_name}")

        for item in items:
            if not isinstance(item, dict):
                raise ValueError(f"Runtime manifest item must be an object in group: {group_name}")
            source = item.get("source")
            target = item.get("target")
            if not source or not target:
                raise ValueError(f"Runtime manifest item requires source and target in group: {group_name}")
            src = _resolve_manifest_source(
                repository_root=repository_root,
                kit=kit,
                manifest_path=manifest_path,
                path_base=path_base,
                source=str(source),
            )
            dst = _safe_target(destination, str(target))
            _copy_manifest_item(src, dst)

        if items:
            copied.append(destination_name)

    # Keep the active manifest visible in the workspace for diagnostics. It is
    # not read by OpenCode as an instruction source, but it makes the resolved
    # kit profile auditable from the run workspace alone.
    manifest_root = workspace / "runtime"
    if manifest_root.exists():
        shutil.rmtree(manifest_root)
    manifest_dst = manifest_root / "manifest.yaml"
    manifest_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(manifest_path, manifest_dst)
    copied.append("runtime")

    return copied


def copy_kit_runtime(kit: Path, workspace: Path) -> list[str]:
    """Overlay kit-owned runtime context into a prepared workspace.

    Runtime context is deliberately separate from ``template/``. The template
    is used only for a greenfield workspace, while this function also refreshes
    runtime files for incremental runs that start from a previous workspace.
    """
    copied: list[str] = []

    for name in KIT_RUNTIME_FILES:
        src = kit / name
        dst = workspace / name
        if not src.exists():
            if dst.exists():
                dst.unlink()
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(name)

    for name in KIT_DIRECT_RUNTIME_DIRS:
        src = kit / name
        dst = workspace / name
        if dst.exists():
            shutil.rmtree(dst)
        if not src.exists() or not src.is_dir():
            continue
        shutil.copytree(src, dst)
        copied.append(name)

    copied.extend(_materialize_runtime_manifest(kit, workspace))
    return copied
