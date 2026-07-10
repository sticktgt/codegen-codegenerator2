# Test method catalog

Use this catalog to choose validation methods for this kit. Do not invent a new testing style when one of these methods matches the planned artifact and acceptance criterion. Add new method entries here when a future kit or scenario needs a genuinely different testing approach.

Each validation check may include `test_method_id` with one of the ids below. The id is advisory metadata for the agent and reviewer; the file plan and validation runner remain the execution source of truth.

## backend.pytest.api.mutable-state

Use for Python backend API behavior when endpoints read or mutate JSON files, SQLite files, in-memory repositories, mock adapters, or other external/mutable state.

Expected shape:
- Test through the public API using `TestClient` or the kit's equivalent API client.
- Prepare isolated test-owned state for each test or fixture.
- Replace mutable dependencies through an explicit seam: FastAPI `Depends(...)` provider plus `app.dependency_overrides`, app/service factory, constructor injection, repository interface, or exact route-module service replacement.
- Create the test client after dependency replacement if the app or route captures dependencies.
- Do not rewrite implementation `.py` files, symlink tracked storage files, or depend on records created by earlier tests.

Use this method for API edge cases, request validation, not-found cases, and most negative cases. Do not move these edge cases into browser/e2e unless they are explicitly user-visible UI behavior.

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

Use for a single user-facing CRUD/list/search screen.

Expected shape:
- Prefer one compact Playwright spec that covers the main happy path for several related requirements.
- Create runtime-unique records through the UI before editing or searching for them.
- Scope all interactions through stable anchors: screen/widget/form/item/action.
- Backend pytest covers API edge cases and negative cases; the browser test proves the user-visible journey.

## web.e2e.playwright.form-submit-flow

Use when a UI action is performed through a form.

Expected shape:
- If a separate button only opens a form, anchor it as an auxiliary control such as `control.open-create-note`; it is not the scheme action.
- Put the scheme `action.create-*` or `action.edit-*` anchor on the submit/save control that actually performs the mutation.
- In tests, click the opener, locate the visible form or screen region, fill fields inside that scope, and click the submit action inside that same scope.
- Avoid page-wide role/text selectors for ambiguous buttons such as `Create`, `Save`, or `Edit`.

## web.e2e.playwright.item-action-flow

Use when interacting with repeated row/card actions.

Expected shape:
- Render each repeated row/card with a stable auxiliary item anchor such as `data-prototype-id="item.note"` or an equivalent role/name.
- In tests, first locate the row/card for the runtime-created record, then click the action inside that row/card.
- Preferred style:
  `const row = page.getByTestId('item.note').filter({ hasText: runtimeTitle });`
  `await row.getByTestId('action.edit-note').click();`
- Avoid chained text/CSS selector strings such as `[data-prototype-id="item.note"] >> text=${title} >> [data-prototype-id="action.edit-note"]`; they are fragile and may look for a descendant of a text node rather than the row action.

## web.e2e.playwright.async-state-transition

Use after any UI action that changes page state: create/edit/delete, submit form, search/filter, clear input, switch tab, navigate, or reload data.

Expected shape:
- Wait for a user-visible result before derived assertions.
- Prefer positive visible-state assertions on a scoped row/card/control.
- Only after visible state is settled, compute `count()` or assert collection size.
- Avoid fragile negative assertions against old text in mutable lists unless the test owns the dataset and can uniquely scope the old record.

## web.e2e.playwright.filtered-list-flow

Use for search/filter behavior on a list.

Expected shape:
- Create or otherwise control the records being filtered.
- Filter for a runtime-owned value and assert the matching row/card is visible.
- For non-matching filters, prefer an explicit empty-state UI if the app has one; otherwise avoid global `toHaveCount(0)` on persistent lists unless the dataset is controlled by the test.
- Clearing a filter is an async state transition: wait for a known row/card to become visible before asserting counts.

## web.e2e.playwright.count-assertion

Use only after visible state has settled.

Expected shape:
- `const count = await locator.count();`
- `expect(count).toBeGreaterThan(0);`
- Never pass a Promise to Jest/Playwright assertions, for example `expect(locator.count()).toBeGreaterThan(...)`.
