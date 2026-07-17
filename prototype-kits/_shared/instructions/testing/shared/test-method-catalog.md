# Test method catalog

Use this catalog to choose validation methods for this kit. Do not invent a new testing style when one of these methods matches the planned artifact and acceptance criterion. Add new method entries here when a future kit or scenario needs a genuinely different testing approach.

Each validation check should include `test_method_id` with one of the ids below. The id is a method contract for the agent and reviewer. The file plan and validation runner remain the execution source of truth, but implementation and repair must follow the selected method instead of mixing styles.

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

## backend.pytest.api.mutable-state

Use for Python backend API behavior when endpoints read or mutate JSON files, SQLite files, in-memory repositories, mock adapters, or other external/mutable state.

Contract for this FastAPI kit:
- Test through the public API using `TestClient`.
- Generated API routes that use mutable state must expose a provider function such as `get_<entity>_service()` in the API module.
- Route handlers must receive the service through `Depends(get_<entity>_service)`. Do not hide the service only in a module-level singleton that tests cannot override.
- Feature pytest fixtures must import the provider function directly from the API module and override that exact function: `from app.api.<entity> import get_<entity>_service`; `app.dependency_overrides[get_<entity>_service] = lambda: <Service>(storage_path=temp_file)`.
- Generated browser-backed CRUD APIs must use one request payload contract across backend, frontend, and pytest. For this kit, `POST` create and `PUT`/`PATCH` update endpoints should accept JSON request bodies through Pydantic request models; `GET` list/search/filter endpoints may use query parameters. Frontend `fetch` calls and backend pytest must use the same shape (`json=`/JSON body for create/update, `params`/query string for list filters).
- For new FastAPI JSON-backed resources in this kit, use one standard public path: `/api/<resources>`. Implement it as router `prefix="/<resources>"` plus `app.include_router(router, prefix="/api")`; backend pytest and frontend calls should use `/api/<resources>`. Do not silently adapt tests to an unplanned route-prefix mismatch.
- Clear dependency overrides in fixture teardown.
- Do not introspect FastAPI route internals to find dependencies. Never use `app.routes[...]`, `.dependencies`, `dependant`, or route-order indexes as the key for `app.dependency_overrides`; these are framework internals, not the provider contract.
- Each test or fixture owns a fresh temp storage path. Do not symlink or overwrite tracked mock JSON files.
- The service/storage layer must preserve the injected test resource identity. Do not let implementation convert an injected temp path, repository, adapter, client, or config to a basename, default resource, global singleton, or planned production mock; that breaks test isolation even when dependency override is correct. For JSON storage this means using the full injected path for reads and writes.
- Do not rewrite implementation `.py` files from pytest fixtures and do not depend on records created by earlier tests.

Use this method for API edge cases, request validation, not-found cases, and most negative cases. Do not move these edge cases into browser/e2e unless they are explicitly user-visible UI behavior.

For future non-FastAPI stacks, add a separate method or stack-specific example instead of weakening this kit method.

## backend.pytest.service.unit

Use for pure service/model logic that is not primarily an HTTP contract and does not need the app router.

Expected shape:
- Instantiate the service/model directly with isolated dependencies.
- Test deterministic inputs and outputs.
- Avoid filesystem/network state unless the service responsibility is specifically about that adapter.

## backend.smoke.import-health

Use only to rerun baseline import/health/route sanity checks already present in the kit.

Expected shape:
- `backend/tests/test_smoke.py` is normally read-only rerun coverage.
- Do not create, extend, or modify smoke tests for feature-specific API behavior.
- Feature behavior belongs in a feature API test such as `backend/tests/test_<feature>_api.py` or in a service test when appropriate.

## web.ui.static-anchors

Use for non-executable UI anchor checks.

Expected shape:
- `proposed_file` is `null` and there is no `validation_intent`.
- The implementation file must contain the exact `data-prototype-id` anchors for the relevant `screen.*`, `widget.*`, and directly rendered `action.*` scheme elements.
- This method does not create a test file and does not prove behavior.

## web.e2e.playwright.crud-list-search-flow

Use for a single user-facing create/edit/list/search or CRUD-like screen. The method name is historical: it does **not** grant permission to test delete, confirmation, bulk operations, minimal-field edge cases, or multiple-record edge cases unless those behaviors are explicitly required by the current requirements and validation plan.

