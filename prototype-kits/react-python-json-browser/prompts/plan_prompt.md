Plan the current implementation slice. Do not implement code.

Read:
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
- the current workspace source files as needed

Canonical instruction paths:
- Runtime workspace copies live under `instructions/...` at the workspace root.
- Markdown instructions are available from the workspace-root `instructions/` tree.
- Use `prototype/input/...` only for JSON/YAML run inputs and machine-readable contracts.

Rules:
- Do not edit production source files.
- Do not create implementation files.
- Do not change package files or dependencies during planning; only propose them in the file plan when justified and allowed.
- Do not propose dependency/package-file changes by default. If a new dependency is genuinely useful for implementation or validation, include the relevant package/config file in the file plan only when the architecture contract allows it, and record a short rationale. Otherwise record the limitation or use existing kit dependencies.
- Use project structure and kit rules to propose where changes should go.
- The model owns architectural planning decisions. Python validation may reject unsafe or malformed plans, but it must not rewrite artifact types, file placement, or create/modify decisions to repair architectural meaning. Produce a plan that is already consistent with the architecture rules.
- Before writing final JSON, self-check the plan against `instructions/architecture.md`, `instructions/planning-rules.md`, `generation-rules.yaml`, and `architecture-contract.yaml`; fix your own plan if any row violates those rules.
- The baseline workspace is not empty even for `change_type: create_new`: kit skeleton files such as `frontend/src/routes/routeRegistry.js`, `frontend/src/App.jsx`, `backend/app/main.py`, and package/task files may already exist. If an existing skeleton/integration file must be wired, put it under `file_plan_draft.modify` with a writable policy such as `may_modify`; do not put existing files under `file_plan_draft.create`.
- Artifact types whose contract allows only `modify`/`read` (for example `frontend_integration` and `backend_integration`) must never be proposed as `create`.
- Use `backend_integration` only for `backend/app/main.py`. Use `backend_storage` for `backend/app/storage/__init__.py` and all files under `backend/app/storage/`.
- Use `frontend_integration` for existing frontend wiring files such as `frontend/src/routes/routeRegistry.js` and `frontend/src/App.jsx`.
- New file names and new scheme element ids must be proposed by you from the requirement intent and current project conventions, not copied from hardcoded assumptions.
- Follow the `planner_output` section of `architecture-contract.yaml` for canonical design_delta output. Do not use deprecated alternatives such as `scheme_delta`.
- Treat `prototype/input/run_input.json`, when present, as the canonical scenario input from the requirements stage. Treat `implementation_slice.json` as a compatibility view generated from it for the current pipeline.
- Treat `prototype/input/scheme_model.json` as scheme context from requirements/design. A scheme element being present does not prove that the implementation artifact exists in the workspace.
- The scenario/run input describes user intent, acceptance criteria, optional selected existing scheme elements, and constraints. It does not prescribe file policies, new element ids, or implementation artifact names.
- If `run_input.json` or `implementation_slice.json` includes `selected_existing_elements`, use them as user-selected context. If it is empty or absent, resolve affected existing elements yourself from requirements, scheme_model, traceability implied by existing files, and code.
- Strictly separate existing and new scheme elements:
  - `design_delta.resolved_existing_elements` contains only elements that already exist in `scheme_model.json` or were explicitly listed in `implementation_slice.selected_existing_elements`.
  - `design_delta.proposed_new_elements` contains only elements you introduce for this slice; do not put these ids into `resolved_existing_elements`.
  - No element id may appear in both lists.
  - Use `source: "selected_by_user"` only for ids explicitly listed in `implementation_slice.selected_existing_elements`.
  - Use `source: "resolved_by_planner"` for existing elements you inferred from requirements, scheme_model, traceability, or code.
- If the slice extends existing behavior, preserve already accepted behavior by default. Prefer adding a wrapper, UI state, or new artifact over repurposing an existing artifact with a stable responsibility.
- If a new scheme action is implemented inside an existing screen rather than a dedicated action file, list it in `design_delta.proposed_new_elements` with `implementation_mode: "screen_internal"` and `owning_artifact`. Also include that action id in the owning screen file-plan item `scheme_elements` so UI anchor checks can validate it.
- For simple React CRUD/list/search screens, prefer screen-internal UI actions when the button/form handler is rendered directly by the screen. Do not create dedicated frontend action files just for naming symmetry. In the planned screen file item, include the `action.*` ids rendered by the screen so ui_static can validate the anchors.
- If a new scheme action is implemented by a dedicated file, list it with `implementation_mode: "separate_artifact"` and `artifact` or `planned_artifact`, and the path must follow `generation-rules.yaml` exactly: `frontend/src/actions/{PascalName}.js` such as `CreateNote.js`, not kebab-case or lowercase variants.
- Do not repurpose an existing action/API/service artifact unless the requirement explicitly asks to replace the old behavior. If you must modify an existing artifact, explain why reuse/wrapping is insufficient in `design_delta.preservation_decisions`.
- If tests are needed, propose validation checks in validation_plan_proposal.json; do not create them yet. Choose validation methods from `instructions/testing/test-method-catalog.md`; include `test_method_id` for executable checks and for non-file `ui_static` checks when a matching method exists.
- Tests are important, but test file modification is not always necessary. Choose explicit validation intent for executable validation checks:
  - `rerun_existing`: use when an existing test file already covers preserved behavior; the test file must be read-only in the promoted file plan.
  - `extend_existing_test`: use when an existing executable test file should be modified because acceptance criteria are not covered.
  - `create_new_test`: use when no suitable existing test file exists and the kit can run that validation.
  - `rerun_behavior_test` / `extend_behavior_test` / `create_behavior_test`: use only for frontend behavior checks when `frontend_behavior` is enabled and executable.
