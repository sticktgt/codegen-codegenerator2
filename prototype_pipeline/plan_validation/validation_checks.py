from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.common import read_json

from prototype_pipeline.plan_validation.contract import (
    capability_for_check,
    infer_artifact_type,
    taskfile_runs_frontend_behavior_tests,
    taskfile_runs_frontend_tests,
)
from prototype_pipeline.plan_validation.utils import as_list


def extract_validation_file_entries(
    validation_plan: dict[str, Any],
    workspace: Path,
    contract: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], set[str]]:
    """Promote explicit agent-proposed validation files into the file plan."""
    entries: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    dropped_check_ids: set[str] = set()
    checks = validation_plan.get("checks") or validation_plan.get("validation_checks") or []

    frontend_test_supported = _frontend_test_supported(workspace)
    for check in checks:
        if not isinstance(check, dict):
            continue
        proposed_file = check.get("proposed_file")
        check_type = str(check.get("type") or "").lower()
        capability = capability_for_check(check_type, contract)
        capability_enabled = True if capability is None else bool(capability.get("enabled", True))
        if not proposed_file:
            _warn_for_non_executable_check(check, check_type, warnings)
            continue
        path = str(proposed_file).replace("\\", "/")
        smoke_warning = _coerce_smoke_test_to_read_only(check, path)
        if smoke_warning:
            warnings.append(smoke_warning)
        if not capability_enabled:
            dropped_check_ids.add(str(check.get("id")))
            warnings.append({
                "code": "dropped_unsupported_validation_check",
                "path": path,
                "check_id": check.get("id"),
                "check_type": check.get("type"),
                "message": capability.get("reason") if capability else "The architecture contract says this validation capability is disabled.",
            })
            continue
        if path.startswith("frontend/") and not _frontend_validation_supported(workspace, capability, frontend_test_supported):
            dropped_check_ids.add(str(check.get("id")))
            warnings.append({
                "code": "dropped_unsupported_frontend_validation_file",
                "path": path,
                "check_id": check.get("id"),
                "check_type": check.get("type"),
                "message": _frontend_validation_message(capability),
            })
            continue
        entries.append(_entry_for_check(check, path, workspace, contract, capability))
    return entries, blockers, warnings, dropped_check_ids


def sanitize_validation_plan(validation_plan: dict[str, Any], dropped_check_ids: set[str]) -> dict[str, Any]:
    if not dropped_check_ids:
        return validation_plan
    sanitized = dict(validation_plan)
    checks = validation_plan.get("checks") or validation_plan.get("validation_checks") or []
    kept = []
    dropped = []
    for check in checks:
        if isinstance(check, dict) and str(check.get("id")) in dropped_check_ids:
            item = dict(check)
            item["status"] = "dropped"
            dropped.append(item)
        else:
            kept.append(check)
    if "checks" in validation_plan:
        sanitized["checks"] = kept
    else:
        sanitized["validation_checks"] = kept
    sanitized["dropped_checks"] = dropped
    return sanitized


def validation_scheme_element_ids(validation_plan: dict[str, Any] | None) -> set[str]:
    if not validation_plan:
        return set()
    result: set[str] = set()
    for check in validation_plan.get("checks") or validation_plan.get("validation_checks") or []:
        if not isinstance(check, dict):
            continue
        for key in ("scheme_element_id", "scheme_element_ids", "scheme_elements"):
            for value in as_list(check.get(key)):
                if value:
                    result.add(str(value))
    return result


def _frontend_test_supported(workspace: Path) -> bool:
    frontend_package = workspace / "frontend" / "package.json"
    if not frontend_package.exists():
        return False
    try:
        package_json = read_json(frontend_package)
        scripts = package_json.get("scripts", {}) or {}
        return bool(scripts.get("test")) and taskfile_runs_frontend_tests(workspace)
    except Exception:
        return False


def _frontend_validation_supported(workspace: Path, capability: dict[str, Any] | None, frontend_unit_supported: bool) -> bool:
    if not capability:
        return frontend_unit_supported
    artifact_type = str(capability.get("artifact_type") or "")
    if artifact_type == "frontend_behavior_test":
        markers = [str(item) for item in capability.get("required_taskfile_markers") or []]
        return taskfile_runs_frontend_behavior_tests(workspace, markers)
    return frontend_unit_supported


