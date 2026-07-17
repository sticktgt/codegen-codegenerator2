# Pytest / Playwright validation planning additions

Additional reads and rules:
- instructions/testing/validation-planning.md
- instructions/testing/test-method-catalog.md
- If tests are needed, propose validation checks in validation_plan_proposal.json; do not create them yet. Choose validation methods from `instructions/testing/test-method-catalog.md`; include `test_method_id` for executable checks and for non-file `ui_static` checks when a matching method exists.
- Tests are important, but test file modification is not always necessary. Choose explicit validation intent for executable validation checks:
  - `rerun_existing`: use when an existing test file already covers preserved behavior; the test file must be read-only in the promoted file plan.
  - `extend_existing_test`: use when an existing executable test file should be modified because acceptance criteria are not covered.
  - `create_new_test`: use when no suitable existing test file exists and the kit can run that validation.
  - `rerun_behavior_test` / `extend_behavior_test` / `create_behavior_test`: use only for frontend behavior checks when `frontend_behavior` is enabled and executable.
- Keep validation intent consistent with workspace file existence:
  - If `proposed_file` already exists in the current workspace, do not use `create_new_test` or `create_behavior_test` for that same path. Use `extend_existing_test` / `extend_behavior_test` when the file must be modified, or `rerun_existing` / `rerun_behavior_test` when existing coverage is sufficient.
  - Use `create_new_test` only for a new path that does not already exist and whose file-plan item is `create`/`must_create` or equivalent writable creation policy.
  - When extending an existing test file, plan an additive change that preserves its existing tests; do not plan a full replacement of prior coverage.
- For preserved behavior, prefer rerunning existing tests before creating or modifying test files.
- Do not propose frontend unit test files unless `frontend/package.json` already has a test script and declared test runner.
- Prefer backend API/service tests for backend behavior, edge cases, validation errors, and most negative cases. For Python API behavior with mutable state, use `test_method_id: "backend.pytest.api.mutable-state"`. Do not use smoke tests for feature-specific API behavior; smoke checks are baseline reruns (`backend.smoke.import-health`) and should normally be read-only.
- For changed web UI controls or UI behavior, include non-file `ui_static` checks linked to the relevant requirement and scheme screen/widget/action. Use `proposed_file: null`, omit `validation_intent`, and use `test_method_id: "web.ui.static-anchors"` for `ui_static`.
- For created or modified frontend screen/widget files, include the relevant `screen.*`, `widget.*`, and directly rendered `action.*` ids in that file-plan item's `scheme_elements`, so implementation and `ui_static` can validate the required anchors. Do not put unrelated action ids on a widget unless the widget itself renders those controls.
- If `architecture-contract.yaml` enables executable `frontend_behavior`, changed user-visible UI behavior should also have at least one executable browser/e2e behavior check under an allowed e2e root. Keep that coverage lean: one compact spec may cover several related requirements for a single CRUD/list/search screen. For CRUD/list/search screens, use `test_method_id: "web.e2e.playwright.crud-list-search-flow"` and combine it with the relevant form, item-action, filtered-list, async-state, and count assertion catalog methods in the check description if needed.
- When a search requirement names several searchable fields or dimensions, reflect that in the browser/e2e check description. A compact spec is still preferred, but it must cover the named user-visible search dimensions instead of testing only the first field.
- If `frontend_behavior` is disabled, do not propose unsupported browser/e2e files; record the missing browser behavior coverage as a kit limitation or assumption.
- Do not create separate browser specs or browser edge-case tests merely for symmetry with requirement ids. Multiple validation checks may point to the same compact browser spec.
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
- For `web.e2e.playwright.crud-list-search-flow`, compact means one user journey test with steps, not many independent Playwright tests for every possible edge case.
- Do not propose browser checks for unrequested behavior such as delete/confirmation, empty-state, minimal-field, or multi-record edge cases unless the requirements explicitly include them. Backend pytest should cover API edge cases.
- Browser behavior tests should exercise the actual running frontend through Playwright and may use the existing backend API through the Vite proxy.
