# Testing implementation additions

Additional reads and rules:
- instructions/testing/validation-planning.md
- instructions/testing/test-method-catalog.md, if creating or updating any validation test
- If a validation test file is listed in file_plan.json, follow its policy, `validation_intent`, and any `test_method_id`/catalog guidance.
- `validation_intent: "rerun_existing"` / `"rerun_behavior_test"` with read-only/read means do not edit that test file.
- `validation_intent: "extend_existing_test"` / `"extend_behavior_test"` means preserve the existing file and add only missing acceptance-criteria coverage.
- `validation_intent: "create_new_test"` / `"create_behavior_test"` means create the planned file only if it is in file_plan.json and does not already exist; otherwise document the plan mismatch.
- For non-file checks such as `ui_static`, do not create any test file; implement the required UI anchors in the allowed UI artifact.
- If validation_plan.json proposes a test file that is not present in file_plan.json, do not create it; report the limitation.
- When writing tests into an existing file, never replace previous test coverage with only the current slice tests. Preserve unrelated existing tests unless the requirement explicitly removes that behavior.
