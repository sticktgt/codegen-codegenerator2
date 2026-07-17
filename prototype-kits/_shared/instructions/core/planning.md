# Planning Rules

Planning mode is read-only for source code.

When asked to plan a slice:

- Read `prototype/input/run_input.json` when it is present. This is the canonical scenario input from the requirements stage.
- Treat `prototype/input/implementation_slice.json` as a compatibility view generated from `run_input.json` for the current pipeline.
- Read `prototype/input/scheme_model.json` as scheme context from requirements/design. A listed scheme element is not proof that its implementation file already exists, and the scheme may be partial in incremental runs.
- Read `prototype/input/baseline_context/*.json` when present. These files are read-only semantic context from the previous successful run, not file-change instructions.
- Read `prototype/input/architecture-contract.yaml` and follow the artifact types, path placement rules, validation capabilities, validation intent rules, and UI conventions declared there.
- Read `instructions/core/architecture.md` and `instructions/core/architecture-addons/react-python-json-browser.md` as the human-readable architecture rules for layers, owned artifacts, and skeleton/integration files.
- Do not edit production source files.
- Produce `prototype/output/plan_proposal.json`.
- Produce `prototype/output/validation_plan_proposal.json` when validation checks or tests are part of the plan.
- Do not rely on static pre-generated file names. New file names must come from the proposed design delta, the current project structure, and the architecture contract.
- `run_input.json` describes requirement intent and optional selected existing elements. It does not prescribe file operations, new scheme element ids, test file names, or implementation artifact names.
- When an incremental slice references an element missing from the current scheme_model, inspect baseline_context and workspace code before treating it as new. If it is already implemented or previously traced, classify it as resolved existing and record a schema gap/update candidate.
- Prefer the smallest safe change set that satisfies the acceptance criteria and preserves already accepted behavior.
- If a new file is needed, include `artifact_type`, `operation`, `policy`, `path`, `reason`, `requirement_id(s)`, and `scheme_element_id(s)`.
- Use existing files when the architecture contract says the element is an integration point or when the feature is a small extension of existing behavior.
- Create a new file only when the feature introduces a new architecture artifact that should be reusable or independently owned: new screen/view/tab, reusable widget, frontend action, backend API resource, service/component, model, storage adapter/data artifact, or executable validation test.
- If behavior is preserved and existing executable tests already cover it, use `validation_intent: "rerun_existing"` instead of modifying a test file.
- Before finalizing the file plan, compare the planned implementation operations with the validation flow. If validation checks list, detail, create, update, delete, search, filter, or UI refresh behavior, the file-plan reasons for the owning model/service/API/frontend files must explicitly cover those operations or explain why a shared helper/model change covers all of them.
- For derived or related response/display fields, plan consistent population across every endpoint or service method that returns the same response model in the validated flow. Do not plan only the list operation when validation will assert detail, create, update, or post-edit refresh responses.
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
- executable tests have an explicit `validation_intent` and `proposed_file`;
- validation checks are aligned with file-plan reasons: every endpoint/UI operation asserted by validation is either named in the relevant file-plan reason or covered by a clearly planned shared helper/model/mapper change.

A plan proposal should include canonical `design_delta`, not deprecated `scheme_delta`:

```json
{
  "slice_id": "SLICE-...",
  "requirement_ids": ["REQ-..."],
  "design_delta": {
    "change_type": "extend_existing_behavior",
    "resolved_existing_elements": [],
    "proposed_new_elements": [],
    "schema_gaps": [],
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

## Scheme context and baseline discovery

`scheme_model.json` is an analyst/design context snapshot, not a complete mandatory registry of every element in the codebase. In incremental runs, classify element ids as follows:

- `resolved_existing_elements` for ids present in `scheme_model.json`, explicitly selected by the slice, found in `prototype/input/baseline_context`, previous traceability, or discovered in current workspace code.
- `proposed_new_elements` only for ids introduced by the current slice and not known from scheme_model, selected elements, baseline context, previous traceability, or workspace discovery.
- `schema_gaps` for existing/discovered elements that are absent from the current scheme_model and should later be added to an analyst-facing schema.

Do not create artificial proposed-new elements merely to satisfy validation when the element is already present in the baseline app. Conversely, if an element is not present in the scheme, not discoverable in baseline/code, and still appears in file/validation plans, either propose it as new with an implementation mode or remove the reference.


Browser kit rule:
- This kit variant enables executable `frontend_behavior` validation.
- When a slice changes user-visible UI behavior, propose at least one browser/e2e behavior check (`ui_behavior`, `browser_e2e`, or `e2e`) in addition to `ui_static` checks.
- For a new behavior test, use `validation_intent: "create_behavior_test"` and a `proposed_file` under `frontend/e2e/` or `frontend/tests/e2e/`.
- Browser behavior tests should exercise the actual running frontend through Playwright and may use the existing backend API through the Vite proxy.

## File policy strength: must_modify vs may_modify

Use `must_modify` only for files that must receive a semantic code/content change for the slice to be correct. Use `may_modify` for files that are likely implementation locations but could remain unchanged after reading the existing code. Use `read`/`read_only` for files needed only as context or regression inputs.

Do not require a file to change just because it belongs to a related layer or helps traceability. In incremental slices, first decide the precise owner of the new behavior. If a derived field can be provided cleanly as a model computed field, the service/API layer should not be `must_modify` unless it also needs real filtering, mapping, endpoint, or persistence logic changes.

For every `must_modify` row, the reason should describe a concrete expected semantic change in that file, such as “add `<field>` to the response model” or “add `<filter>` handling to the list operation”. If the reason is “inspect existing behavior”, “preserve behavior”, “reuse endpoint”, or “verify anchors”, the file should not be `must_modify`.

When a `must_modify` reason mentions a derived/related field, do not make the reason narrower than the validation flow. Prefer wording such as “populate `<field>` for list/detail/update responses through the shared response mapper” or “add a shared enrichment helper used by list/get/update” when those operations are validated. Narrow wording such as “extend list loop” is unsafe if tests will assert get/update responses.

## Existing skeleton and integration files

A greenfield slice starts from a kit skeleton, not from an empty directory. Existing skeleton/integration files must be planned as `modify` when they are wired to new artifacts. Do not put an existing file under `file_plan_draft.create`.

Use these artifact types for common skeleton files:

- `frontend/src/routes/routeRegistry.js` → `frontend_integration`, `policy: may_modify`
- `frontend/src/App.jsx` → `frontend_integration`, `policy: may_modify` if needed
- `backend/app/main.py` → `backend_integration`, `policy: may_modify`
- `backend/app/storage/__init__.py` → `backend_storage`, `policy: may_modify`

Artifact types that allow only `modify` and `read` in `architecture-contract.yaml` must never be planned as `create`. The planner should fix its own file plan before writing final JSON; do not rely on Python normalization to convert `create` to `modify` or to change an artifact type.