Contract for this React + Playwright kit:
- Prefer one compact Playwright spec for the user journey. For this method, "one compact spec" means one main `test(...)` with `test.step(...)` sections for create/edit/list/search/filter behavior, not many independent Playwright `test(...)` cases that share mutable backend state.
- Compose this method with `form-submit-flow`, `item-action-flow`, `async-state-transition`, `filtered-list-flow`, and `count-assertion` where relevant.
- Create runtime-unique records through the UI before editing or searching for them. For search/filter contrast, create at most the records needed by the visible user journey, normally one primary record and optionally one contrast record.
- Scope interactions through stable anchors: `screen.*`, `widget.*`, `form.*`, `field.*`, `item.*`, `control.*`, and `action.*`. The `data-prototype-id` attribute is the kit-wide testability contract for these anchors, not a scenario-specific name.
- Use the kit's real app entry and route registry shape. In this kit `App.jsx` renders the first `routes[]` entry through its `component` property and does not provide generated navigation links by default. Browser tests should not click links that the app does not render, and route integration should not use a different property such as `element` unless the template has been changed to consume it.
- For repeated table/list rows, assertions for field values must be row-scoped and field-scoped. Avoid `getByText()` for short or numeric values such as short numeric values, amount fragments, status codes, or category labels when they may appear in more than one cell. Prefer stable field display anchors such as `field.<entity>-<field>-display`. Do not guess table-cell indexes with `row.locator('td').nth(...)`; use a header-derived index only when the table contract intentionally fixes column order and no display anchor is available.
- Treat opener and submit anchors as a first-pass contract: if the UI has a separate open-create button, the opener must use `control.open-create-<entity>` and the create submit/save control inside `form.<entity>` must use `action.create-<entity>`. The Playwright spec must click the same opener contract rather than falling back to the action anchor.
- Keep search/filter state explicit. After every search/filter input change, first wait for a runtime-owned expected row/card that satisfies the filter to be visible. Only then use `count()` or collection assertions. Before asserting full-list counts or presence of multiple records, clear search/filter controls and wait for all runtime-owned rows/cards that the assertion depends on to be visible. Prefer presence assertions for runtime-owned rows over global exact counts unless the test fully controls the visible dataset and every filter/search control is known to be reset.
- Cover explicit search dimensions from the requirement. If a requirement names several searchable fields, the UI must make all of those user-visible search dimensions reachable: either one generic text search that searches across all named fields, or explicit controls for each named field. The compact e2e spec should exercise each explicitly named search dimension at least once when there are only a few; otherwise document which dimensions are representative and why.
- After a mutation changes any visible field used later for row lookup or search, use the current updated value for subsequent assertions. This includes every visible or requirement-named search dimension. If a test edits a searchable field and later searches by that field, it must use the edited value rather than the original value.
- Values reused across `test.step(...)` sections must be declared in the parent test scope and assigned/updated deliberately. Do not declare a value inside one step and reference it from a later step; this leads to repair-only scoping failures such as `ReferenceError`.
- Do not assert optional UI cleanup state such as `expect(form).not.toBeVisible()` unless the requirement explicitly says the form must close. After submit, wait for the domain outcome that proves success: created row visible, updated row visible, status changed, filter result visible, etc. A form remaining open can be a valid UI design.
- Backend pytest covers API edge cases and negative cases; the browser test proves the user-visible journey. Do not duplicate backend API edge cases as separate browser tests.

## web.e2e.playwright.form-submit-flow

Use when a UI action is performed through a form.

Expected shape:
- If a separate button only opens a form, anchor it as an auxiliary control such as `control.open-create-<entity>`; it is not the scheme action.
- Put the scheme `action.create-*` or `action.edit-*` anchor on the submit/save control that actually performs the mutation. Do not put the same `action.create-*` anchor on both the opener and the submit button. If the e2e uses `control.open-create-*`, the generated UI must render that exact opener anchor.
- Generated forms should have a stable auxiliary form anchor such as `form.<entity>` when the test needs to scope fields and submit controls.
- Generated form fields should have stable auxiliary field anchors such as `field.<entity>-title`, `field.<entity>-status`, or `field.<entity>-due-date`. These anchors are not scheme elements; they are testability anchors for fields.
- In tests, click the opener, locate the visible form by `getByTestId('form.<entity>')`, fill fields inside that scope by `getByTestId('field.<entity>-<field>')`, and click the submit action inside that same form scope.
- Do not depend on label text being an ancestor of an input, for example `getByText('Primary field:').locator('input')`. If using accessible labels, the UI must still provide correct `htmlFor`/`id`, but field anchors are preferred for generated e2e tests in this kit.
- Avoid page-wide role/text selectors for ambiguous buttons such as `Create`, `Save`, or `Edit`.

