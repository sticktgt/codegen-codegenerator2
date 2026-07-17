# Testing repair additions

Additional reads and rules:
- instructions/testing/validation-planning.md
- instructions/testing/test-method-catalog.md
- Repair the smallest failed validation surface while keeping the approved file plan and selected test method.
- Do not repair feature behavior by editing smoke/bootstrap tests unless the feature file plan explicitly allows that smoke file to change for the feature.
- For non-file checks such as `ui_static`, repair the allowed UI artifact; do not create or edit test files just to satisfy the static check.
- If ui_static reports advisory hygiene warnings, use them as context only. Repair a browser/e2e file only when Playwright or validation output confirms the warning is connected to an actual failure.