def _frontend_validation_message(capability: dict[str, Any] | None) -> str:
    if capability and capability.get("artifact_type") == "frontend_behavior_test":
        return (
            "A browser/e2e UI behavior test file was proposed, but this kit does not expose "
            "an executable frontend behavior validation task. Enable the frontend_behavior capability "
            "only together with a Taskfile/package runner such as npm run test:e2e or npx playwright test."
        )
    return (
        "A frontend validation file was proposed, but this lightweight kit has no executable frontend "
        "test script configured. The check will be dropped from validation_plan.json."
    )


def _warn_for_non_executable_check(check: dict[str, Any], check_type: str, warnings: list[dict[str, Any]]) -> None:
    if check_type not in {"api", "service", "unit", "integration", "e2e", "browser_e2e", "ui_behavior", "ui_unit", "component"}:
        return
    warnings.append({
        "code": "non_executable_validation_check",
        "check_id": check.get("id"),
        "check_type": check.get("type"),
        "requirement_id": check.get("requirement_id"),
        "scheme_element_id": check.get("scheme_element_id"),
        "message": "Functional validation checks need an explicit proposed_file to be executable by this pipeline.",
    })



def _coerce_smoke_test_to_read_only(check: dict[str, Any], path: str) -> dict[str, Any] | None:
    """Keep baseline smoke tests read-only even when planner intent is too broad.

    Smoke tests are baseline import/health checks. They are useful as rerun
    coverage, but a feature slice should not mutate ``backend/tests/test_smoke.py``
    or hide feature API assertions there. Rather than fail an otherwise safe plan,
    coerce the smoke check to read-only rerun coverage and emit a warning. Feature
    behavior remains covered by the feature API/e2e checks that the coverage guard
    already requires.
    """
    normalized = path.replace("\\", "/")
    if not normalized.endswith("/test_smoke.py") and normalized != "backend/tests/test_smoke.py":
        return None
    intent = str(check.get("validation_intent") or check.get("intent") or "").strip().lower()
    if intent and intent != "rerun_existing":
        check["validation_intent"] = "rerun_existing"
        check["intent"] = "rerun_existing"
        return {
            "code": "smoke_test_coerced_to_read_only",
            "path": normalized,
            "check_id": check.get("id"),
            "original_validation_intent": intent,
            "message": (
                "Smoke tests are baseline import/health checks and were coerced to read-only rerun coverage. "
                "Put feature API behavior in a planned feature test such as backend/tests/test_<feature>_api.py."
            ),
        }
    return None

def _entry_for_check(
    check: dict[str, Any],
    path: str,
    workspace: Path,
    contract: dict[str, Any],
    capability: dict[str, Any] | None,
) -> dict[str, Any]:
    artifact_type = check.get("artifact_type") or (capability or {}).get("artifact_type")
    if artifact_type == "none":
        artifact_type = None
    if not artifact_type:
        artifact_type, _ = infer_artifact_type(path, contract)
    policy, operation, validation_intent = _policy_for_validation_check(check, path, workspace)
    return {
        "path": path,
        "policy": policy,
        "operation": operation,
        "kind": "validation_test",
        "artifact_type": artifact_type,
        "requirement_id": check.get("requirement_id"),
        "requirements": check.get("requirements") or as_list(check.get("requirement_id")),
        "scheme_element_id": check.get("scheme_element_id"),
        "reason": check.get("description") or f"Validation check {check.get('id')}",
        "validation_check_id": check.get("id"),
        "validation_check_type": check.get("type"),
        "validation_intent": validation_intent,
        "executable_validation": True,
    }


def _policy_for_validation_check(check: dict[str, Any], path: str, workspace: Path) -> tuple[str, str, str]:
    """Map planner-declared validation intent to a file policy.

    The planner owns the validation intent. The validator only turns that intent
    into a boundary contract: rerun existing tests are read-only, while explicit
    extend/create intents may write test files.
    """
    intent = str(check.get("validation_intent") or check.get("intent") or "").strip().lower()
    exists = (workspace / path).exists()

    if intent == "rerun_existing":
        return "read_only", "read", intent
    if intent == "extend_existing_test":
        return ("may_modify", "modify", intent) if exists else ("must_create", "create", intent)
    if intent == "create_new_test":
        return ("must_create", "create", intent) if not exists else ("may_modify", "modify", intent)
    if intent == "rerun_behavior_test":
        return "read_only", "read", intent
    if intent == "extend_behavior_test":
        return ("may_modify", "modify", intent) if exists else ("must_create", "create", intent)
    if intent == "create_behavior_test":
        return ("must_create", "create", intent) if not exists else ("may_modify", "modify", intent)

    # Backwards-compatible default for older planner outputs.
    policy = "may_modify" if exists else "must_create"
    return policy, "modify" if policy == "may_modify" else "create", "unspecified"
