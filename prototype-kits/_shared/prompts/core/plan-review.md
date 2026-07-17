MANDATORY OUTPUT CONTRACT:
- You must write `prototype/output/plan_review.json` before finishing this phase.
- A text summary in stdout is not sufficient.
- If the plan is safe, write status `pass` or `warning`; if unsafe, write status `blocker`.
- Do not end the response until `prototype/output/plan_review.json` has been written.

Review the proposed plan. Do not implement code.

- Do not use `todowrite` or `todoread`. Use `plan_review.json` as the structured phase output.

Read:
- prototype/output/plan_proposal.json
- prototype/output/validation_plan_proposal.json
- prototype/input/requirements.json
- prototype/input/scheme_model.json
- prototype/input/baseline_context/*.json, if present
- prototype/input/run_input.json, if present
- prototype/input/implementation_slice.json
- prototype/input/kit.yaml
- prototype/input/generation-rules.yaml
- prototype/input/architecture-contract.yaml
- instructions/core/architecture.md
- instructions/core/planning.md
- current workspace source files as needed

Canonical instruction paths:
- Runtime workspace copies live under `instructions/...` at the workspace root.
- Markdown instructions are available from the workspace-root `instructions/` tree.
- Use `prototype/input/...` only for JSON/YAML run inputs and machine-readable contracts.

Check:
- Does the plan cover the scenario/run input requirements and acceptance criteria?
- Does every file-plan row use an artifact type that matches its path and responsibility?
- If `run_input.json` is present, does the plan treat it as requirement intent rather than a file plan?
- Are proposed files and validation checks minimal and relevant?
- Does the plan derive affected existing elements and proposed new elements from the requirement intent rather than assuming they were predeclared by the analyst?
- Does the plan use canonical `design_delta` only, with no deprecated `scheme_delta` substitute?
- Does every scheme element referenced by file operations or validation checks appear in one of the accepted categories: current `scheme_model.json`, `design_delta.resolved_existing_elements`, or `design_delta.proposed_new_elements`?
- If an element is absent from the current scheme_model but present in baseline_context or discoverable in workspace code, is it classified as resolved existing with a baseline/workspace source rather than proposed as new?
- If the slice extends existing behavior, does the plan preserve existing accepted behavior by default?
- Does the plan avoid repurposing existing artifacts with stable responsibilities when a wrapper, UI state, or new artifact would be sufficient?
- If the plan modifies an existing artifact, does `design_delta.preservation_decisions` explain why reuse/wrapping is insufficient and what behavior remains preserved?
- For dedicated files, does `implementation_mode: "separate_artifact"` align with the proposed file plan?
- Does the plan avoid unnecessary dependencies, and are any proposed dependency/package changes explicitly allowed by the contract, included in the file plan, and justified?
- Are `must_modify` file-plan rows limited to files that truly need semantic changes? Warn if a file is marked `must_modify` only because it is related to the requirement, while the plan itself could satisfy the behavior in another file such as a model computed field.
- If the plan adds a response field, derived display field, query-supported field, or relationship field that must be serialized through a model/DTO/schema, is that owning model/DTO/schema file explicitly in the file plan? Warn or block if implementation would have to modify an unplanned response model file to pass validation.
- Compare validation checks with file-plan reasons. If validation checks list/detail/create/update/search/filter/UI refresh behavior, the planned model/service/API/frontend changes should cover the same operations or name a shared helper/mapper that covers them. Recommend plan improvement for vague or narrow wording. Use a blocker only when the mismatch makes the plan very likely to fail or requires editing files outside the approved plan.
- If formal plan validation already passed, do not block solely because design_delta metadata could be cleaner; warn and allow implementation when the file plan is safe.
- If formal plan validation warns that resolved existing elements are missing from the current scheme_model, treat this as a schema gap/update candidate, not as a blocker, when the file plan is safe and baseline/workspace evidence exists.

Review guidance:
- Before reporting a missing, forbidden, extra, or inconsistent field, verify the exact final JSON object. Do not report that a field is present when it is absent, and distinguish an omitted field from a field whose value is `null`.
- Prefer a working, safe implementation plan over blocking on planner-output metadata issues that do not change implementation safety.
- Prefer `warning` plus a concrete recommendation when the plan is likely workable but may need broader first-pass coverage, for example a derived field reason that should mention list/detail/update instead of only list. Use `blocker` only for mismatches that would probably produce a non-working prototype, unsafe/unbounded edits, or edits outside the approved file set.
- Use `blocker` only when the plan would likely produce unsafe, incorrect, unbounded, or unimplementable code changes, or when it repurposes existing behavior without explicit requirement support.
- Treat an unnecessary `must_modify` policy as a warning unless it makes the plan unsafe, unbounded, or likely to overwrite existing behavior. Do not block an otherwise safe prototype plan solely because a related file may remain unchanged.
- Do not ask the analyst questions about internal file responsibilities. Make an architectural review judgment.

Write prototype/output/plan_review.json with:
{
  "status": "pass|warning|blocker",
  "blockers": [],
  "warnings": [],
  "recommendations": []
}

Architecture contract requirement:
- Follow `prototype/input/architecture-contract.yaml` for artifact types, allowed roots, path placement, test capabilities, dependency policy, and UI anchor conventions.
- Do not invent file placement rules outside the contract.

Workspace path discipline:
- Treat the current working directory as the workspace root.
- Read and write `prototype/input/...` and `prototype/output/...` relative to the workspace root.
- Never use `/runs/<run-name>/prototype/...`; the valid path is `/runs/<run-name>/workspace/prototype/...` when an absolute path is unavoidable.
- Do not read from run-level `input/` or `output/` unless the prompt explicitly asks for a diagnostics-only fallback.

Final action requirement:
- Use the file write tool to create or overwrite `prototype/output/plan_review.json` with valid JSON exactly matching the schema above.
- After writing the file, you may provide a short textual summary.
- Never provide only a textual review without writing `prototype/output/plan_review.json`.

Also review requirement coverage: every requirement in `implementation_slice.requirements` must appear in implementation files and validation checks.