- For preserved behavior, prefer rerunning existing tests before creating or modifying test files.
- Do not propose frontend unit test files unless `frontend/package.json` already has a test script and declared test runner.
- Prefer backend API/service tests for backend behavior, edge cases, validation errors, and most negative cases. For Python API behavior with mutable state, use `test_method_id: "backend.pytest.api.mutable-state"`. Do not use smoke tests for feature-specific API behavior; smoke checks are baseline reruns (`backend.smoke.import-health`) and should normally be read-only.
- For changed web UI controls or UI behavior, include non-file `ui_static` checks linked to the relevant requirement and scheme screen/widget/action. Use `proposed_file: null`, omit `validation_intent`, and use `test_method_id: "web.ui.static-anchors"` for `ui_static`.
- For created or modified frontend screen/widget files, include the relevant `screen.*`, `widget.*`, and directly rendered `action.*` ids in that file-plan item's `scheme_elements`, so implementation and `ui_static` can validate the required anchors. Do not put unrelated action ids on a widget unless the widget itself renders those controls.
- If `architecture-contract.yaml` enables executable `frontend_behavior`, changed user-visible UI behavior should also have at least one executable browser/e2e behavior check under an allowed e2e root. Keep that coverage lean: one compact spec may cover several related requirements for a single CRUD/list/search screen. For CRUD/list/search screens, use `test_method_id: "web.e2e.playwright.crud-list-search-flow"` and combine it with the relevant form, item-action, filtered-list, async-state, and count assertion catalog methods in the check description if needed.
- If `frontend_behavior` is disabled, do not propose unsupported browser/e2e files; record the missing browser behavior coverage as a kit limitation or assumption.
- Do not create separate browser specs or browser edge-case tests merely for symmetry with requirement ids. Multiple validation checks may point to the same compact browser spec.
- If the requirement is ambiguous, make a conservative planner decision that preserves existing behavior. Do not ask the analyst implementation-design questions about internal file responsibilities.

Write exactly these JSON reports:
- prototype/output/plan_proposal.json
- prototype/output/validation_plan_proposal.json

plan_proposal.json shape:
{
  "slice_id": "...",
  "requirement_ids": [],
  "design_delta": {
    "change_type": "create_new|extend_existing_behavior|replace_existing_behavior|refactor_only",
    "resolved_existing_elements": [
      {
        "id": "existing scheme element id",
        "type": "screen|action|api|service|data|component|other",
        "source": "selected_by_user|resolved_by_planner",
        "reason": "why this existing element is relevant; use selected_by_user only when id is explicitly selected in implementation_slice"
      }
    ],
    "proposed_new_elements": [
      {
        "id": "new scheme element id proposed by the planner",
        "type": "screen|action|api|service|data|component|other",
        "requirement_id": "REQ-...",
        "implementation_mode": "separate_artifact|screen_internal|existing_artifact_extension",
        "artifact": "relative/path for separate_artifact or null",
        "owning_artifact": "relative/path for screen_internal or existing_artifact_extension, otherwise null",
        "reason": "why this new element is needed"
      }
    ],
    "preservation_decisions": [
      {
        "existing_element_id": "existing scheme element id",
        "artifact": "relative/path or null",
        "decision": "reuse|wrap|modify_without_repurpose|replace",
        "preserved_behavior": "what existing accepted behavior remains valid",
        "reason": "why this decision preserves or intentionally replaces existing behavior"
      }
    ]
  },
  "file_plan_draft": {
    "create": [
      {
        "path": "relative/path",
        "policy": "must_create",
        "requirement_id": "REQ-...",
        "scheme_element_id": "primary scheme element id",
        "scheme_elements": ["all scheme element ids implemented or anchored by this file"],
        "artifact_type": "...",
        "reason": "why this file is needed"
      }
    ],
    "modify": [],
    "read": []
  },
  "assumptions": [],
  "questions": []
}

