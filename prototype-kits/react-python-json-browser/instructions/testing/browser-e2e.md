# Browser/e2e rules

Read `instructions/testing/test-method-catalog.md` first and use the matching Playwright method. For a single CRUD/list/search screen, the default is `web.e2e.playwright.crud-list-search-flow` plus the form, item-action, filtered-list, async-state, and count methods where relevant.

Browser/e2e tests validate user-visible behavior through the browser. They should be small, stable, and scoped to UI contracts.

- Prefer one compact browser spec for a related flow instead of one spec per requirement when the same screen state covers them. For `web.e2e.playwright.crud-list-search-flow`, implement one main `test(...)` with `test.step(...)` sections; do not generate many independent Playwright tests that share mutable backend/browser state.
- Use runtime-unique test data created by the test through the UI. Do not depend on mutable seed records for mutating flows.
- Use `data-prototype-id` anchors and accessible roles/names. Do not read backend JSON storage files from Playwright.
- Start from the actual rendered entry point of the kit. For this React browser kit, the baseline `App.jsx` renders `routes[0].component` and does not render a navigation menu. Do not make Playwright click a route link such as `Customers` unless that link is implemented by the app. Prefer `await page.goto('/')` plus a screen-root assertion, or use the exact route contract that the template already supports.
- Opener controls and submit actions are different: click an auxiliary opener such as `control.open-create-<entity>`, then scope the submit/save click to the visible form and submit action anchor. The opener is not the scheme action; the submit/save control is. If the UI uses a separate open-create button, do not put `action.create-<entity>` on that opener and do not make the test click `action.create-<entity>` to open the form.
- Generated forms should expose a stable auxiliary form anchor such as `form.<entity>` when tests need to scope fields and submit controls. Generated form fields should expose auxiliary field anchors such as `field.<entity>-title`, `field.<entity>-status`, and `field.<entity>-due-date`.
- For repeated rows/cards, locate the row/card first and then click/assert inside that locator:
  - `const row = page.getByTestId('item.note').filter({ hasText: runtimeTitle });`
  - `await row.getByTestId('action.edit-note').click();`
- Avoid chained selector strings for row actions, especially `[data-prototype-id="item.note"] >> text=${title} >> [data-prototype-id="action.edit-note"]`; this is fragile and can search below the text node instead of the row.
- Treat create/edit/delete/search/filter/tab/navigation as async UI state transitions. Wait for a positive visible result before count or absence assertions. For search/filter changes, wait for the runtime-owned expected row/card that matches the new criteria to be visible before reading `count()`. Before full-list count assertions, explicitly reset search/filter state and wait for every runtime-owned row/card that the next assertion depends on, not just one arbitrary row.
- When a visible Clear/Reset control exists, browser/e2e should exercise that real control from a non-empty search/filter state. Do not pre-empty the input before clicking Clear, because that can hide a stale-state reset bug in the product code. After clicking Clear/Reset, assert that every resettable input/control is visibly empty or reset, then wait for at least two runtime-owned rows/cards that prove the list is no longer filtered whenever the flow has full-list/reset semantics. Use records that differ on the active search/filter dimension, for example two different categories or a row that was excluded by the filter. A single matching row plus `count >= 1` is not enough to prove that Clear restored the unfiltered list.
- For explicit multi-field search requirements, browser coverage must follow the user wording. If users must search by name, email, or phone, the generated UI and e2e must demonstrate name search, email search, and phone search, or one generic search input that demonstrably matches all three fields. Each search step must use a value that is currently visible in a runtime-owned row/card, fill/clear the search input deliberately, wait for that row/card to be visible after the search transition, and only then read `count()` if a count helps.
- After editing a record, use the current user-visible values for later row lookup/search assertions. This applies to any changed field used as a locator or search dimension, not only title/name. If an edit changes email, phone, status, category, date, or another visible field, later assertions/searches for that field must use the edited value or a stable id; do not search by the old value unless the UI intentionally still displays it.
- Keep runtime values that cross `test.step(...)` boundaries in test-function scope. Declare values that will be reused later before the steps, update them when the UI edit changes the record, and avoid introducing variables in one step that are referenced by another step.
- Await Playwright async locator APIs before numeric assertions: `const count = await locator.count(); expect(count).toBeGreaterThan(0);`
- Do not add browser tests for unrequested behavior. For example, do not add delete/confirmation, empty-state, minimal-field, or multi-record edge-case tests unless they are explicitly required and represented in the validation plan. Backend pytest is the normal place for API edge cases.
- Avoid global negative assertions against old text in persistent lists unless the test fully controls the dataset and scopes the old row uniquely.
- For filtered-list behavior, assert a runtime-owned matching row is visible. Use an explicit empty-state assertion only if the UI provides one, or a count assertion only after the dataset is controlled and state has settled. Do not change the product loading UI merely to make a premature count assertion pass; fix the test wait unless the requirement specifies loading behavior.


