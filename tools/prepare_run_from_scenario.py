from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path
from typing import Any

from common import read_json, run_cmd, write_json


CURRENT_PROTOTYPE_DEFAULTS = {
    "scheme_model_file": "scheme_model.json",
    "data_sources_file": "data_sources.json",
    "mock_plan_file": "mock_plan.json",
}


def _resolve(base: Path, value: str | None, *, label: str) -> Path:
    if not value:
        raise SystemExit(f"Missing {label} in run input")
    path = Path(value)
    return path if path.is_absolute() else base / path


def _copy_required(src: Path, dst: Path) -> None:
    if not src.exists():
        raise SystemExit(f"Required scenario input file does not exist: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _slice_to_implementation_slice(run_input: dict[str, Any]) -> dict[str, Any]:
    slice_data = run_input.get("slice")
    if not isinstance(slice_data, dict):
        raise SystemExit("run_input.json must contain object field: slice")

    requirement_ids = slice_data.get("requirement_ids") or slice_data.get("requirements")
    if not requirement_ids:
        raise SystemExit("run_input.json slice must include requirement_ids")

    result: dict[str, Any] = {
        "slice_id": slice_data.get("slice_id"),
        "title": slice_data.get("title"),
        "requirements": requirement_ids,
        "goal": slice_data.get("goal"),
        "change_type": slice_data.get("change_type"),
        "selected_existing_elements": slice_data.get("selected_existing_elements", []),
        "preserve_existing_behavior_by_default": slice_data.get("preserve_existing_behavior_by_default", True),
        "acceptance_criteria": slice_data.get("acceptance_criteria", []),
    }

    for optional_key in ["constraints", "notes", "non_goals", "assumptions"]:
        if optional_key in slice_data:
            result[optional_key] = slice_data[optional_key]

    missing = [key for key in ["slice_id", "title", "goal", "change_type"] if not result.get(key)]
    if missing:
        raise SystemExit(f"run_input.json slice is missing required fields: {', '.join(missing)}")
    if not result["acceptance_criteria"]:
        raise SystemExit("run_input.json slice must include acceptance_criteria")
    return result


def _materialize_sample(run_input_path: Path, sample_dir: Path, materialized_dir: Path) -> None:
    run_input = read_json(run_input_path)
    materialized_dir.mkdir(parents=True, exist_ok=True)

    requirements_file = run_input.get("requirements_file", "requirements.json")
    _copy_required(_resolve(sample_dir, requirements_file, label="requirements_file"), materialized_dir / "requirements.json")

    current_prototype = run_input.get("current_prototype") or {}
    if not isinstance(current_prototype, dict):
        raise SystemExit("run_input.json current_prototype must be an object when provided")

    for output_name, default_name in [
        ("scheme_model.json", CURRENT_PROTOTYPE_DEFAULTS["scheme_model_file"]),
        ("data_sources.json", CURRENT_PROTOTYPE_DEFAULTS["data_sources_file"]),
        ("mock_plan.json", CURRENT_PROTOTYPE_DEFAULTS["mock_plan_file"]),
    ]:
        key = output_name.replace(".json", "_file")
        source_name = current_prototype.get(key, default_name)
        _copy_required(_resolve(sample_dir, source_name, label=f"current_prototype.{key}"), materialized_dir / output_name)

    write_json(materialized_dir / "implementation_slice.json", _slice_to_implementation_slice(run_input))
    shutil.copy2(run_input_path, materialized_dir / "run_input.json")


def _run_or_exit(command: list[str], *, cwd: Path) -> None:
    result = run_cmd(command, cwd=cwd)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="")
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare a run from canonical run_input.json, materializing pipeline input files for the planner."
    )
    parser.add_argument("--scenario", required=True, type=Path, help="Path to run_input.json")
    parser.add_argument("--sample", type=Path, help="Directory for files referenced by run_input.json; defaults to scenario parent")
    parser.add_argument("--from-run", type=Path, help="Successful previous run to use as incremental baseline")
    parser.add_argument("--run", required=True, type=Path, help="New run directory")
    parser.add_argument("--kit", required=True, type=Path)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    scenario = args.scenario if args.scenario.is_absolute() else root / args.scenario
    sample_dir = args.sample if args.sample else scenario.parent
    if not sample_dir.is_absolute():
        sample_dir = root / sample_dir
    kit = args.kit if args.kit.is_absolute() else root / args.kit
    run = args.run if args.run.is_absolute() else root / args.run

    if not scenario.exists():
        raise SystemExit(f"Scenario file does not exist: {scenario}")
    if not kit.exists():
        raise SystemExit(f"Kit directory does not exist: {kit}")

    with tempfile.TemporaryDirectory(prefix="prototype-run-input-") as temp:
        materialized = Path(temp) / "sample"
        _materialize_sample(scenario, sample_dir, materialized)

        if args.from_run:
            from_run = args.from_run if args.from_run.is_absolute() else root / args.from_run
            command = [
                "python3",
                "tools/prepare_incremental_run.py",
                "--from-run",
                str(from_run),
                "--sample",
                str(materialized),
                "--run",
                str(run),
                "--kit",
                str(kit),
            ]
        else:
            command = [
                "python3",
                "tools/prepare_workspace.py",
                "--sample",
                str(materialized),
                "--run",
                str(run),
                "--kit",
                str(kit),
            ]
        _run_or_exit(command, cwd=root)

    print(f"Run prepared from scenario: {run}")
    print(f"Canonical run input copied to: {run / 'input' / 'run_input.json'}")


if __name__ == "__main__":
    main()
