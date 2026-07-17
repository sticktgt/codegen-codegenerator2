# Pytest / Playwright validation review additions

Additional reads and rules:
- instructions/testing/validation-planning.md
- instructions/testing/test-method-catalog.md
- Does the validation plan use explicit `validation_intent` for executable test-file checks, while omitting `validation_intent` for non-file checks such as `ui_static`?
- For preserved existing behavior, does the validation plan prefer `rerun_existing` before modifying or creating tests?
- If the plan proposes `extend_existing_test` or `create_new_test`, is there a clear acceptance-criteria gap that existing tests do not cover?
- For each executable validation check, compare `proposed_file` with current workspace files and file_plan:
  - If `validation_intent` is `create_new_test` / `create_behavior_test` but the file already exists, treat this as a blocker because implementation may overwrite existing tests. It should be `extend_existing_test` / `extend_behavior_test` or `rerun_existing` / `rerun_behavior_test`.
  - If a test file is existing and writable, the implementation plan must preserve existing tests and add only the missing coverage.
  - If the file is read-only, validation intent must be rerun-only.
- If the slice changes UI behavior and `frontend_behavior` is enabled, does the validation plan include an executable browser/e2e behavior check with a behavior validation intent and a proposed file under an allowed e2e root?
- Is browser/e2e coverage lean for the slice? For one coherent CRUD/list/search screen, prefer one compact browser spec linked to multiple requirements; warn if the plan creates many independent browser specs or browser tests for edge cases that backend pytest should cover.
- If `frontend_behavior` is disabled, does the plan avoid unsupported browser/e2e test files and make the limitation explicit while still requiring `ui_static` checks?
- Use `warning` for design_delta classification/source-attribution issues or non-critical validation-intent issues when the file plan is still safe and minimal, for example:
  - a new element appears in both `resolved_existing_elements` and `proposed_new_elements`, but the file plan implements it safely as `screen_internal`;
  - `source` is incorrectly set to `selected_by_user`, but no unsafe file operation follows from it;
  - an existing element is discovered from baseline/workspace but missing from the current scheme_model;
  - an existing test file is referenced for regression validation with `validation_intent: "rerun_existing"`;
  - an existing test file is proposed for modification, but rerunning existing tests would probably be enough.
- Tests are required when behavior changes, but a test file should be modified only when existing executable tests do not cover the relevant acceptance criterion.
- Do not block a safe implementation plan just because validation could be cleaner; prefer a warning unless the validation plan is non-executable or misleading.
- A `ui_static` check is not a test file. If it has `proposed_file: null`, it should normally omit `validation_intent`; if the planner accidentally used a test-file intent for `ui_static`, warn but do not block when other validation is executable.
- Browser/e2e UI behavior coverage is required only when the kit declares the `frontend_behavior` capability enabled and executable. When disabled, missing browser/e2e coverage is a warning/limitation, not a blocker, if `ui_static` and relevant regressions are present. When enabled and executable, missing browser/e2e coverage for changed UI acceptance criteria should be treated as a blocker or strong warning depending on whether implementation would otherwise be unverifiable.
- Excessive browser/e2e scope is normally a warning, not a blocker, when requirement coverage is still explicit. Recommend consolidating related UI behavior checks into one compact spec and moving API edge cases to backend pytest.