validation_plan_proposal.json shape:
{
  "slice_id": "...",
  "checks": [
    {
      "id": "VAL-...",
      "type": "smoke|unit|api|service|build|static|ui_static|ui_behavior|browser_e2e|e2e",
      "requirement_id": "REQ-...",
      "scheme_element_id": "...",
      "description": "what this check proves; mention secondary catalog methods when useful",
      "test_method_id": "catalog method id such as backend.pytest.api.mutable-state, web.ui.static-anchors, or web.e2e.playwright.crud-list-search-flow",
      "validation_intent": "rerun_existing|extend_existing_test|create_new_test|rerun_behavior_test|extend_behavior_test|create_behavior_test; omit for non-file checks such as ui_static",
      "proposed_file": "relative/test/path or null"
    }
  ],
  "assumptions": []
}

Architecture contract requirement:
- Follow `prototype/input/architecture-contract.yaml` for artifact types, allowed roots, path placement, test capabilities, dependency policy, and UI anchor conventions.
- Do not invent file placement rules outside the contract.

Workspace path discipline:
- Treat the current working directory as the workspace root.
- Read and write `prototype/input/...` and `prototype/output/...` relative to the workspace root.
- Never use `/runs/<run-name>/prototype/...`; the valid path is `/runs/<run-name>/workspace/prototype/...` when an absolute path is unavoidable.
- Do not read from run-level `input/` or `output/` unless the prompt explicitly asks for a diagnostics-only fallback.


Planner-output discipline:
- `design_delta` is the only canonical design-delta section. Do not write `scheme_delta`.
- Every new scheme element referenced by `file_plan_draft` or `validation_plan_proposal` must appear in `design_delta.proposed_new_elements`.
- New scheme element ids must not appear in `resolved_existing_elements`, even if they are mentioned by validation checks or anchored inside an existing screen.
- Existing element ids already present in `scheme_model.json` should not appear in `proposed_new_elements`.
- A screen-internal action may have no dedicated file, but it still needs a design_delta entry with `implementation_mode: "screen_internal"` and `owning_artifact` pointing to the owning file path or owning screen element id.
- If a screen file implements screen-internal actions, include those action ids in the screen file's `scheme_elements` and include the related requirement ids on the screen file when you can.
- Do not include files in the file plan merely to satisfy naming symmetry. File creation must follow the actual architecture decision.
- For confirmation flows, prefer a working minimal plan: preserve the existing destructive action and implement Confirm/Cancel as screen-internal if separate files are not needed.

Validation-intent discipline:
- For backend/API behavior that is preserved rather than changed, use `validation_intent: "rerun_existing"` and point to an existing test file if that test already covers the regression.
- `rerun_existing` means the implementation agent must not edit that test file; it is validation coverage, not a change request.
- Use `extend_existing_test` only when the acceptance criteria require new executable coverage that is not already present.
- Use `create_new_test` only when there is no suitable existing test file and the kit can run the new test.
- UI-only confirmation/cancel behavior in the browser-enabled kit should be covered by `ui_static` anchors plus preserved backend regression checks unless an executable UI/e2e capability is enabled.
- In a browser/e2e kit where `frontend_behavior.enabled: true`, UI behavior changes such as Delete → Confirm/Cancel must include an executable browser/e2e validation check with a proposed file under `frontend/e2e/` or `frontend/tests/e2e/`.
- When an executable `frontend_behavior` capability is enabled, changed UI behavior should get browser/e2e coverage using `ui_behavior`, `browser_e2e`, or `e2e` checks and a behavior validation intent.
- If the capability is disabled, mention the browser/e2e gap in assumptions instead of creating unsupported test files.


Browser kit rule:
- This kit variant enables executable `frontend_behavior` validation.
- When a slice changes user-visible UI behavior, propose at least one browser/e2e behavior check (`ui_behavior`, `browser_e2e`, or `e2e`) in addition to `ui_static` checks.
- For a new behavior test, use `validation_intent: "create_behavior_test"` and a `proposed_file` under `frontend/e2e/` or `frontend/tests/e2e/`.
- A single compact browser spec may cover multiple related requirements; represent coverage with separate validation checks if needed.
- Browser behavior tests should exercise the actual running frontend through Playwright and may use the existing backend API through the Vite proxy.


- Requirement coverage rules:
  - Every requirement id in `implementation_slice.requirements` must appear in at least one planned implementation file and at least one validation check.
  - Coverage may be direct (`requirement_id`/`requirements`) or through a referenced scheme element whose scheme-model requirements include that id.
  - For screen-internal actions, the owning screen file is the implementation file for that action requirement; make that relationship explicit through `scheme_elements` and/or `design_delta.owning_artifact`.
  - Do not cover primary requirements only implicitly through a broad check under a different requirement id.
