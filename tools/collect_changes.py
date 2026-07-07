from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from common import read_json, run_cmd, write_json

WRITE_POLICIES = {"must_create", "may_modify", "modify_allowed", "allowed_change", "must_modify", "may_write", "create", "modify", "must_exist"}
READ_ONLY_POLICIES = {"no_change", "may_read", "read_only", "read"}
REQUIRED_POLICIES = {"must_create", "must_modify", "must_exist"}
REQUIRED_CHANGE_POLICIES = {"must_create", "must_modify"}


RUNTIME_ARTIFACT_PREFIXES = (
    "frontend/test-results/",
    "frontend/playwright-report/",
    "frontend/.playwright/",
    "test-results/",
    "playwright-report/",
)
RUNTIME_ARTIFACT_EXACT = {
    "frontend/.last-run.json",
}


def _is_runtime_artifact_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return normalized in RUNTIME_ARTIFACT_EXACT or any(
        normalized.startswith(prefix) for prefix in RUNTIME_ARTIFACT_PREFIXES
    )


def _load_allowed_plan(run: Path) -> tuple[dict[str, Any], dict[str, str], set[str], set[str]]:
    file_plan_path = run / "input" / "file_plan.json"
    if not file_plan_path.exists():
        raise SystemExit(f"Missing required file plan: {file_plan_path}")
    plan = read_json(file_plan_path)
    policies = {
        item["path"]: item.get("policy", "may_modify")
        for item in plan.get("allowed_files", [])
        if item.get("path")
    }
    writable = {path for path, policy in policies.items() if policy in WRITE_POLICIES}
    required = {path for path, policy in policies.items() if policy in REQUIRED_POLICIES}
    return plan, policies, writable, required


def _parse_status(stdout: str) -> tuple[set[str], set[str], set[str], set[str]]:
    created: set[str] = set()
    modified: set[str] = set()
    deleted: set[str] = set()
    renamed: set[str] = set()
    for line in stdout.splitlines():
        if not line:
            continue
        code = line[:2]
        path = line[3:]
        if " -> " in path:
            _old, new = path.split(" -> ", 1)
            renamed.add(new)
            modified.add(new)
            continue
        if code == "??":
            created.add(path)
        elif "D" in code:
            deleted.add(path)
        elif "A" in code:
            created.add(path)
        elif "M" in code or "T" in code:
            modified.add(path)
    return created, modified, deleted, renamed


HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def _parse_diff_hunks(diff_text: str) -> list[dict[str, Any]]:
    hunks: list[dict[str, Any]] = []
    current_file: str | None = None
    current_hunk: dict[str, Any] | None = None
    added_lines: list[str] = []
    removed_lines: list[str] = []

    def flush() -> None:
        nonlocal current_hunk, added_lines, removed_lines
        if current_file and current_hunk:
            current_hunk["added_preview"] = added_lines[:12]
            current_hunk["removed_preview"] = removed_lines[:12]
            hunks.append(current_hunk)
        current_hunk = None
        added_lines = []
        removed_lines = []

    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            flush()
            parts = line.split()
            if len(parts) >= 4:
                current_file = parts[3][2:] if parts[3].startswith("b/") else parts[3]
            continue
        match = HUNK_RE.match(line)
        if match:
            flush()
            old_start = int(match.group(1))
            old_lines = int(match.group(2) or "1")
            new_start = int(match.group(3))
            new_lines = int(match.group(4) or "1")
            current_hunk = {
                "file": current_file,
                "type": "diff_hunk",
                "old_start": old_start,
                "old_lines": old_lines,
                "new_start": new_start,
                "new_lines": new_lines,
            }
            continue
        if current_hunk:
            if line.startswith("+") and not line.startswith("+++"):
                added_lines.append(line[1:])
            elif line.startswith("-") and not line.startswith("---"):
                removed_lines.append(line[1:])
    flush()
    return [h for h in hunks if h.get("file")]


def _untracked_hunk(workspace: Path, path: str) -> dict[str, Any] | None:
    file_path = workspace / path
    if not file_path.exists() or not file_path.is_file():
        return None
    try:
        text = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {
            "file": path,
            "type": "new_binary_file",
            "old_start": 0,
            "old_lines": 0,
            "new_start": 1,
            "new_lines": 0,
            "added_preview": [],
            "removed_preview": [],
        }
    lines = text.splitlines()
    return {
        "file": path,
        "type": "new_file",
        "old_start": 0,
        "old_lines": 0,
        "new_start": 1,
        "new_lines": len(lines),
        "added_preview": lines[:12],
        "removed_preview": [],
    }


