# Testing plan additions

Additional reads and rules:
- instructions/testing/validation-planning.md
- instructions/testing/test-method-catalog.md
- If tests are needed, propose validation checks in validation_plan_proposal.json; do not create them yet. Choose validation methods from the catalog and include `test_method_id` for executable checks and for non-file `ui_static` checks when a matching method exists.
- For existing coverage that already validates the behavior, prefer `validation_intent: "rerun_existing"` or `"rerun_behavior_test"` with `proposed_file` pointing at the existing test and a read-only/read file-plan entry.
- For new or extended coverage, use the smallest validation surface that proves the requirement: backend pytest for API/service contracts, `ui_static` for anchor presence, browser/e2e for user-visible journeys.
- Non-file checks such as `ui_static` must use `proposed_file: null` and omit `validation_intent`; they must not create test files.
- Do not add behavior outside the current requirements merely because a catalog method name mentions CRUD, search, or list behavior.
