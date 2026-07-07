from __future__ import annotations

from pathlib import Path

from tools.common import read_json, write_json


def ensure_validation_placeholder(run: Path, reason: str) -> None:
    """Create a placeholder validation_result for pre-validation repair.

    Boundary/UI repair can run before validation. Repair prompts read
    prototype/output/validation_result.json when present, so provide an explicit
    not_run record instead of forcing the agent to search for a missing file.
    """
    output = run / "output"
    output.mkdir(parents=True, exist_ok=True)
    path = output / "validation_result.json"
    if path.exists():
        return
    data = {
        "status": "not_run",
        "reason": reason,
        "task": None,
        "exit_code": None,
        "stdout_log": None,
        "stderr_log": None,
    }
    write_json(path, data)
    workspace_output = run / "workspace" / "prototype" / "output"
    workspace_output.mkdir(parents=True, exist_ok=True)
    write_json(workspace_output / "validation_result.json", data)


def ui_static_failed(run: Path) -> bool:
    path = run / "output" / "ui_static_check_result.json"
    if not path.exists():
        return False
    try:
        return read_json(path).get("status") == "failed"
    except Exception:
        return False


def ui_check_args(py: str, run: Path, strict: bool) -> list[str]:
    result = [py, "tools/run_ui_static_checks.py", "--run", str(run)]
    if strict:
        result.extend(["--mode", "strict"])
    return result


def boundary_failed(run: Path) -> bool:
    path = run / "output" / "changed_files.json"
    if not path.exists():
        return False
    changed = read_json(path)
    return bool(
        changed.get("boundary_status") == "failed"
        or changed.get("unexpected_files")
        or changed.get("policy_violations")
        or changed.get("missing_required_files")
        or changed.get("missing_required_changes")
    )


def review_has_blocker(run: Path) -> bool:
    for path in [
        run / "agent_reports" / "plan_review.json",
        run / "output" / "plan_review.json",
        run / "workspace" / "prototype" / "output" / "plan_review.json",
    ]:
        if not path.exists():
            continue
        review = read_json(path)
        return review.get("status") == "blocker" or bool(review.get("blockers"))
    return False
