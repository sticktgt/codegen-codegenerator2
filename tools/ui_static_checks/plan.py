from __future__ import annotations

from pathlib import Path
from typing import Any

from common import read_json, read_yaml


def load_contract(run: Path) -> dict[str, Any]:
    for path in [
        run / "input" / "architecture-contract.yaml",
        run / "workspace" / "prototype" / "input" / "architecture-contract.yaml",
    ]:
        if path.exists():
            data = read_yaml(path)
            return data if isinstance(data, dict) else {}
    return {}


def changed_files(run: Path) -> set[str]:
    path = run / "output" / "changed_files.json"
    if not path.exists():
        return set()
    data = read_json(path)
    return set(data.get("changed_files") or [])


def file_plan_items(run: Path) -> list[dict[str, Any]]:
    path = run / "input" / "file_plan.json"
    if not path.exists():
        path = run / "workspace" / "prototype" / "input" / "file_plan.json"
    if not path.exists():
        return []
    data = read_json(path)
    return data.get("allowed_files") or []


def scheme_elements(item: dict[str, Any]) -> list[str]:
    values = list(item.get("scheme_elements") or [])
    if item.get("scheme_element_id"):
        values.append(item["scheme_element_id"])
    return [str(value) for value in values if value]


def requirements(item: dict[str, Any]) -> list[str]:
    values = list(item.get("requirements") or item.get("requirement_ids") or [])
    if item.get("requirement_id"):
        values.append(item["requirement_id"])
    return [str(value) for value in values if value]


def group_plan_items_by_path(items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_path: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        path = item.get("path")
        if path:
            by_path.setdefault(str(path), []).append(item)
    return by_path


def requirement_scheme_index(items: list[dict[str, Any]]) -> dict[str, set[str]]:
    by_requirement: dict[str, set[str]] = {}
    for item in items:
        item_schemes = set(scheme_elements(item))
        for requirement in requirements(item):
            by_requirement.setdefault(requirement, set()).update(item_schemes)
    return by_requirement
