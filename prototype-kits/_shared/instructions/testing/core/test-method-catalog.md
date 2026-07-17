# Test method catalog

Use this catalog to choose validation methods for this kit. Do not invent a new testing style when one of these methods matches the planned artifact and acceptance criterion. Add new method entries in the appropriate stack-specific catalog when a future kit needs a genuinely different testing approach.

## Method selection rules

- If a planned check matches an existing method, use that method id.
- Do not switch to another test style during implementation or repair unless the selected method is impossible for the approved file plan; report that conflict instead.
- Method examples use neutral placeholders. Replace them with entity names, file names, and anchors from the current scheme and file plans.
- Baseline smoke/bootstrap checks are rerun coverage; feature behavior belongs in feature test files.

## Rule levels

Keep method rules at the right level:
- **Core testing principles** apply across stacks: validate only requested behavior, keep tests isolated, wait for observable state after async UI transitions, and do not turn smoke/bootstrap checks into feature tests.
- **Kit contracts** apply to this React + FastAPI + JSON kit: FastAPI mutable-state API tests use explicit providers and dependency overrides; Playwright tests use the generic generated-prototype `data-prototype-id` anchor contract with `getByTestId`.
- **Method contracts** below define the allowed shape for recurring validation methods. Agents should follow these contracts rather than inventing a per-scenario testing style.
- **Concrete run data** must not be promoted into generic method rules. Use names and fields from the current `scheme_model` and `file_plan`.

## Available method ids

- `backend.pytest.api.mutable-state` — see `instructions/testing/backend-pytest-methods.md`.
- `backend.pytest.service.unit` — see `instructions/testing/backend-pytest-methods.md`.
- `backend.smoke.import-health` — see `instructions/testing/backend-pytest-methods.md`.
- `web.ui.static-anchors` — see `instructions/testing/ui-static-methods.md`.
- `web.e2e.playwright.crud-list-search-flow` — see `instructions/testing/browser-playwright-methods.md`.
- `web.e2e.playwright.form-submit-flow` — see `instructions/testing/browser-playwright-methods.md`.
- `web.e2e.playwright.item-action-flow` — see `instructions/testing/browser-playwright-methods.md`.
- `web.e2e.playwright.async-state-transition` — see `instructions/testing/browser-playwright-methods.md`.
- `web.e2e.playwright.filtered-list-flow` — see `instructions/testing/browser-playwright-methods.md`.
- `web.e2e.playwright.count-assertion` — see `instructions/testing/browser-playwright-methods.md`.