## Submit success signals

After a create/edit submit, wait for the requested domain outcome rather than an optional UI cleanup side effect.

Preferred success waits:
- created row/card is visible with the runtime-owned title/name/status;
- edited row/card is visible with the edited value;
- status/category/date visible state changed as requested;
- filter/search result contains the runtime-owned row.

Do not add `await expect(form).not.toBeVisible()` as a generic race fix. Use that assertion only when the requirement or approved UI design explicitly says the form must close after submit. A generated form may remain open for additional entry or editing, and that should not fail the e2e flow.

## Enum/status display assertions

For enum/status/category fields, keep API values and visible labels aligned deliberately. If the UI renders human labels such as `In progress`, browser/e2e must assert that visible label, not the raw API value `in_progress`. If the UI is expected to show raw values, render exactly those raw values. Prefer stable attribute anchors such as `field.<entity>-status` for form controls and visible row text or auxiliary field display anchors for row attributes.

Do not repair a failed status assertion by adding waits when the actual problem is value/label mismatch. First inspect the UI rendering and align the test with the intended user-visible value, or align the UI rendering with the acceptance criterion.


## Search/filter wait contract

After filling a search box or selecting a filter, the next assertion should normally be a positive visible-state assertion for a runtime-owned row/card that is expected to match the new criteria:

```javascript
await filter.getByTestId('field.task-status-filter').selectOption('in_progress');
const expectedRow = page.getByTestId('item.task').filter({ hasText: editedTitle });
await expect(expectedRow).toBeVisible();
const count = await page.getByTestId('item.task').count();
expect(count).toBeGreaterThan(0);
```

Avoid this pattern:

```javascript
await filter.getByTestId('field.task-status-filter').selectOption('in_progress');
expect(await page.getByTestId('item.task').count()).toBeGreaterThan(0); // races loading/rendering
```

A transient zero count while the frontend reloads data is not itself a product requirement violation. Repair the Playwright wait first; change loading/rendering behavior only when the acceptance criteria require that UX.

When clearing a search/filter after checking a specific dimension, the reset itself is also asynchronous. For a small controlled browser journey with two runtime-owned records, wait for both rows/cards by their unique visible values before asserting a full-list count:

```javascript
await search.getByTestId('control.clear-search').click();
await expect(page.getByTestId('item.customer').filter({ hasText: runtimeNameA })).toBeVisible();
await expect(page.getByTestId('item.customer').filter({ hasText: runtimeNameB })).toBeVisible();
const count = await page.getByTestId('item.customer').count();
expect(count).toBeGreaterThanOrEqual(2);
```

The clear/reset step should represent what a demonstrator would do: leave the search/filter value active, click the visible Clear/Reset control, and verify every relevant field/control reset plus unfiltered rows. Avoid `fill('')` immediately before clicking Clear unless the actual requirement is to test manual text deletion rather than the Clear control.

Avoid using count as the only proof that a reset completed. For reset/full-list proof, first wait for two runtime-owned rows/cards with different search/filter values to be visible. Counts may be asserted only after those rows are visible. If the reset step only verifies the same row that matched the previous filter, it can pass while the list is still filtered.

When a later search dimension depends on an edited field, keep the current value explicit:

```javascript
let currentPhone = runtimePhone;

await test.step('Edit contact phone', async () => {
  currentPhone = `555-${Date.now()}`;
  await form.getByTestId('field.customer-phone').fill(currentPhone);
  await form.getByTestId('action.edit-customer').click();
  await expect(page.getByTestId('item.customer').filter({ hasText: currentPhone })).toBeVisible();
});

await test.step('Search by phone', async () => {
  await search.getByTestId('field.customer-search-query').fill('');
  await search.getByTestId('field.customer-search-query').fill(currentPhone);
  const phoneRow = page.getByTestId('item.customer').filter({ hasText: currentPhone });
  await expect(phoneRow).toBeVisible();
  const phoneCount = await page.getByTestId('item.customer').count();
  expect(phoneCount).toBeGreaterThanOrEqual(1);
});
```

Do not declare `const editedPhone = ...` inside one `test.step(...)` and reference it from a different step. Also do not search by `runtimePhone` after the edit changed the visible phone to another value. Do not replace the positive row wait with a count-only assertion; a zero count after a search can indicate either a race or that the UI search implementation does not actually cover the searched field.
