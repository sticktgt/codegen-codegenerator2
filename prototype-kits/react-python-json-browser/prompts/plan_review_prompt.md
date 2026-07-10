MANDATORY OUTPUT CONTRACT:
- You must write `prototype/output/plan_review.json` before finishing this phase.
- A text summary in stdout is not sufficient.
- If the plan is safe, write status `pass` or `warning`; if unsafe, write status `blocker`.
- Do not end the response until `prototype/output/plan_review.json` has been written.

Review the proposed plan. Do not implement code.

Read:
- prototype/output/plan_proposal.json
- prototype/output/validation_plan_proposal.json
- prototype/input/requirements.json
- prototype/input/scheme_model.json
- prototype/input/run_input.json, if present
- prototype/input/implementation_slice.json
- prototype/input/kit.yaml
- prototype/input/generation-rules.yaml
- prototype/input/architecture-contract.yaml
- instructions/architecture.md
- instructions/planning-rules.md
- instructions/validation-rules.md
- instructions/testing/test-method-catalog.md
- current workspace source files as needed

Canonical instruction paths:
- Runtime workspace copies live under `instructions/...` at the workspace root.
- Markdown instructions are available from the workspace-root `instructions/` tree.
- Use `prototype/input/...` only for JSON/YAML run inputs and machine-readable contracts.

Check:
- Does the plan cover the scenario/run input requirements and acceptance criteria?
- Does the plan follow the layer rules in `instructions/architecture.md` without relying on Python to repair artifact types or create/modify decisions?
- Does every file-plan row use an artifact type that matches its path and responsibility?
- Are existing skeleton/integration files planned as modify/read rather than create?
- Is `backend/app/storage/__init__.py`, if used, classified as `backend_storage` rather than `backend_integration`?
- If `run_input.json` is present, does the plan treat it as requirement intent rather than a file plan?
- Are proposed files and validation checks minimal and relevant?
- Are any backend/frontend layers missing?
- Does the plan derive affected existing elements and proposed new elements from the requirement intent rather than assuming they were predeclared by the analyst?
- Does the plan use canonical `design_delta` only, with no deprecated `scheme_delta` substitute?
- Does every new scheme element referenced by file operations or validation checks appear in `design_delta.proposed_new_elements`?
- If the slice extends existing behavior, does the plan preserve existing accepted behavior by default?
- Does the plan avoid repurposing existing artifacts with stable responsibilities when a wrapper, UI state, or new artifact would be sufficient?
- If the plan modifies an existing artifact, does `design_delta.preservation_decisions` explain why reuse/wrapping is insufficient and what behavior remains preserved?
- For new scheme elements without a dedicated file, does `implementation_mode: "screen_internal"` name an `owning_artifact` and is the owning artifact allowed by the file plan?
- For dedicated files, does `implementation_mode: "separate_artifact"` align with the proposed file plan?
- Does the plan avoid unnecessary dependencies, and are any proposed dependency/package changes explicitly allowed by the contract, included in the file plan, and justified?
- Does the validation plan use explicit `validation_intent` for executable test-file checks, while omitting `validation_intent` for non-file checks such as `ui_static`?
- For preserved existing behavior, does the validation plan prefer `rerun_existing` before modifying or creating tests?
- If the plan proposes `extend_existing_test` or `create_new_test`, is there a clear acceptance-criteria gap that existing tests do not cover?
- If the slice changes UI behavior and `frontend_behavior` is enabled, does the validation plan include an executable browser/e2e behavior check with a behavior validation intent and a proposed file under an allowed e2e root?
- Is browser/e2e coverage lean for the slice? For one coherent CRUD/list/search screen, prefer one compact browser spec linked to multiple requirements; warn if the plan creates many independent browser specs or browser tests for edge cases that backend pytest should cover.
- If `frontend_behavior` is disabled, does the plan avoid unsupported browser/e2e test files and make the limitation explicit while still requiring `ui_static` checks?
- If formal plan validation already passed, do not block solely because design_delta metadata could be cleaner; warn and allow implementation when the file plan is safe.

Review guidance:
- Prefer a working, safe implementation plan over blocking on planner-output metadata issues that do not change implementation safety.
- Use `blocker` only when the plan would likely produce unsafe, incorrect, unbounded, or unimplementable code changes, or when it repurposes existing behavior without explicit requirement support.
- Use `warning` for design_delta classification/source-attribution issues or non-critical validation-intent issues when the file plan is still safe and minimal, for example:
  - a new element appears in both `resolved_existing_elements` and `proposed_new_elements`, but the file plan implements it safely as `screen_internal`;
  - `source` is incorrectly set to `selected_by_user`, but no unsafe file operation follows from it;
  - an existing test file is referenced for regression validation with `validation_intent: "rerun_existing"`;
  - an existing test file is proposed for modification, but rerunning existing tests would probably be enough.
- Tests are required when behavior changes, but a test file should be modified only when existing executable tests do not cover the relevant acceptance criterion.
- Do not block a safe implementation plan just because validation could be cleaner; prefer a warning unless the validation plan is non-executable or misleading.
- A `ui_static` check is not a test file. If it has `proposed_file: null`, it should normally omit `validation_intent`; if the planner accidentally used a test-file intent for `ui_static`, warn but do not block when other validation is executable.
- Browser/e2e UI behavior coverage is required only when the kit declares the `frontend_behavior` capability enabled and executable. When disabled, missing browser/e2e coverage is a warning/limitation, not a blocker, if `ui_static` and relevant regressions are present. When enabled and executable, missing browser/e2e coverage for changed UI acceptance criteria should be treated as a blocker or strong warning depending on whether implementation would otherwise be unverifiable.
- Excessive browser/e2e scope is normally a warning, not a blocker, when requirement coverage is still explicit. Recommend consolidating related UI behavior checks into one compact spec and moving API edge cases to backend pytest.
- Treat repurposing an existing API/action/service artifact as a blocker unless the requirement explicitly asks to replace the old behavior.
- For a confirmation flow around an existing destructive action, prefer preserving the existing destructive action and adding confirmation UI/state or a wrapper action.
- It is acceptable for a cancel/confirm action to be screen-internal if it only manages local UI flow or invokes an existing action; in that case the design_delta should say so explicitly and the screen file must carry the relevant scheme element for UI anchor validation.
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
