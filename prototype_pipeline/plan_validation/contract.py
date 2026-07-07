from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from tools.common import read_json, read_yaml

DEFAULT_FORBIDDEN_EXACT = {
    "frontend/package.json",
    "frontend/package-lock.json",
    "backend/requirements.txt",
    "Taskfile.yml",
    "opencode.json",
    "AGENTS.md",
}
DEFAULT_FORBIDDEN_PREFIXES = (
    ".git/",
    "node_modules/",
    "frontend/node_modules/",
    ".venv/",
    "dist/",
    "frontend/dist/",
    "prototype/input/",
)
DEFAULT_ALLOWED_ROOTS = (
    "frontend/src/",
    "backend/app/",
    "backend/tests/",
)


def taskfile_runs_frontend_tests(workspace: Path) -> bool:
    taskfile = workspace / "Taskfile.yml"
    if not taskfile.exists():
        return False
    text = taskfile.read_text(encoding="utf-8", errors="ignore")
    return "npm test" in text or "npm run test" in text or "task: frontend-test" in text


def taskfile_runs_frontend_behavior_tests(workspace: Path, markers: list[str] | None = None) -> bool:
    taskfile = workspace / "Taskfile.yml"
    if not taskfile.exists():
        return False
    text = taskfile.read_text(encoding="utf-8", errors="ignore")
    candidates = markers or [
        "frontend-behavior",
        "npm run test:e2e",
        "npx playwright test",
        "npx cypress run",
    ]
    return any(marker and marker in text for marker in candidates)


def load_contract(workspace: Path) -> dict[str, Any]:
    path = workspace / "prototype" / "input" / "architecture-contract.yaml"
    if path.exists():
        data = read_yaml(path)
        if isinstance(data, dict):
            return data
    return {}


def contract_artifact_types(contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    types = contract.get("artifact_types") or {}
    return types if isinstance(types, dict) else {}


def contract_validation_capabilities(contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    caps = contract.get("validation_capabilities") or {}
    return caps if isinstance(caps, dict) else {}


def planner_output_contract(contract: dict[str, Any]) -> dict[str, Any]:
    spec = contract.get("planner_output") or {}
    return spec if isinstance(spec, dict) else {}


def all_allowed_roots(contract: dict[str, Any]) -> tuple[str, ...]:
    roots: list[str] = []
    for spec in contract_artifact_types(contract).values():
        for root in spec.get("allowed_roots") or []:
            root = str(root).replace("\\", "/")
            if root and root not in roots:
                roots.append(root)
    return tuple(roots or DEFAULT_ALLOWED_ROOTS)


def contract_forbidden(contract: dict[str, Any]) -> tuple[tuple[str, ...], set[str]]:
    policy = contract.get("path_policy") or {}
    prefixes = [str(item).replace("\\", "/") for item in (policy.get("forbidden_prefixes") or DEFAULT_FORBIDDEN_PREFIXES)]
    exact = {str(item).replace("\\", "/") for item in (policy.get("forbidden_exact") or DEFAULT_FORBIDDEN_EXACT)}
    return tuple(prefixes), exact


def template_to_regex(template: str) -> re.Pattern[str]:
    token = "__DOUBLE_STAR__"
    template = template.replace("\\", "/").replace("**", token)
    escaped = re.escape(template)
    escaped = escaped.replace(re.escape(token), ".*")
    escaped = re.sub(r"\\\{[^{}]+\\\}", r"[^/]+", escaped)
    return re.compile(r"^" + escaped + r"$")


def matches_template(path: str, template: str) -> bool:
    return bool(template_to_regex(template).match(path.replace("\\", "/")))


def artifact_matches_path(path: str, artifact_type: str, contract: dict[str, Any]) -> bool:
    spec = contract_artifact_types(contract).get(artifact_type) or {}
    roots = [str(root).replace("\\", "/") for root in spec.get("allowed_roots") or []]
    if roots and not any(path.startswith(root) for root in roots):
        return False
    templates = [str(template) for template in spec.get("path_templates") or []]
    if templates:
        return any(matches_template(path, template) for template in templates)
    return bool(roots)


def infer_artifact_type(path: str, contract: dict[str, Any]) -> tuple[str | None, list[str]]:
    exact_matches = []
    root_matches = []
    for name, spec in contract_artifact_types(contract).items():
        roots = [str(root).replace("\\", "/") for root in spec.get("allowed_roots") or []]
        if roots and any(path.startswith(root) for root in roots):
            root_matches.append(name)
        templates = [str(template) for template in spec.get("path_templates") or []]
        if templates and any(matches_template(path, template) for template in templates):
            exact_matches.append(name)
    candidates = exact_matches or root_matches
    if len(candidates) == 1:
        return candidates[0], candidates
    return None, candidates


def capability_for_check(check_type: str, contract: dict[str, Any]) -> dict[str, Any] | None:
    check_type = check_type.lower()
    for capability in contract_validation_capabilities(contract).values():
        types = [str(item).lower() for item in capability.get("executable_check_types") or []]
        if check_type in types:
            return capability
    return None


def load_rules(workspace: Path, contract: dict[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...], set[str]]:
    roots = all_allowed_roots(contract)
    forbidden_prefixes, forbidden_exact = contract_forbidden(contract)
    rules_path = workspace / "prototype" / "input" / "generation-rules.yaml"
    if rules_path.exists():
        rules = read_yaml(rules_path)
        for raw in rules.get("forbidden_paths", []) or []:
            raw = str(raw).replace("\\", "/")
            if raw.endswith("/"):
                forbidden_prefixes = tuple(sorted(set(forbidden_prefixes + (raw,))))
            else:
                forbidden_exact.add(raw)
    return roots, forbidden_prefixes, forbidden_exact
