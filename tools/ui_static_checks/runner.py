from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common import write_json

from .anchors import build_ui_anchor_findings
from .behavior import behavior_test_warnings
from .plan import (
    changed_files,
    file_plan_items,
    group_plan_items_by_path,
    load_contract,
    requirement_scheme_index,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--mode", choices=["warning", "strict"], help="Override ui_validation.mode from architecture contract")
    args = parser.parse_args()

    result = run_checks(args.run, mode_override=args.mode)
    write_check_result(args.run, result)
    print(f"UI static checks {result['status']}; warnings: {len(result['warnings'])}; blockers: {len(result['blockers'])}")
    if result["blockers"]:
        raise SystemExit(1)


def run_checks(run: Path, *, mode_override: str | None = None) -> dict[str, Any]:
    workspace = run / "workspace"
    contract = load_contract(run)
    ui = contract.get("ui_validation") or {}
    enabled = bool(ui.get("enabled", True))
    mode = str(mode_override or ui.get("mode") or "warning")
    attr = str(ui.get("anchor_attribute") or "data-prototype-id")
    ui_artifact_types = set(ui.get("artifact_types") or [])
    changed = changed_files(run)
    warnings: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    checked: list[dict[str, Any]] = []

    if enabled:
        plan_items = file_plan_items(run)
        by_path = group_plan_items_by_path(plan_items)
        requirement_schemes = requirement_scheme_index(plan_items)
        for path, items in sorted(by_path.items()):
            if path not in changed:
                continue
            artifact_types = {str(item.get("artifact_type")) for item in items if item.get("artifact_type")}
            is_ui_artifact = not ui_artifact_types or bool(artifact_types & ui_artifact_types)
            is_behavior_test = bool(artifact_types & {"frontend_behavior_test", "browser_e2e", "ui_behavior_test"}) or path.startswith("frontend/e2e/")
            if not is_ui_artifact and not is_behavior_test:
                continue
            file_path = workspace / path
            if not file_path.exists() or not file_path.is_file():
                continue
            try:
                text = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue

            if is_behavior_test:
                warnings.extend(behavior_test_warnings(path, text))
                checked.append({
                    "path": path,
                    "artifact_types": sorted(artifact_types),
                    "check_type": "frontend_behavior_test_hygiene",
                })
                if not is_ui_artifact:
                    continue

            entry, file_warnings, file_blockers = build_ui_anchor_findings(
                path=path,
                text=text,
                attr=attr,
                mode=mode,
                artifact_types=artifact_types,
                items=items,
                requirement_scheme_elements=requirement_schemes,
            )
            checked.append(entry)
            warnings.extend(file_warnings)
            blockers.extend(file_blockers)

    return {
        "status": "failed" if blockers else "passed",
        "mode": mode,
        "enabled": enabled,
        "anchor_attribute": attr,
        "checked_files": checked,
        "warnings": warnings,
        "blockers": blockers,
    }


def write_check_result(run: Path, result: dict[str, Any]) -> None:
    write_json(run / "output" / "ui_static_check_result.json", result)
    workspace_output = run / "workspace" / "prototype" / "output"
    if workspace_output.exists():
        write_json(workspace_output / "ui_static_check_result.json", result)
