from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from tools.common import read_yaml, write_json

RUN_PROMPT_SNAPSHOTS = {
    "plan": "opencode_plan_prompt.txt",
    "plan-review": "opencode_plan_review_prompt.txt",
    "implementation": "opencode_implementation_prompt.txt",
    "repair": "opencode_repair_prompt.txt",
}

DEFAULT_PROMPT_MANIFEST = "prompts/manifest.yaml"


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


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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
        existing = [path for path in kits_root.iterdir() if path.is_dir() and not path.name.startswith("_")]
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


def _manifest_path(kit_dir: Path) -> Path:
    kit_data = _load_yaml(kit_dir / "kit.yaml")
    configured = kit_data.get("prompt_manifest")
    if configured:
        candidate = Path(str(configured))
        return candidate if candidate.is_absolute() else kit_dir / candidate
    return kit_dir / DEFAULT_PROMPT_MANIFEST


def _resolve_manifest_source(
    *,
    root: Path,
    kit_dir: Path,
    manifest_path: Path,
    path_base: str,
    source: str,
) -> Path:
    source_path = Path(source)
    if source_path.is_absolute():
        return source_path
    if path_base == "repository":
        return root / source_path
    if path_base == "kit":
        return kit_dir / source_path
    if path_base == "manifest":
        return manifest_path.parent / source_path
    raise ValueError(f"Unsupported prompt manifest path_base: {path_base}")


def _compose_prompt(
    *,
    root: Path,
    kit_dir: Path,
    phase: str,
) -> dict[str, Any]:
    manifest_path = _manifest_path(kit_dir)
    if not manifest_path.exists():
        return {
            "status": "missing",
            "manifest": manifest_path,
            "sources": [],
            "missing_sources": [manifest_path],
            "content": None,
        }

    manifest = _load_yaml(manifest_path)
    if manifest.get("version") != 1:
        return {
            "status": "invalid_manifest",
            "manifest": manifest_path,
            "sources": [],
            "missing_sources": [],
            "content": None,
        }
    phases = manifest.get("phases")
    phase_sources = phases.get(phase) if isinstance(phases, dict) else None
    if not isinstance(phase_sources, list) or not phase_sources:
        return {
            "status": "invalid_manifest",
            "manifest": manifest_path,
            "sources": [],
            "missing_sources": [],
            "content": None,
        }

    path_base = str(manifest.get("path_base", "manifest"))
    try:
        sources = [
            _resolve_manifest_source(
                root=root,
                kit_dir=kit_dir,
                manifest_path=manifest_path,
                path_base=path_base,
                source=str(item),
            )
            for item in phase_sources
        ]
    except ValueError:
        return {
            "status": "invalid_manifest",
            "manifest": manifest_path,
            "sources": [],
            "missing_sources": [],
            "content": None,
        }

    missing_sources = [path for path in sources if not path.exists() or not path.is_file()]
    if missing_sources:
        return {
            "status": "missing",
            "manifest": manifest_path,
            "sources": sources,
            "missing_sources": missing_sources,
            "content": None,
        }

    parts = [path.read_text(encoding="utf-8").strip() for path in sources]
    content = "\n\n".join(part for part in parts if part) + "\n"
    return {
        "status": "ok",
        "manifest": manifest_path,
        "sources": sources,
        "missing_sources": [],
        "content": content,
    }


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
    result: dict[str, Any] = {
        "phase": phase,
        "prompt_file": str(prompt_path) if prompt_path else None,
        "kit_source": None,
        "kit_sources": [],
        "composition_manifest": None,
        "missing_sources": [],
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

    if kit_dir is None:
        result.update({"status": "kit_not_found", "action": "check_only"})
        return result

    composition = _compose_prompt(root=root, kit_dir=kit_dir, phase=phase)
    sources = composition.get("sources", [])
    manifest_path = composition.get("manifest")
    result["kit_source"] = str(manifest_path or sources[0]) if (manifest_path or sources) else None
    result["kit_sources"] = [str(path) for path in sources]
    result["composition_manifest"] = str(manifest_path) if manifest_path else None
    result["missing_sources"] = [str(path) for path in composition.get("missing_sources", [])]

    if composition.get("status") == "invalid_manifest":
        result.update({"status": "kit_prompt_invalid", "action": "check_only"})
        return result
    if composition.get("status") != "ok":
        result.update({"status": "kit_prompt_missing", "action": "check_only"})
        return result

    source_content = str(composition["content"])
    source_hash = _sha256_text(source_content)
    prompt_hash = _sha256(prompt_path)
    result["kit_source_sha256"] = source_hash
    result["prompt_sha256"] = prompt_hash

    if prompt_hash == source_hash:
        result.update({"status": "up_to_date", "action": "none"})
        return result

    if sync and managed:
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(source_content, encoding="utf-8")
        result.update({
            "status": "synced",
            "action": "composed_from_kit",
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
        if status in {
            "stale",
            "external_override",
            "kit_not_found",
            "kit_prompt_missing",
            "kit_prompt_invalid",
        }:
            warnings.append({
                "code": f"prompt_{status}",
                "phase": item.get("phase"),
                "prompt_file": item.get("prompt_file"),
                "kit_source": item.get("kit_source"),
                "kit_sources": item.get("kit_sources", []),
                "missing_sources": item.get("missing_sources", []),
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
        "stale": "Run prompt snapshot differs from the composed kit prompt. Use --sync-prompts to refresh it.",
        "external_override": "Prompt file is outside the run directory and was not synchronized from the kit.",
        "kit_not_found": "Unable to infer kit directory for prompt synchronization.",
        "kit_prompt_missing": "The kit prompt manifest or one of its configured source modules is missing.",
        "kit_prompt_invalid": "The kit prompt manifest is invalid or does not define the requested phase.",
    }
    return messages.get(status, status)
