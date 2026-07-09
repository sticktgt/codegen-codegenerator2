from __future__ import annotations

import re
from typing import Any

from .plan import requirements, scheme_elements


def has_anchor(text: str, attr: str) -> bool:
    return bool(re.search(rf"\b{re.escape(attr)}\s*=", text))


def anchor_counts_for(text: str, attr: str) -> dict[str, int]:
    pattern = re.compile(rf"\b{re.escape(attr)}\s*=\s*['\"]([^'\"]+)['\"]")
    counts: dict[str, int] = {}
    for match in pattern.finditer(text):
        anchor = match.group(1)
        counts[anchor] = counts.get(anchor, 0) + 1
    return counts


def collect_item_context(
    items: list[dict[str, Any]],
    requirement_scheme_elements: dict[str, set[str]],
) -> dict[str, Any]:
    scheme_ids: list[str] = []
    requirement_ids: list[str] = []
    relevant_scheme_ids: list[str] = []
    for item in items:
        for requirement in requirements(item):
            if requirement not in requirement_ids:
                requirement_ids.append(requirement)
        for scheme in scheme_elements(item):
            if scheme not in scheme_ids:
                scheme_ids.append(scheme)
    for requirement in requirement_ids:
        for scheme in sorted(requirement_scheme_elements.get(requirement, set())):
            if scheme not in relevant_scheme_ids:
                relevant_scheme_ids.append(scheme)
    return {
        "requirements": requirement_ids,
        "scheme_elements": scheme_ids,
        "relevant_scheme_elements": relevant_scheme_ids,
    }


def required_root_anchors(items: list[dict[str, Any]]) -> set[str]:
    """Return root-level UI anchors this file-plan item owns directly.

    The check is intentionally file-scoped. Requirement-linked scheme elements
    from other files are diagnostics context only and must not force a widget to
    carry screen or action anchors owned elsewhere.
    """
    required: set[str] = set()
    for item in items:
        artifact_type = str(item.get("artifact_type") or "")
        schemes = set(scheme_elements(item))
        if artifact_type == "frontend_screen":
            required.update(scheme for scheme in schemes if scheme.startswith("screen."))
        elif artifact_type == "frontend_widget":
            required.update(scheme for scheme in schemes if scheme.startswith("widget."))
    return required


def required_action_anchors(items: list[dict[str, Any]]) -> set[str]:
    """Return action anchors explicitly owned by this file-plan path."""
    required: set[str] = set()
    for item in items:
        required.update(scheme for scheme in scheme_elements(item) if scheme.startswith("action."))
    return required


def build_ui_anchor_findings(
    *,
    path: str,
    text: str,
    attr: str,
    mode: str,
    artifact_types: set[str],
    items: list[dict[str, Any]],
    requirement_scheme_elements: dict[str, set[str]],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    warnings: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    anchor_counts = anchor_counts_for(text, attr)
    anchors = sorted(anchor_counts)
    anchor_set = set(anchors)
    context = collect_item_context(items, requirement_scheme_elements)
    checked_entry = {
        "path": path,
        "artifact_types": sorted(artifact_types),
        "requirements": context["requirements"],
        "scheme_elements": context["scheme_elements"],
        "relevant_scheme_elements": context["relevant_scheme_elements"],
        "anchors": anchors,
    }

    if not has_anchor(text, attr):
        warning = {
            "code": "missing_ui_anchor",
            "path": path,
            "artifact_types": sorted(artifact_types),
            "scheme_elements": context["scheme_elements"],
            "message": f"Changed UI file has no {attr} anchors. Add stable anchors for new/changed controls when practical.",
        }
        _add_finding(warning, mode, warnings, blockers)
        return checked_entry, warnings, blockers

    root_anchors = required_root_anchors(items)
    action_anchors = required_action_anchors(items)
    required_direct = root_anchors | action_anchors
    duplicate_root_anchors = {
        anchor: count
        for anchor, count in anchor_counts.items()
        if anchor in root_anchors and count > 1
    }
    if duplicate_root_anchors:
        warning = {
            "code": "duplicate_unique_ui_anchor",
            "path": path,
            "anchors": anchors,
            "requirements": context["requirements"],
            "scheme_elements": context["scheme_elements"],
            "duplicate_anchors": [
                {"anchor": anchor, "count": count}
                for anchor, count in sorted(duplicate_root_anchors.items())
            ],
            "message": (
                "Changed UI file has duplicate direct screen/widget root anchors: "
                f"{', '.join(sorted(duplicate_root_anchors))}. Use each owned screen.* or widget.* "
                "root anchor only once per source file."
            ),
        }
        _add_finding(warning, mode, warnings, blockers)
        return checked_entry, warnings, blockers

    missing_action_anchors = sorted(action_anchors - anchor_set)
    if missing_action_anchors:
        warning = {
            "code": "missing_required_ui_action_anchor",
            "path": path,
            "anchors": anchors,
            "requirements": context["requirements"],
            "scheme_elements": context["scheme_elements"],
            "relevant_scheme_elements": context["relevant_scheme_elements"],
            "missing_anchors": missing_action_anchors,
            "message": (
                "Changed UI file is missing action anchors it directly owns in file_plan: "
                f"{', '.join(missing_action_anchors)}."
            ),
        }
        _add_finding(warning, mode, warnings, blockers)
        return checked_entry, warnings, blockers

    missing_root_anchors = sorted(root_anchors - anchor_set)
    if missing_root_anchors:
        warning = {
            "code": "missing_required_ui_root_anchor",
            "path": path,
            "anchors": anchors,
            "requirements": context["requirements"],
            "scheme_elements": context["scheme_elements"],
            "relevant_scheme_elements": context["relevant_scheme_elements"],
            "missing_anchors": missing_root_anchors,
            "message": (
                "Changed UI file is missing root anchors it directly owns in file_plan: "
                f"{', '.join(missing_root_anchors)}."
            ),
        }
        _add_finding(warning, mode, warnings, blockers)
        return checked_entry, warnings, blockers

    relevant_scheme_set = set(context["relevant_scheme_elements"])
    if relevant_scheme_set and not (relevant_scheme_set & anchor_set):
        warning = {
            "code": "ui_anchor_not_linked_to_requirement_scheme_element",
            "path": path,
            "anchors": anchors,
            "requirements": context["requirements"],
            "scheme_elements": context["scheme_elements"],
            "relevant_scheme_elements": context["relevant_scheme_elements"],
            "message": "UI anchors exist but do not match any scheme element ids linked to the same requirement.",
        }
        warnings.append(warning)
    elif required_direct:
        checked_entry["anchor_link_scope"] = "direct_file_plan"

    return checked_entry, warnings, blockers


def _add_finding(
    finding: dict[str, Any],
    mode: str,
    warnings: list[dict[str, Any]],
    blockers: list[dict[str, Any]],
) -> None:
    if mode == "strict":
        blockers.append(finding)
    else:
        warnings.append(finding)
