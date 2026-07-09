from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.common import read_json, write_json

from prototype_pipeline.plan_validation.runner import find_default_proposal, find_default_validation_plan, validate_proposal
from prototype_pipeline.plan_validation.validation_checks import sanitize_validation_plan


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--proposal", type=Path)
    parser.add_argument("--validation-plan", type=Path)
    parser.add_argument("--write-file-plan", action="store_true")
    args = parser.parse_args()

    proposal_path = args.proposal or find_default_proposal(args.run)
    validation_plan_path = args.validation_plan or find_default_validation_plan(args.run)
    if not proposal_path.exists():
        result = {
            "status": "failed",
            "blockers": [{"code": "proposal_not_found", "path": str(proposal_path)}],
            "warnings": [],
        }
    else:
        proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
        validation_plan = read_json(validation_plan_path) if validation_plan_path and validation_plan_path.exists() else None
        result = validate_proposal(args.run, proposal, validation_plan=validation_plan)

    out = args.run / "output" / "plan_validation_result.json"
    write_json(out, result)
    if args.write_file_plan and result.get("status") == "passed":
        _write_promoted_plans(args.run, result, validation_plan_path)
    print(f"Plan validation {result['status']}")
    if result.get("status") != "passed":
        _print_failure_details(result)
        raise SystemExit(1)


def _print_failure_details(result: dict) -> None:
    blockers = result.get("blockers") or []
    warnings = result.get("warnings") or []
    dropped = result.get("dropped_validation_check_ids") or []
    if blockers:
        print("Plan validation blockers:")
        for item in blockers:
            print(f"- {_format_issue(item)}")
    if warnings:
        print("Plan validation warnings:")
        for item in warnings[:20]:
            print(f"- {_format_issue(item)}")
        if len(warnings) > 20:
            print(f"- ... {len(warnings) - 20} more warning(s)")
    if dropped:
        print("Dropped validation checks:")
        for check_id in dropped:
            print(f"- {check_id}")


def _format_issue(item: dict) -> str:
    code = item.get("code") or "issue"
    message = item.get("message") or ""
    fields = []
    for key in ["path", "field", "artifact_type", "scheme_element_id", "validation_check_id"]:
        value = item.get(key)
        if value is not None:
            fields.append(f"{key}={value}")
    if "scheme_element_ids" in item:
        fields.append(f"scheme_element_ids={item.get('scheme_element_ids')}")
    suffix = f" ({', '.join(fields)})" if fields else ""
    return f"{code}: {message}{suffix}"


def _write_promoted_plans(run: Path, result: dict, validation_plan_path: Path | None) -> None:
    file_plan = result["normalized_file_plan"]
    write_json(run / "input" / "file_plan.json", file_plan)
    workspace_input = run / "workspace" / "prototype" / "input"
    if workspace_input.exists():
        write_json(workspace_input / "file_plan.json", file_plan)
    if validation_plan_path and validation_plan_path.exists():
        validation_plan = read_json(validation_plan_path)
        dropped = set(result.get("dropped_validation_check_ids", []))
        validation_plan = sanitize_validation_plan(validation_plan, dropped)
        write_json(run / "input" / "validation_plan.json", validation_plan)
        if workspace_input.exists():
            write_json(workspace_input / "validation_plan.json", validation_plan)


if __name__ == "__main__":
    main()
