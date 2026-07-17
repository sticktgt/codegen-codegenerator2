from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import Any

from common import read_yaml, write_json
from kit_runtime import copy_kit_runtime


KIT_INPUT_FILES = [
    "kit.yaml",
    "generation-rules.yaml",
    "architecture-contract.yaml",
]

RUN_CONTEXT_INPUT_FILES = [
    "run_input.json",
]

RUN_CONTEXT_INPUT_DIRS = [
    "baseline_context",
]


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = read_yaml(path)
    return data if isinstance(data, dict) else {}


def _copy_if_exists(src: Path, *dests: Path) -> bool:
    if not src.exists():
        return False
    for dst in dests:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    return True


def _copytree_clean_if_exists(src: Path, dst: Path) -> bool:
    if not src.exists() or not src.is_dir():
        return False
    if dst.exists():
        shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst)
    return True


def _infer_kit_dir(root: Path, run: Path, explicit_kit: Path | None) -> Path | None:
    if explicit_kit:
        path = explicit_kit if explicit_kit.is_absolute() else root / explicit_kit
        return path if path.exists() else None

    candidates: list[Path] = []
    for kit_yaml in [
        run / "workspace" / "prototype" / "input" / "kit.yaml",
        run / "input" / "kit.yaml",
    ]:
        kit_data = _load_yaml(kit_yaml)
        kit_id = kit_data.get("id")
        if kit_id:
            candidates.append(root / "prototype-kits" / str(kit_id))

    # Most spike runs use a single kit. Use it if unambiguous.
    kits_root = root / "prototype-kits"
    if kits_root.exists():
        existing = [path for path in kits_root.iterdir() if path.is_dir() and not path.name.startswith("_")]
        if len(existing) == 1:
            candidates.append(existing[0])

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def sync_run_inputs(run: Path, *, root: Path, kit: Path | None = None) -> dict[str, Any]:
    run = run.resolve()
    workspace = run / "workspace"
    workspace_input = workspace / "prototype" / "input"
    run_input = run / "input"
    actions: list[str] = []
    warnings: list[dict[str, Any]] = []

    run_input.mkdir(parents=True, exist_ok=True)
    if workspace.exists():
        workspace_input.mkdir(parents=True, exist_ok=True)

    kit_dir = _infer_kit_dir(root, run, kit)
    if kit_dir is None:
        warnings.append({"code": "kit_not_found", "message": "Unable to infer kit directory for run input sync."})
    else:
        for name in KIT_INPUT_FILES:
            src = kit_dir / name
            if src.exists():
                dests = [run_input / name]
                if workspace.exists():
                    dests.append(workspace_input / name)
                if _copy_if_exists(src, *dests):
                    actions.append(f"sync_{name}")
            else:
                warnings.append({"code": "kit_input_file_missing", "path": str(src)})

        # Refresh kit-owned runtime context independently from template/. This
        # includes modular instructions and optional project-local OpenCode skills.
        # Also keep the instruction compatibility mirror under prototype/input.
        if workspace.exists():
            for copied in copy_kit_runtime(kit_dir, workspace):
                actions.append(f"sync_runtime_{copied}")
            instructions_src = workspace / "instructions"
            if _copytree_clean_if_exists(instructions_src, workspace_input / "instructions"):
                actions.append("sync_prototype_input_instructions")

    # Mirror already-present run inputs into workspace inputs, useful when the run
    # was created with an older preparation script and then rerun with a newer pipeline.
    if workspace.exists():
        mirrored_names = set(KIT_INPUT_FILES) | set(RUN_CONTEXT_INPUT_FILES)
        for src in run_input.iterdir() if run_input.exists() else []:
            if src.is_file() and src.name in mirrored_names:
                dst = workspace_input / src.name
                if not dst.exists() or src.read_bytes() != dst.read_bytes():
                    shutil.copy2(src, dst)
                    actions.append(f"mirror_run_input_{src.name}")
            elif src.is_dir() and src.name in RUN_CONTEXT_INPUT_DIRS:
                dst = workspace_input / src.name
                if _copytree_clean_if_exists(src, dst):
                    actions.append(f"mirror_run_input_dir_{src.name}")

    result = {
        "run": str(run),
        "workspace": str(workspace),
        "kit": str(kit_dir) if kit_dir else None,
        "actions": actions,
        "warnings": warnings,
    }
    out = run / "output" / "sync_run_inputs_result.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    write_json(out, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Synchronize kit-level input artifacts into a run and its workspace.")
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--kit", type=Path, help="Optional explicit kit directory")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    result = sync_run_inputs(args.run, root=root, kit=args.kit)
    for action in result["actions"]:
        print(action)
    for warning in result["warnings"]:
        print(f"warning:{warning.get('code')}:{warning.get('path') or warning.get('message')}")


if __name__ == "__main__":
    main()
