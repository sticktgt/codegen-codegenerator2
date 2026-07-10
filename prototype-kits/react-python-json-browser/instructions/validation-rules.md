# Validation Rules

Validation has three levels:

- Kit-level validation: install, smoke, backend tests, frontend build.
- Slice-level functional validation: executable checks proposed for the current requirement.
- UI static validation: static checks for UI anchors and action/control linkage.

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
- New test dependencies are allowed when the plan explicitly includes the relevant package/dependency file changes and a short rationale. Otherwise keep generated tests within the current kit dependency set.
- Prefer backend API or service tests before browser/e2e tests for this browser-enabled kit when backend behavior is involved.
- For changed UI behavior, propose browser/e2e tests only when `validation_capabilities.frontend_behavior.enabled` is true and the kit has an executable frontend behavior validation task.
- When frontend behavior validation is disabled, keep `ui_static` checks and record browser/e2e coverage as a kit limitation; do not invent test files, package scripts, or dependencies outside the approved plan.
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
- A direct `screen.*` or `widget.*` root anchor must appear only once in the source file that owns it. Do not put the same anchor on both the root container and a nested heading/control.
- Duplicate direct screen/widget anchors are strict UI blockers because browser/e2e tests use strict locators for stable prototype anchors.
- Action ids (`action.*`) are required only in UI files whose file-plan item directly lists those action ids and that actually render the corresponding controls. Do not require a widget to carry action anchors that are rendered by its owning screen or another file.
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


Browser kit rule:
- This kit variant enables executable `frontend_behavior` validation.
- When a slice changes user-visible UI behavior, propose at least one browser/e2e behavior check (`ui_behavior`, `browser_e2e`, or `e2e`) in addition to `ui_static` checks.
- For a new behavior test, use `validation_intent: "create_behavior_test"` and a `proposed_file` under `frontend/e2e/` or `frontend/tests/e2e/`.
- A single browser spec file may cover multiple related requirements. Use separate validation check objects with different `requirement_id` values when one spec proves multiple UI acceptance criteria.
- Keep browser/e2e validation lean. It should prove representative user-visible flows; backend pytest should cover API edge cases and most negative cases.
- Browser behavior tests should exercise the actual running frontend through Playwright and may use the existing backend API through the Vite proxy.
- Detailed browser test writing rules are in `instructions/testing/browser-e2e.md`; load them when creating or repairing browser/e2e tests.

Backend test rule:
- Detailed backend pytest writing rules are in `instructions/testing/backend-pytest.md`; load them when creating or repairing backend API tests.
- Prefer the simplest available backend test style that proves the requirement. Synchronous FastAPI `TestClient` is usually enough for ordinary CRUD behavior, but async pytest plugins or other test dependencies are allowed when the dependency is already available or the approved file plan explicitly allows the package-file change.


## Phase output and validation authority

- OpenCode may run targeted diagnostic commands during implementation or repair, but official validation status comes from the pipeline validation step.
- Required phase report files are the durable structured output. See `instructions/pipeline-output.md`.
- Agent stdout summaries are not validation artifacts and must not replace report files.
