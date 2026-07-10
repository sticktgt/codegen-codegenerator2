from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tools.common import read_json

from prototype_pipeline.events import PipelineLogger, call
from prototype_pipeline.phases.baseline import commit_plan_inputs, commit_synced_kit_inputs
from prototype_pipeline.phases.clean import clean_run
from prototype_pipeline.phases.opencode import OpenCodeOptions, phase_args as opencode_phase_args
from prototype_pipeline.phases.reports import copy_workspace_report_if_exists
from prototype_pipeline.phases.repair_context import write_repair_context
from prototype_pipeline.phases.prompt_sync import sync_prompt_snapshots
from prototype_pipeline.phases.status import (
    boundary_failed as is_boundary_failed,
    ensure_validation_placeholder,
    review_has_blocker,
    ui_check_args,
    ui_static_failed as is_ui_static_failed,
)
from prototype_pipeline.phases.sync_inputs import sync_run_inputs
from prototype_pipeline.summary import summarize



def log_final_status_details(logger: PipelineLogger, summary: dict[str, object]) -> None:
    traceability_incomplete = summary.get("traceability_incomplete") or []
    if traceability_incomplete:
        logger.log(f"Traceability coverage incomplete: {len(traceability_incomplete)} requirement item(s)")
        for item in traceability_incomplete[:10]:
            if isinstance(item, dict):
                logger.log(
                    "Traceability gap: "
                    f"{item.get('requirement_id')} [{item.get('role')}] -> {item.get('status')}"
                )
    validation = summary.get("validation") or {}
    if isinstance(validation, dict) and validation.get("status") not in {None, "passed", "not_run"}:
        logger.log(f"Validation status: {validation.get('status')}")
    boundary = summary.get("boundary") or {}
    if isinstance(boundary, dict) and boundary.get("status") == "failed":
        logger.log(
            "File boundary failed: "
            f"unexpected={len(boundary.get('unexpected_files') or [])}, "
            f"policy_violations={len(boundary.get('policy_violations') or [])}, "
            f"missing_required_files={len(boundary.get('missing_required_files') or [])}, "
            f"missing_required_changes={len(boundary.get('missing_required_changes') or [])}"
        )
    ui_static = summary.get("ui_static") or {}
    if isinstance(ui_static, dict) and ui_static.get("status") == "failed":
        logger.log(
            "UI static checks failed: "
            f"blockers={len(ui_static.get('blockers') or [])}, "
            f"warnings={len(ui_static.get('warnings') or [])}"
        )


