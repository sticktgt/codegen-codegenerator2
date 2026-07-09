# Planning Rules

Planning mode is read-only for source code.

When asked to plan a slice:

- Read `prototype/input/run_input.json` when it is present. This is the canonical scenario input from the requirements stage.
- Treat `prototype/input/implementation_slice.json` as a compatibility view generated from `run_input.json` for the current pipeline.
- Read `prototype/input/scheme_model.json` as scheme context from requirements/design. A listed scheme element is not proof that its implementation file already exists.
- Read `prototype/input/architecture-contract.yaml` and follow the artifact types, path placement rules, validation capabilities, validation intent rules, and UI conventions declared there.
- Read `instructions/architecture.md` as the human-readable architecture rules for layers, owned artifacts, and skeleton/integration files.
- Do not edit production source files.
- Produce `prototype/output/plan_proposal.json`.
- Produce `prototype/output/validation_plan_proposal.json` when validation checks or tests are part of the plan.
- Do not rely on static pre-generated file names. New file names must come from the proposed design delta, the current project structure, and the architecture contract.
- `run_input.json` describes requirement intent and optional selected existing elements. It does not prescribe file operations, new scheme element ids, test file names, or implementation artifact names.
- Prefer the smallest safe change set that satisfies the acceptance criteria and preserves already accepted behavior.
- If a new file is needed, include `artifact_type`, `operation`, `policy`, `path`, `reason`, `requirement_id(s)`, and `scheme_element_id(s)`.
- Use existing files when the architecture contract says the element is an integration point or when the feature is a small extension of existing behavior.
- Create a new file only when the feature introduces a new architecture artifact that should be reusable or independently owned: new screen/view/tab, reusable widget, frontend action, backend API resource, service/component, model, storage adapter/data artifact, or executable validation test.
- If behavior is preserved and existing executable tests already cover it, use `validation_intent: "rerun_existing"` instead of modifying a test file.
- Use `validation_intent: "extend_existing_test"` only when current tests do not cover the new or changed acceptance criteria.
- Use `validation_intent: "create_new_test"` only when no suitable test file exists and the kit can execute that validation type.
- For changed UI behavior, always include `ui_static` anchor checks without a validation intent. Use browser/e2e behavior test intents (`rerun_behavior_test`, `extend_behavior_test`, `create_behavior_test`) only when the architecture contract enables executable `frontend_behavior` validation.
- If a screen file is created or modified and the file plan links it to a `screen.*` scheme element, the implementation must preserve or add a root `data-prototype-id` anchor for that screen id. If the screen directly renders action controls, list those `action.*` ids in that screen file-plan item.
- If a widget file is created or modified and the file plan links it to a `widget.*` scheme element, the implementation must preserve or add a root `data-prototype-id` anchor for that widget id. Do not list unrelated action ids in a widget file-plan item unless the widget itself renders those action controls.
- If `frontend_behavior` is disabled, do not propose frontend behavior test files; plan `ui_static` checks and note the browser/e2e coverage limitation.
- If a test becomes invalid because the requirement changed intentionally, explain whether it should be modified or removed. Do not delete tests without a reason linked to the requirement.
- If the requirement is ambiguous, make a conservative planner decision that preserves existing behavior. Do not ask the analyst questions about internal file responsibilities.


## Planner ownership

The model owns the architectural content of the plan. Python validation may reject unsafe or malformed output, but it must not repair artifact types, file placement, or create/modify decisions for the model. Therefore the planner must self-check the plan before writing final JSON.

Before writing `plan_proposal.json`, verify:

- every file path is inside an allowed architecture layer;
- every `artifact_type` matches the path according to `architecture-contract.yaml`;
- existing skeleton/integration files are under `file_plan_draft.modify`, not `create`;
- `backend/app/storage/__init__.py` uses `artifact_type: backend_storage`, not `backend_integration`;
- `backend/app/main.py` is the backend integration file and uses `artifact_type: backend_integration`;
- `frontend/src/routes/routeRegistry.js` and `frontend/src/App.jsx` use `artifact_type: frontend_integration`;
- new owned artifacts use layer-specific names derived from requirements and naming rules;
- `ui_static` checks are non-file checks and should not have `validation_intent`;
- executable tests have an explicit `validation_intent` and `proposed_file`.

A plan proposal should include canonical `design_delta`, not deprecated `scheme_delta`:

```json
{
  "slice_id": "SLICE-...",
  "requirement_ids": ["REQ-..."],
  "design_delta": {
    "change_type": "extend_existing_behavior",
    "resolved_existing_elements": [],
    "proposed_new_elements": [],
    "preservation_decisions": []
  },
  "file_plan_draft": {
    "create": [],
    "modify": [],
    "read": []
  },
  "assumptions": [],
  "questions": []
}
```

Do not include package/dependency files in normal implementation plans. If a dependency is needed, write a dependency request as a limitation instead of modifying package manifests.


Browser kit rule:
- This kit variant enables executable `frontend_behavior` validation.
- When a slice changes user-visible UI behavior, propose at least one browser/e2e behavior check (`ui_behavior`, `browser_e2e`, or `e2e`) in addition to `ui_static` checks.
- For a new behavior test, use `validation_intent: "create_behavior_test"` and a `proposed_file` under `frontend/e2e/` or `frontend/tests/e2e/`.
- Browser behavior tests should exercise the actual running frontend through Playwright and may use the existing backend API through the Vite proxy.

## Existing skeleton and integration files

A greenfield slice starts from a kit skeleton, not from an empty directory. Existing skeleton/integration files must be planned as `modify` when they are wired to new artifacts. Do not put an existing file under `file_plan_draft.create`.

Use these artifact types for common skeleton files:

- `frontend/src/routes/routeRegistry.js` → `frontend_integration`, `policy: may_modify`
- `frontend/src/App.jsx` → `frontend_integration`, `policy: may_modify` if needed
- `backend/app/main.py` → `backend_integration`, `policy: may_modify`
- `backend/app/storage/__init__.py` → `backend_storage`, `policy: may_modify`

Artifact types that allow only `modify` and `read` in `architecture-contract.yaml` must never be planned as `create`. The planner should fix its own file plan before writing final JSON; do not rely on Python normalization to convert `create` to `modify` or to change an artifact type.
