# Validation Rules

Validation has three levels:

- Kit-level validation: install, smoke, backend tests, frontend build.
- Slice-level functional validation: executable checks proposed for the current requirement.
- UI static validation: lightweight checks for UI anchors and action/control linkage.

When proposing slice-level validation:

- Read `prototype/input/architecture-contract.yaml` and use only validation capabilities enabled by the kit.
- Use explicit validation intent for executable test-file checks:
  - `rerun_existing`: rerun an existing test file without modifying it.
  - `extend_existing_test`: add missing coverage to an existing test file.
  - `create_new_test`: create a new test file when no suitable existing file exists.
  - `rerun_behavior_test`: rerun an existing browser/e2e UI behavior test without modifying it.
  - `extend_behavior_test`: add missing browser/e2e coverage to an existing behavior test.
  - `create_behavior_test`: create a browser/e2e UI behavior test when the kit has enabled executable frontend behavior validation.
- For preserved existing behavior, prefer `rerun_existing` before changing tests. Tests are required, but test-file modification is not required when an existing executable test already covers the regression.
- Do not create tests unless the validation plan explicitly includes the test file via `proposed_file`.
- Do not add test dependencies unless the plan explicitly allows a dependency-review flow.
- Prefer backend API or service tests before browser/e2e tests for this lightweight kit when backend behavior is involved.
- For changed UI behavior, propose browser/e2e tests only when `validation_capabilities.frontend_behavior.enabled` is true and the kit has an executable frontend behavior validation task.
- When frontend behavior validation is disabled, keep `ui_static` checks and record browser/e2e coverage as a kit limitation; do not invent test files or dependencies.
- Do not propose frontend unit test files unless the architecture contract and Taskfile say frontend tests are enabled and executed.
- Link each validation check to requirement ids and scheme element ids.
- Store validation proposals in `prototype/output/validation_plan_proposal.json`.
- Existing tests are part of the architecture. If a later requirement changes behavior, plan either to modify the affected test, keep it as regression coverage, or explicitly explain why it is obsolete.
- Generated tests must not leave tracked mock data changed. Prefer `tmp_path`, monkeypatching the storage path/function, or an isolated fixture copy. If a test temporarily touches tracked mock storage, it must restore it exactly before the test finishes.

Validation plans are proposals. They are checked and promoted by the pipeline before implementation.

A functional validation check should be executable and should usually have `proposed_file`:

```json
{
  "id": "VAL-REQ-...-api",
  "type": "api",
  "requirement_id": "REQ-...",
  "scheme_element_id": "api.notes",
  "description": "Verify the new API behavior.",
  "validation_intent": "extend_existing_test",
  "proposed_file": "backend/tests/test_example.py",
  "executable_validation": true
}
```

Build, smoke, and static checks are useful supporting checks, but they do not by themselves prove that a business requirement was implemented.

Existing regression example:

```json
{
  "id": "VAL-REQ-006-api-regression",
  "type": "api",
  "requirement_id": "REQ-006",
  "scheme_element_id": "api.notes",
  "description": "Rerun the existing DELETE API tests to verify preserved backend behavior still works.",
  "validation_intent": "rerun_existing",
  "proposed_file": "backend/tests/test_notes_api.py",
  "executable_validation": true
}
```


UI static validation checks:

- When a slice creates or changes web UI controls, propose a `ui_static` check with `proposed_file: null` and no `validation_intent`.
- Link the check to the requirement id and the relevant UI/action scheme element id.
- Screen ids (`screen.*`) must be anchored on the screen root/outermost JSX element when the screen file is created or modified for the slice.
- Widget ids (`widget.*`) must be anchored on the widget root/outermost JSX element when the widget file is created or modified for the slice.
- `ui_static` checks do not create test files. They are executed by the pipeline's UI static checker. Do not use `create_new_test`, `extend_existing_test`, or behavior test intents for `ui_static`.
- In strict UI mode, missing anchors become repairable blockers. In normal mode they remain warnings.

Example:

```json
{
  "id": "VAL-REQ-006-ui-static",
  "type": "ui_static",
  "requirement_id": "REQ-006",
  "scheme_element_id": "action.confirm-delete-note",
  "description": "Verify confirm/cancel delete UI controls have stable prototype anchors.",
  "proposed_file": null
}
```

Browser/e2e UI behavior example, only when frontend_behavior is enabled and executable:

```json
{
  "id": "VAL-REQ-006-ui-behavior",
  "type": "ui_behavior",
  "requirement_id": "REQ-006",
  "scheme_element_id": "action.confirm-delete-note",
  "description": "Verify Delete opens confirmation, Cancel keeps the note, and Confirm deletes it in the browser.",
  "validation_intent": "create_behavior_test",
  "proposed_file": "frontend/e2e/confirm_delete_note.spec.js",
  "executable_validation": true
}
```