## web.e2e.playwright.item-action-flow

Use when interacting with repeated row/card actions.

Expected shape:
- Render each repeated row/card with a stable auxiliary item anchor such as `data-prototype-id="item.<entity>"` or an equivalent role/name.
- In tests, first locate the row/card for the runtime-created record, then click the action inside that row/card.
- For row/card assertions, first locate the runtime-owned row/card, then assert the specific field/cell inside it. Do not use `.first()`/`.last()` to disambiguate repeated action or text anchors unless the selection is tied to a documented UI contract; ambiguous selectors should be repaired to a stable row/field/cell locator.
- Preferred style:
  `const row = page.getByTestId('item.<entity>').filter({ hasText: runtimePrimary });`
  `await row.getByTestId('action.edit-<entity>').click();`
- Avoid chained text/CSS selector strings such as `[data-prototype-id="item.<entity>"] >> text=${title} >> [data-prototype-id="action.edit-<entity>"]`; they are fragile and may look for a descendant of a text node rather than the row action.

## web.e2e.playwright.async-state-transition

Use after any UI action that changes page state: create/edit/delete, submit form, search/filter, clear input, switch tab, navigate, or reload data.

Expected shape:
- Wait for a user-visible result before derived assertions.
- Prefer positive visible-state assertions on a scoped row/card/control that represents the requested domain outcome. Do not use negative assertions about optional UI state, such as form disappearance, as a generic submit-success signal.
- Only after visible state is settled, compute `count()` or assert collection size. For filter/search flows, the settling signal should be the expected runtime-owned row/card becoming visible, not just the screen root or widget staying visible.
- Avoid fragile negative assertions against old text in mutable lists unless the test owns the dataset and can uniquely scope the old record.

## web.e2e.playwright.filtered-list-flow

Use for search/filter behavior on a list.

Expected shape:
- Match the user's search model, not just the backend endpoint shape. For explicit multi-field search requirements, prove through the browser that the user can search by the named fields or by a single free-text query that matches all named fields.
- Create or otherwise control the records being filtered.
- Filter for a runtime-owned value and assert the matching row/card is visible before any derived count assertion. A transient zero count during loading is a test timing problem unless the user requirement explicitly says the list must remain populated while loading.
- For each named field/dimension in a multi-field search requirement, search by a value currently visible in a runtime-owned row/card. If an earlier edit changed that field, use the updated current value and keep it in parent test scope across `test.step(...)` sections.
- For non-matching filters, prefer an explicit empty-state UI if the app has one; otherwise avoid global `toHaveCount(0)` on persistent lists unless the dataset is controlled by the test.
- Clearing a filter is an async state transition: wait for every runtime-owned row/card needed by the following assertion to become visible before asserting counts. If multiple explicit search dimensions are tested in one flow, clear all search/filter controls between dimensions and prove the reset by visible runtime-owned rows, not by an immediate exact count alone.
- When a generated Clear/Reset control exists, the e2e must click that control from a non-empty search/filter state. Do not pre-clear the input before clicking the generated control; otherwise the test can hide a stale-state implementation bug. If the reset is supposed to return to an unfiltered/full list, prove it with two runtime-owned rows/cards that differ on the active search/filter dimension, not with the same row that was already visible under the filter.
- Do not repair a search/filter timing failure by changing list loading behavior unless the implementation violates a requirement. Prefer a stable Playwright wait on the expected visible filtered result.

## web.e2e.playwright.count-assertion

Use only after visible state has settled.

Expected shape:
- `const count = await locator.count();`
- `expect(count).toBeGreaterThan(0);`
- Never pass a Promise to Jest/Playwright assertions, for example `expect(locator.count()).toBeGreaterThan(...)`.

## Enumerated-value display assertions

For enumerated fields, keep API values and visible labels aligned deliberately. If the UI renders a user-facing label, browser/e2e must assert that label rather than assuming the raw API value is shown. If the UI is expected to show raw values, render exactly those raw values. Prefer stable anchors such as `field.<entity>-<field>` for controls and visible row text or auxiliary field-display anchors for row attributes.

Do not repair a failed enumerated-value assertion by adding waits when the actual problem is value/label mismatch. First inspect the UI rendering and align the test with the intended user-visible value, or align the UI rendering with the acceptance criterion.
