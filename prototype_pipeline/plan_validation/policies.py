from __future__ import annotations

from typing import Any

from prototype_pipeline.plan_validation.utils import as_list

WRITE_POLICIES = {
    "must_create",
    "may_modify",
    "modify_allowed",
    "allowed_change",
    "must_modify",
    "may_write",
    "create",
    "modify",
}
READ_ONLY_POLICIES = {"no_change", "may_read", "read_only", "read"}
POLICY_TO_OPERATION = {
    "must_create": "create",
    "create": "create",
    "must_modify": "modify",
    "may_modify": "modify",
    "modify_allowed": "modify",
    "allowed_change": "modify",
    "modify": "modify",
    "may_write": "modify",
    "may_read": "read",
    "read": "read",
    "read_only": "read",
    "no_change": "read",
}


def normalize_policy(policy: str) -> str:
    if policy == "create":
        return "must_create"
    if policy == "modify":
        return "may_modify"
    if policy == "read":
        return "read_only"
    return policy


def operation_for(policy: str, entry: dict[str, Any]) -> str:
    return str(entry.get("operation") or POLICY_TO_OPERATION.get(policy) or "modify")


def normalize_entry(raw: Any, policy: str) -> dict[str, Any]:
    if isinstance(raw, str):
        return {"path": raw, "policy": policy}
    if not isinstance(raw, dict):
        return {"path": None, "policy": policy, "raw": raw}
    item = dict(raw)
    item.setdefault("policy", item.get("change_policy") or policy)
    return item


def extract_plan_entries(proposal: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract file entries from an agent-generated plan without inventing names."""
    draft = proposal.get("file_plan_draft") or proposal.get("file_plan") or {}
    entries: list[dict[str, Any]] = []
    buckets = [
        ("create", "must_create"),
        ("files_to_create", "must_create"),
        ("modify", "may_modify"),
        ("files_to_modify", "may_modify"),
        ("read", "may_read"),
        ("files_to_read", "may_read"),
        ("test_files_to_create", "must_create"),
        ("test_files_to_modify", "may_modify"),
    ]
    for key, policy in buckets:
        for raw in as_list(draft.get(key)) + as_list(proposal.get(key)):
            entries.append(normalize_entry(raw, policy))
    for raw in as_list(draft.get("allowed_files")) + as_list(proposal.get("allowed_files")):
        entries.append(normalize_entry(raw, "may_modify"))
    return entries