def fail_if_missing_workspace_or_run_input(run: Path, logger: PipelineLogger | None = None) -> None:
    workspace = run / "workspace"
    if not workspace.exists():
        message = (
            f"Run workspace does not exist: {workspace}. "
            "Prepare the run first, preferably with tools/prepare_run_from_scenario.py."
        )
        if logger:
            logger.log(message)
        raise SystemExit(message)

    run_input = workspace / "prototype" / "input" / "run_input.json"
    if not run_input.exists():
        message = (
            f"Canonical run input is missing: {run_input}. "
            "Use tools/prepare_run_from_scenario.py with a sample run_input.json, "
            "or add run_input.json to the sample before using tools/prepare_workspace.py."
        )
        if logger:
            logger.log(message)
        raise SystemExit(message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--plan-prompt-file", type=Path)
    parser.add_argument("--review-prompt-file", type=Path)
    parser.add_argument("--implementation-prompt-file", type=Path)
    parser.add_argument("--repair-prompt-file", type=Path)
    parser.add_argument("--allow-repair", action="store_true")
    parser.add_argument("--max-repair-attempts", type=int, default=2, help="Maximum OpenCode repair attempts when --allow-repair is enabled")
    parser.add_argument("--skip-validation", action="store_true")
    parser.add_argument("--no-stream", action="store_true", help="Do not mirror OpenCode logs while phases are running")
    parser.add_argument("--model", help="Explicit OpenCode model for all OpenCode phases, e.g. ollama-cloud/qwen3-coder-next")
    parser.add_argument("--kit", type=Path, help="Optional kit directory used to synchronize architecture contract and kit inputs into an existing run")
    parser.add_argument("--clean", action="store_true", help="Clean run logs/output/usage/artifacts and reset workspace before running")
    parser.add_argument("--clean-root-prototype-output", action="store_true", help="With --clean, also clear stale ./prototype/output artifacts at project root")
    parser.add_argument("--keep-plan-inputs", action="store_true", help="With --clean, keep existing file_plan.json and validation_plan.json")
    parser.add_argument("--skip-review", action="store_true", help="Skip separate OpenCode plan-review phase even when a review prompt is supplied")
    parser.add_argument("--fail-on-workspace-leak", action="store_true", help="Fail OpenCode phases when logs show reads/globs of project files outside the active workspace")
    parser.add_argument("--strict-ui-checks", action="store_true", help="Treat UI static check blockers, such as missing required UI anchors, as repairable failures")
    parser.add_argument("--sync-prompts", action="store_true", help="Refresh run prompt snapshot files from the selected kit before OpenCode phases")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    py = sys.executable
    if args.clean:
        clean_run(
            root=root,
            py=py,
            run=args.run,
            clean_root_prototype_output=args.clean_root_prototype_output,
            keep_plan_inputs=args.keep_plan_inputs,
        )

    logger = PipelineLogger(args.run)
    fail_if_missing_workspace_or_run_input(args.run, logger)

    # Existing runs can predate newer kit-level inputs such as architecture-contract.yaml.
    # Synchronize them before OpenCode sees the workspace so prompts, validators, and
    # reports use the same contract. This is metadata sync, not feature/file generation.
    sync_run_inputs(root=root, py=py, run=args.run, kit=args.kit)
    fail_if_missing_workspace_or_run_input(args.run, logger)
    prompt_sync_result = sync_prompt_snapshots(
        root=root,
        run=args.run,
        kit=args.kit,
        prompt_files={
            "plan": args.plan_prompt_file,
            "plan-review": args.review_prompt_file,
            "implementation": args.implementation_prompt_file,
            "repair": args.repair_prompt_file,
        },
        sync=args.sync_prompts,
    )
    synced_count = len([item for item in prompt_sync_result.get("prompts", []) if item.get("status") == "synced"])
    stale_count = len([item for item in prompt_sync_result.get("prompts", []) if item.get("status") == "stale"])
    external_count = len([item for item in prompt_sync_result.get("prompts", []) if item.get("status") == "external_override"])
    if synced_count or stale_count or external_count:
        logger.log(f"Prompt snapshots: synced={synced_count}, stale={stale_count}, external_overrides={external_count}")
    commit_synced_kit_inputs(args.run, logger)

    opencode_options = OpenCodeOptions(
        run=args.run,
        model=args.model,
        no_stream=args.no_stream,
        fail_on_workspace_leak=args.fail_on_workspace_leak,
    )

    def phase_args(phase: str, prompt_file: Path) -> list[str]:
        return opencode_phase_args(py, phase, prompt_file, opencode_options)

    try:
        if args.plan_prompt_file:
            call(phase_args("plan", args.plan_prompt_file), root=root, logger=logger, label="OpenCode plan")
            call([py, "tools/collect_agent_reports.py", "--run", str(args.run)], root=root, logger=logger, label="Collect plan reports")
            copy_workspace_report_if_exists(args.run, "plan_proposal.json")
            call([py, "tools/validate_plan.py", "--run", str(args.run), "--write-file-plan"], root=root, logger=logger, label="Validate plan")
            commit_plan_inputs(args.run, logger)
            plan_result = read_json(args.run / "output" / "plan_validation_result.json")
            if plan_result.get("status") != "passed":
                summary = summarize(args.run)
                logger.log(f"Pipeline failed: plan validation did not pass. See {args.run / 'output' / 'run_report.md'}")
                raise SystemExit(1)

        if args.review_prompt_file and not args.skip_review:
            call(phase_args("plan-review", args.review_prompt_file), root=root, logger=logger, label="OpenCode plan review")
            call([py, "tools/collect_agent_reports.py", "--run", str(args.run)], root=root, logger=logger, label="Collect review reports")
            copy_workspace_report_if_exists(args.run, "plan_review.json")
            if review_has_blocker(args.run):
                summarize(args.run)
                logger.log("Pipeline failed: plan review has blockers")
                raise SystemExit(1)

        if args.implementation_prompt_file:
            call(phase_args("implementation", args.implementation_prompt_file), root=root, logger=logger, label="OpenCode implementation")
            call([py, "tools/collect_agent_reports.py", "--run", str(args.run)], root=root, logger=logger, label="Collect implementation reports")

        call([py, "tools/collect_changes.py", "--run", str(args.run)], root=root, logger=logger, label="Collect changes")
        call(ui_check_args(py, args.run, args.strict_ui_checks), root=root, logger=logger, label="Run UI static checks", required=False)

        def run_diagnostics_validation(label: str) -> None:
            if args.skip_validation:
                ensure_validation_placeholder(args.run, "validation_skipped")
                return
            call([py, "tools/run_validation.py", "--run", str(args.run)], root=root, logger=logger, label=label, required=False)

        def current_failures() -> tuple[bool, bool, bool]:
            boundary = is_boundary_failed(args.run)
            ui_static = is_ui_static_failed(args.run)
            validation_path = args.run / "output" / "validation_result.json"
            validation_data = read_json(validation_path) if validation_path.exists() else {"status": "not_run"}
            validation = validation_data.get("status") == "failed"
            return boundary, ui_static, validation

        # Always collect validation diagnostics before entering repair. If boundary
        # or ui_static already failed, validation is still useful context for repair;
        # it is allowed to fail and post-repair validation remains the source of truth.
        boundary_has_failed = is_boundary_failed(args.run)
        ui_static_has_failed = is_ui_static_failed(args.run)
        if boundary_has_failed:
            logger.log("File boundary failed after implementation")
        if ui_static_has_failed:
            logger.log("UI static checks failed after implementation")
        run_diagnostics_validation("Run validation before repair" if (boundary_has_failed or ui_static_has_failed) else "Run validation")

        repair_attempts = max(0, int(args.max_repair_attempts or 0)) if args.allow_repair else 0
        for attempt in range(1, repair_attempts + 1):
            boundary_has_failed, ui_static_has_failed, validation_has_failed = current_failures()
            if not (boundary_has_failed or ui_static_has_failed or validation_has_failed):
                break
            if not args.repair_prompt_file:
                break
            label = f"repair-{attempt:03d}"
            repair_context_path = write_repair_context(args.run, attempt=attempt, max_attempts=repair_attempts)
            logger.log(f"Repair context: {repair_context_path}")
            call(phase_args(label, args.repair_prompt_file), root=root, logger=logger, label=f"OpenCode {label}")
            call([py, "tools/collect_agent_reports.py", "--run", str(args.run)], root=root, logger=logger, label=f"Collect {label} reports")
            call([py, "tools/collect_changes.py", "--run", str(args.run)], root=root, logger=logger, label=f"Collect changes after {label}")
            call(ui_check_args(py, args.run, args.strict_ui_checks), root=root, logger=logger, label=f"Run UI static checks after {label}", required=False)
            run_diagnostics_validation(f"Run validation after {label}")

        call([py, "tools/build_code_traceability.py", "--run", str(args.run)], root=root, logger=logger, label="Build traceability")
        call([py, "tools/collect_agent_reports.py", "--run", str(args.run)], root=root, logger=logger, label="Collect final agent reports")
        call([py, "tools/export_artifact.py", "--run", str(args.run)], root=root, logger=logger, label="Export artifact")
        # Write report/summary before diagnostics export so they are included in the bundle.
        summarize(args.run)
        call([py, "tools/export_run_bundle.py", "--run", str(args.run)], root=root, logger=logger, label="Export run diagnostics")
        summary = summarize(args.run)
        logger.log(f"Pipeline summary: {args.run / 'output' / 'run_summary.json'}")
        logger.log(f"Scenario result: {args.run / 'output' / 'scenario_result.json'}")
        logger.log(f"Pipeline report: {args.run / 'output' / 'run_report.md'}")
        logger.log(f"Run diagnostics archive: {args.run / 'dist' / 'run_diagnostics.zip'}")
        if summary.get("final_status") != "passed":
            log_final_status_details(logger, summary)
            logger.log(f"Pipeline final status: {summary.get('final_status')}")
            raise SystemExit(1)
        logger.log(f"Pipeline final status: {summary.get('final_status')}")
    finally:
        # Always leave the latest summary/report if enough artifacts exist.
        try:
            summarize(args.run)
        except Exception:
            pass


if __name__ == "__main__":
    main()
