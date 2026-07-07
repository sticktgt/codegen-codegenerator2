from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def _rm(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def _empty_dir(path: Path) -> None:
    if path.exists():
        _rm(path)
    path.mkdir(parents=True, exist_ok=True)


def _run_git(workspace: Path, args: list[str], *, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=workspace, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check)


def _last_commit_subject(workspace: Path) -> str | None:
    result = _run_git(workspace, ["log", "-1", "--pretty=%s"])
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _reset_workspace(workspace: Path, *, drop_approved_plan_commit: bool) -> list[str]:
    actions: list[str] = []
    if not (workspace / ".git").exists():
        actions.append("workspace_git_missing")
        return actions

    if drop_approved_plan_commit and _last_commit_subject(workspace) == "approved plan input artifacts":
        result = _run_git(workspace, ["reset", "--hard", "HEAD~1"])
        actions.append("git_reset_hard_head_minus_1" if result.returncode == 0 else "git_reset_hard_head_minus_1_failed")
    else:
        result = _run_git(workspace, ["reset", "--hard", "HEAD"])
        actions.append("git_reset_hard_head" if result.returncode == 0 else "git_reset_hard_head_failed")

    # Remove untracked non-ignored files created by previous failed runs.
    result = _run_git(workspace, ["clean", "-fd", "--", "."])
    actions.append("git_clean_fd" if result.returncode == 0 else "git_clean_fd_failed")
    return actions


def clean_run(
    run: Path,
    *,
    reset_workspace: bool,
    drop_approved_plan_commit: bool,
    drop_plan_inputs: bool,
    clean_root_prototype_output: bool,
) -> dict:
    run = run.resolve()
    root = Path(__file__).resolve().parents[1]
    workspace = run / "workspace"
    actions: list[str] = []

    if reset_workspace and workspace.exists():
        actions.extend(_reset_workspace(workspace, drop_approved_plan_commit=drop_approved_plan_commit))

    for name in ["output", "logs", "usage", "agent_reports", "dist"]:
        _empty_dir(run / name)
        actions.append(f"reset_run_{name}")

    # OpenCode writes agent reports here. It must be clean before a fresh phase.
    prototype_output = workspace / "prototype" / "output"
    if workspace.exists():
        _empty_dir(prototype_output)
        (prototype_output / ".gitkeep").touch()
        actions.append("reset_workspace_prototype_output")

        # Remove common runtime artifacts that should not affect planning.
        for rel in [
            ".venv",
            "frontend/node_modules",
            "frontend/dist",
            "dist",
            "backend/.pytest_cache",
            ".pytest_cache",
            "frontend/package-lock.json",
            "frontend/playwright-report",
            "frontend/test-results",
            "frontend/.playwright",
            "playwright-report",
            "test-results",
            ".playwright",
        ]:
            path = workspace / rel
            if path.exists():
                _rm(path)
                actions.append(f"remove_workspace_{rel}")

        # git clean -fd intentionally leaves ignored files behind. Remove Python
        # runtime cache explicitly so OpenCode does not inspect stale __pycache__
        # directories during planning or implementation.
        for cache_dir in sorted(workspace.rglob("__pycache__")):
            if cache_dir.is_dir():
                _rm(cache_dir)
                actions.append(f"remove_workspace_{cache_dir.relative_to(workspace)}")
        for pattern in ["*.pyc", "*.pyo"]:
            for cache_file in sorted(workspace.rglob(pattern)):
                if cache_file.is_file():
                    _rm(cache_file)
                    actions.append(f"remove_workspace_{cache_file.relative_to(workspace)}")

        if drop_plan_inputs:
            for rel in [
                "prototype/input/file_plan.json",
                "prototype/input/validation_plan.json",
            ]:
                path = workspace / rel
                if path.exists():
                    path.unlink()
                    actions.append(f"remove_workspace_{rel}")

    if drop_plan_inputs:
        for rel in ["input/file_plan.json", "input/validation_plan.json"]:
            path = run / rel
            if path.exists():
                path.unlink()
                actions.append(f"remove_run_{rel}")

    # Defensive cleanup for stale artifacts accidentally written at project root
    # by manual OpenCode runs. This is opt-in because it is outside the run dir.
    if clean_root_prototype_output:
        root_proto_out = root / "prototype" / "output"
        if root_proto_out.exists():
            _empty_dir(root_proto_out)
            actions.append("reset_root_prototype_output")

    result = {
        "run": str(run),
        "workspace": str(workspace),
        "actions": actions,
        "reset_workspace": reset_workspace,
        "drop_approved_plan_commit": drop_approved_plan_commit,
        "drop_plan_inputs": drop_plan_inputs,
        "clean_root_prototype_output": clean_root_prototype_output,
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean run output/log/usage artifacts before rerunning the pipeline.")
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--no-reset-workspace", action="store_true", help="Do not git reset/clean the run workspace")
    parser.add_argument("--keep-approved-plan-commit", action="store_true", help="Do not roll back the auto-created approved plan commit")
    parser.add_argument("--keep-plan-inputs", action="store_true", help="Keep file_plan.json and validation_plan.json")
    parser.add_argument("--clean-root-prototype-output", action="store_true", help="Also clear ./prototype/output at project root if it exists")
    args = parser.parse_args()

    result = clean_run(
        args.run,
        reset_workspace=not args.no_reset_workspace,
        drop_approved_plan_commit=not args.keep_approved_plan_commit,
        drop_plan_inputs=not args.keep_plan_inputs,
        clean_root_prototype_output=args.clean_root_prototype_output,
    )
    for action in result["actions"]:
        print(action)


if __name__ == "__main__":
    main()
