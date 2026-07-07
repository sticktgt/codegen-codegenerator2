from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from common import read_json, read_yaml, write_json


def _load_contract(run: Path) -> dict[str, Any]:
    for path in [
        run / "input" / "architecture-contract.yaml",
        run / "workspace" / "prototype" / "input" / "architecture-contract.yaml",
    ]:
        if path.exists():
            data = read_yaml(path)
            return data if isinstance(data, dict) else {}
    return {}


def _changed_files(run: Path) -> set[str]:
    path = run / "output" / "changed_files.json"
    if not path.exists():
        return set()
    data = read_json(path)
    return set(data.get("changed_files") or [])


def _file_plan_items(run: Path) -> list[dict[str, Any]]:
    path = run / "input" / "file_plan.json"
    if not path.exists():
        path = run / "workspace" / "prototype" / "input" / "file_plan.json"
    if not path.exists():
        return []
    data = read_json(path)
    return data.get("allowed_files") or []


def _scheme_elements(item: dict[str, Any]) -> list[str]:
    values = item.get("scheme_elements") or []
    if item.get("scheme_element_id"):
        values.append(item["scheme_element_id"])
    return [str(value) for value in values if value]


def _requirements(item: dict[str, Any]) -> list[str]:
    values = item.get("requirements") or item.get("requirement_ids") or []
    if item.get("requirement_id"):
        values.append(item["requirement_id"])
    return [str(value) for value in values if value]


def _has_anchor(text: str, attr: str) -> bool:
    return bool(re.search(rf"\b{re.escape(attr)}\s*=", text))


def _anchors_for(text: str, attr: str) -> set[str]:
    pattern = re.compile(rf"\b{re.escape(attr)}\s*=\s*['\"]([^'\"]+)['\"]")
    return {match.group(1) for match in pattern.finditer(text)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--mode", choices=["warning", "strict"], help="Override ui_validation.mode from architecture contract")
    args = parser.parse_args()

    run = args.run
    workspace = run / "workspace"
    contract = _load_contract(run)
    ui = contract.get("ui_validation") or {}
    enabled = bool(ui.get("enabled", True))
    mode = str(args.mode or ui.get("mode") or "warning")
    attr = str(ui.get("anchor_attribute") or "data-prototype-id")
    ui_artifact_types = set(ui.get("artifact_types") or [])
    changed = _changed_files(run)
    warnings: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    checked: list[dict[str, Any]] = []

    if enabled:
        plan_items = _file_plan_items(run)
        by_path: dict[str, list[dict[str, Any]]] = {}
        requirement_scheme_elements: dict[str, set[str]] = {}
        for item in plan_items:
            path = item.get("path")
            if path:
                by_path.setdefault(str(path), []).append(item)
            item_schemes = set(_scheme_elements(item))
            for requirement in _requirements(item):
                requirement_scheme_elements.setdefault(requirement, set()).update(item_schemes)

        for path, items in sorted(by_path.items()):
            if path not in changed:
                continue
            artifact_types = {str(item.get("artifact_type")) for item in items if item.get("artifact_type")}
            if ui_artifact_types and not (artifact_types & ui_artifact_types):
                continue
            file_path = workspace / path
            if not file_path.exists() or not file_path.is_file():
                continue
            try:
                text = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            anchors = sorted(_anchors_for(text, attr))
            scheme_elements: list[str] = []
            relevant_requirements: list[str] = []
            relevant_scheme_elements: list[str] = []
            for item in items:
                for requirement in _requirements(item):
                    if requirement not in relevant_requirements:
                        relevant_requirements.append(requirement)
                for scheme in _scheme_elements(item):
                    if scheme not in scheme_elements:
                        scheme_elements.append(scheme)
            for requirement in relevant_requirements:
                for scheme in sorted(requirement_scheme_elements.get(requirement, set())):
                    if scheme not in relevant_scheme_elements:
                        relevant_scheme_elements.append(scheme)
            checked.append({
                "path": path,
                "artifact_types": sorted(artifact_types),
                "requirements": relevant_requirements,
                "scheme_elements": scheme_elements,
                "relevant_scheme_elements": relevant_scheme_elements,
                "anchors": anchors,
            })
            if not _has_anchor(text, attr):
                warning = {
                    "code": "missing_ui_anchor",
                    "path": path,
                    "artifact_types": sorted(artifact_types),
                    "scheme_elements": scheme_elements,
                    "message": f"Changed UI file has no {attr} anchors. Add stable anchors for new/changed controls when practical.",
                }
                if mode == "strict":
                    blockers.append(warning)
                else:
                    warnings.append(warning)
            else:
                # Prefer anchors that reference scheme element ids. For UI screens, an
                # action anchor may belong to another file-plan item in the same
                # requirement, e.g. frontend_screen uses action.delete-note from a
                # frontend_action artifact. Treat that as linked.
                anchor_set = set(anchors)
                direct_scheme_set = set(scheme_elements)
                relevant_scheme_set = set(relevant_scheme_elements)
                required_action_anchors = {scheme for scheme in relevant_scheme_set if scheme.startswith("action.")}
                missing_action_anchors = sorted(required_action_anchors - anchor_set)
                if missing_action_anchors:
                    warning = {
                        "code": "missing_required_ui_action_anchor",
                        "path": path,
                        "anchors": anchors,
                        "requirements": relevant_requirements,
                        "scheme_elements": scheme_elements,
                        "relevant_scheme_elements": relevant_scheme_elements,
                        "missing_anchors": missing_action_anchors,
                        "message": f"Changed UI file is missing required action anchors: {', '.join(missing_action_anchors)}.",
                    }
                    if mode == "strict":
                        blockers.append(warning)
                    else:
                        warnings.append(warning)
                elif relevant_scheme_set and not (relevant_scheme_set & anchor_set):
                    warning = {
                        "code": "ui_anchor_not_linked_to_requirement_scheme_element",
                        "path": path,
                        "anchors": anchors,
                        "requirements": relevant_requirements,
                        "scheme_elements": scheme_elements,
                        "relevant_scheme_elements": relevant_scheme_elements,
                        "message": f"UI anchors exist but do not match any scheme element ids linked to the same requirement.",
                    }
                    if mode == "strict":
                        blockers.append(warning)
                    else:
                        warnings.append(warning)
                elif direct_scheme_set and not (direct_scheme_set & anchor_set):
                    checked[-1]["anchor_link_scope"] = "requirement"

    result = {
        "status": "failed" if blockers else "passed",
        "mode": mode,
        "enabled": enabled,
        "anchor_attribute": attr,
        "checked_files": checked,
        "warnings": warnings,
        "blockers": blockers,
    }
    write_json(run / "output" / "ui_static_check_result.json", result)
    workspace_output = workspace / "prototype" / "output"
    if workspace_output.exists():
        write_json(workspace_output / "ui_static_check_result.json", result)
    print(f"UI static checks {result['status']}; warnings: {len(warnings)}; blockers: {len(blockers)}")
    if blockers:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