def _git_show_text(workspace: Path, path: str) -> str | None:
    result = subprocess.run(
        ["git", "show", f"HEAD:{path}"],
        cwd=workspace,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def _read_workspace_text(workspace: Path, path: str) -> str | None:
    file_path = workspace / path
    if not file_path.exists() or not file_path.is_file():
        return None
    try:
        return file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None


def _json_semantically_equal(before: str, after: str) -> bool:
    try:
        return json.loads(before) == json.loads(after)
    except Exception:
        return False


def _is_non_semantic_change(workspace: Path, path: str) -> tuple[bool, str | None]:
    """Classify harmless dirt on read-only/no-change files.

    This intentionally does not ignore arbitrary code whitespace changes. It only
    treats JSON-equivalent changes and final-newline-only/text-line-equivalent
    changes as non-semantic. These are reported as warnings, not blockers.
    """
    before = _git_show_text(workspace, path)
    after = _read_workspace_text(workspace, path)
    if before is None or after is None:
        return False, None
    if before == after:
        return True, "identical"
    if path.endswith(".json") and _json_semantically_equal(before, after):
        return True, "json_semantically_equal"
    if before.splitlines() == after.splitlines():
        return True, "line_equivalent_or_final_newline_only"
    return False, None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, type=Path)
    args = parser.parse_args()

    workspace = args.run / "workspace"
    _, policies, writable_paths, required_paths = _load_allowed_plan(args.run)
    all_planned_paths = set(policies)

    status = run_cmd(["git", "status", "--porcelain", "-uall"], cwd=workspace)
    diff_names = run_cmd(["git", "diff", "--name-only"], cwd=workspace)
    created, modified, deleted, renamed = _parse_status(status.stdout)

    changed = set(diff_names.stdout.splitlines()) | created | modified | deleted | renamed
    changed_paths = sorted(p for p in changed if p)

    non_semantic_changes: list[dict[str, Any]] = []
    runtime_mutated_files: list[dict[str, Any]] = []

    # Detect harmless tracked-file dirt and validation/runtime artifacts for all
    # changed paths, not only paths listed in the active file_plan. Browser test
    # runners can create traces, screenshots, and .last-run files after validation
    # failures. These artifacts must remain visible in reports, but they are not
    # implementation changes and must not fail the file boundary.
    non_semantic_paths: set[str] = set()
    runtime_artifact_paths: set[str] = set()
    for path in changed_paths:
        if _is_runtime_artifact_path(path):
            item = {
                "path": path,
                "policy": policies.get(path, "unplanned"),
                "reason": "runtime_artifact",
                "planned": path in all_planned_paths,
            }
            non_semantic_changes.append(item)
            runtime_mutated_files.append(item)
            non_semantic_paths.add(path)
            runtime_artifact_paths.add(path)
            continue
        non_semantic, reason = _is_non_semantic_change(workspace, path)
        if non_semantic:
            item = {
                "path": path,
                "policy": policies.get(path, "unplanned"),
                "reason": reason or "non_semantic_change",
                "planned": path in all_planned_paths,
            }
            non_semantic_changes.append(item)
            runtime_mutated_files.append(item)
            non_semantic_paths.add(path)

    unexpected = [
        p for p in changed_paths
        if p not in all_planned_paths and p not in non_semantic_paths
    ]
    policy_violations = [
        {
            "path": p,
            "policy": policies.get(p),
            "reason": "changed file is not writable by the active file_plan",
        }
        for p in changed_paths
        if p in all_planned_paths and p not in writable_paths and p not in non_semantic_paths
    ]
    missing = [p for p in sorted(required_paths) if not (workspace / p).exists()]

    missing_required_changes = []
    for path, policy in sorted(policies.items()):
        if policy not in REQUIRED_CHANGE_POLICIES:
            continue
        if policy == "must_create":
            if path not in created:
                missing_required_changes.append({
                    "path": path,
                    "policy": policy,
                    "reason": "file was required to be created by file_plan but was not created in this run",
                })
        elif policy == "must_modify":
            if path not in changed or path in non_semantic_paths:
                missing_required_changes.append({
                    "path": path,
                    "policy": policy,
                    "reason": "file was required to be modified by file_plan but has no semantic change in this run",
                })

    semantic_changed_paths = sorted(p for p in changed_paths if p not in non_semantic_paths)
    unchanged_allowed = sorted(p for p in all_planned_paths if p not in changed)

    diff = run_cmd(["git", "diff"], cwd=workspace)
    diff_hunks = _parse_diff_hunks(diff.stdout)
    tracked_hunk_files = {h["file"] for h in diff_hunks}
    for path in sorted(created):
        if path in runtime_artifact_paths:
            continue
        if path not in tracked_hunk_files:
            hunk = _untracked_hunk(workspace, path)
            if hunk:
                diff_hunks.append(hunk)

    # Runtime/non-semantic changes are warnings. They remain visible in the
    # report, but do not fail the file boundary on their own.
    boundary_status = "passed" if not unexpected and not missing and not policy_violations and not missing_required_changes else "failed"
    output = {
        "boundary_status": boundary_status,
        "changed_files": changed_paths,
        "semantic_changed_files": semantic_changed_paths,
        "created_files": sorted(created),
        "modified_files": sorted(modified),
        "deleted_files": sorted(deleted),
        "renamed_files": sorted(renamed),
        "unexpected_files": unexpected,
        "policy_violations": policy_violations,
        "missing_required_files": missing,
        "missing_required_changes": missing_required_changes,
        "unchanged_allowed_files": unchanged_allowed,
        "runtime_mutated_files": runtime_mutated_files,
        "non_semantic_changes": non_semantic_changes,
        "git_status": status.stdout,
        "diff_artifact": "output/workspace.diff",
        "diff_hunks": diff_hunks,
    }
    write_json(args.run / "output" / "changed_files.json", output)
    workspace_output = workspace / "prototype" / "output"
    if workspace_output.exists():
        write_json(workspace_output / "changed_files.json", output)
    (args.run / "output" / "workspace.diff").write_text(diff.stdout, encoding="utf-8")
    print(
        f"Changed files: {len(changed_paths)}; "
        f"unexpected: {len(unexpected)}; "
        f"policy_violations: {len(policy_violations)}; "
        f"missing_required_changes: {len(missing_required_changes)}; "
        f"non_semantic: {len(non_semantic_changes)}; "
        f"missing: {len(missing)}; "
        f"boundary: {boundary_status}"
    )


if __name__ == "__main__":
    main()
