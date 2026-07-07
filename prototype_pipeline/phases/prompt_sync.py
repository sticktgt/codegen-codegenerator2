from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Any

from tools.common import read_yaml, write_json

PROMPT_SOURCES = {
    "plan": "plan_prompt.md",
    "plan-review": "plan_review_prompt.md",
    "implementation": "implementation_prompt.md",
    "repair": "repair_prompt.md",
}

RUN_PROMPT_SNAPSHOTS = {
    "plan": "opencode_plan_prompt.txt",
    "plan-review": "opencode_plan_review_prompt.txt",
    "implementation": "opencode_implementation_prompt.txt",
    "repair": "opencode_repair_prompt.txt",
}


def _resolve(root: Path, path: Path | None) -> Path | None:
    if path is None:
        return None
    return path if path.is_absolute() else root / path


def _sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = read_yaml(path)
    return data if isinstance(data, dict) else {}


def _infer_kit_dir(root: Path, run: Path, explicit_kit: Path | None) -> Path | None:
    if explicit_kit:
        candidate = explicit_kit if explicit_kit.is_absolute() else root / explicit_kit
        return candidate if candidate.exists() else None

    candidates: list[Path] = []
    for kit_yaml in [run / "input" / "kit.yaml", run / "workspace" / "prototype" / "input" / "kit.yaml"]:
        kit_data = _load_yaml(kit_yaml)
        kit_id = kit_data.get("id")
        if kit_id:
            candidates.append(root / "prototype-kits" / str(kit_id))

    kits_root = root / "prototype-kits"
    if kits_root.exists():
        existing = [path for path in kits_root.iterdir() if path.is_dir()]
        if len(existing) == 1:
            candidates.append(existing[0])

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _is_managed_snapshot(prompt_path: Path, run: Path, phase: str) -> bool:
    try:
        resolved_prompt = prompt_path.resolve()
        resolved_run = run.resolve()
    except FileNotFoundError:
        resolved_prompt = prompt_path.absolute()
        resolved_run = run.absolute()

    expected_name = RUN_PROMPT_SNAPSHOTS.get(phase)
    if expected_name and resolved_prompt == (resolved_run / expected_name):
        return True
    return resolved_run in resolved_prompt.parents


def _phase_result(
    *,
    root: Path,
    run: Path,
    kit_dir: Path | None,
    phase: str,
    prompt_file: Path | None,
    sync: bool,
) -> dict[str, Any]:
    prompt_path = _resolve(root, prompt_file)
    source_name = PROMPT_SOURCES[phase]
    source_path = kit_dir / "prompts" / source_name if kit_dir else None
    result: dict[str, Any] = {
        "phase": phase,
        "prompt_file": str(prompt_path) if prompt_path else None,
        "kit_source": str(source_path) if source_path else None,
        "managed_snapshot": False,
        "action": "skipped",
        "status": "not_configured",
        "prompt_sha256": None,
        "kit_source_sha256": None,
    }

    if prompt_path is None:
        return result

    managed = _is_managed_snapshot(prompt_path, run, phase)
    result["managed_snapshot"] = managed

    if source_path is None:
        result.update({"status": "kit_not_found", "action": "check_only"})
        return result
    if not source_path.exists():
        result.update({"status": "kit_prompt_missing", "action": "check_only"})
        return result

    source_hash = _sha256(source_path)
    prompt_hash = _sha256(prompt_path)
    result["kit_source_sha256"] = source_hash
    result["prompt_sha256"] = prompt_hash

    if prompt_hash == source_hash:
        result.update({"status": "up_to_date", "action": "none"})
        return result

    if sync and managed:
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, prompt_path)
        result.update({
            "status": "synced",
            "action": "copied_from_kit",
            "prompt_sha256": _sha256(prompt_path),
        })
        return result

    if managed:
        result.update({"status": "stale", "action": "check_only"})
    else:
        result.update({"status": "external_override", "action": "not_synced"})
    return result


def sync_prompt_snapshots(
    *,
    root: Path,
    run: Path,
    kit: Path | None,
    prompt_files: dict[str, Path | None],
    sync: bool,
) -> dict[str, Any]:
    run = run if run.is_absolute() else root / run
    kit_dir = _infer_kit_dir(root, run, kit)
    prompts = [
        _phase_result(
            root=root,
            run=run,
            kit_dir=kit_dir,
            phase=phase,
            prompt_file=prompt_files.get(phase),
            sync=sync,
        )
        for phase in ["plan", "plan-review", "implementation", "repair"]
    ]

    warnings: list[dict[str, Any]] = []
    for item in prompts:
        status = item.get("status")
        if status in {"stale", "external_override", "kit_not_found", "kit_prompt_missing"}:
            warnings.append({
                "code": f"prompt_{status}",
                "phase": item.get("phase"),
                "prompt_file": item.get("prompt_file"),
                "kit_source": item.get("kit_source"),
                "message": _warning_message(status),
            })

    result = {
        "run": str(run),
        "kit": str(kit_dir) if kit_dir else None,
        "sync_requested": sync,
        "prompts": prompts,
        "warnings": warnings,
    }
    out = run / "output" / "sync_prompt_files_result.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    write_json(out, result)
    return result


def _warning_message(status: str) -> str:
    messages = {
        "stale": "Run prompt snapshot differs from the kit prompt. Use --sync-prompts to refresh it.",
        "external_override": "Prompt file is outside the run directory and was not synchronized from the kit.",
        "kit_not_found": "Unable to infer kit directory for prompt synchronization.",
        "kit_prompt_missing": "Expected kit prompt file is missing.",
    }
    return messages.get(status, status)
