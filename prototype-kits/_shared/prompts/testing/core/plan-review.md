# Testing validation review additions

Additional reads and rules:
- instructions/testing/validation-planning.md
- instructions/testing/test-method-catalog.md
- Does the validation plan use explicit `validation_intent` for executable test-file checks, while omitting `validation_intent` for non-file checks such as `ui_static`?
- For preserved existing behavior, does the validation plan prefer rerun coverage before modifying or creating tests?
- If the plan proposes extending or creating a test, is there a clear acceptance-criteria gap that existing tests do not cover?
- Treat small coverage gaps as warnings when the plan is otherwise executable. Use blockers only for plans that almost certainly cannot validate or implement the requested prototype within the approved file plan.
