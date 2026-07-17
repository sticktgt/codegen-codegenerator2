# Browser/e2e rules

Read `instructions/testing/test-method-catalog.md` and `instructions/testing/browser-playwright-methods.md` first and use the matching Playwright method. For a single CRUD/list/search screen, the default is `web.e2e.playwright.crud-list-search-flow` plus the form, item-action, filtered-list, async-state, and count methods where relevant.

Browser/e2e tests validate user-visible behavior through the browser. They should be small, stable, and scoped to UI contracts.

- Prefer one compact browser spec for a related flow instead of one spec per requirement when the same screen state covers them. For `web.e2e.playwright.crud-list-search-flow`, implement one main `test(...)` with `test.step(...)` sections; do not generate many independent Playwright tests that share mutable backend/browser state.
- Use runtime-unique test data created by the test through the UI. Do not depend on mutable seed records for mutating flows.
- Use the kit-wide `data-prototype-id` anchor contract and accessible roles/names. `data-prototype-id` is a generic generated-prototype testability attribute, not a scenario-specific name. Do not read backend JSON storage files from Playwright.
- Start from the actual rendered entry point of the kit. For this React browser kit, the baseline `App.jsx` renders `routes[0].component` and does not render a navigation menu. Do not make Playwright click a route link such as `<resource label>` unless that link is implemented by the app. Prefer `await page.goto('/')` plus a screen-root assertion, or use the exact route contract that the template already supports.
- Opener controls and submit actions are different: click an auxiliary opener such as `control.open-create-<entity>`, then scope the submit/save click to the visible form and submit action anchor. The opener is not the scheme action; the submit/save control is. If the UI uses a separate open-create button, do not put `action.create-<entity>` on that opener and do not make the test click `action.create-<entity>` to open the form.
- Generated forms should expose a stable auxiliary form anchor such as `form.<entity>` when tests need to scope fields and submit controls. Generated form fields should expose auxiliary control anchors such as `field.<entity>-<field>` for every editable field used by the flow. Generated repeated rows/cards should expose auxiliary display anchors such as `field.<entity>-<field>-display` for every visible value that browser/e2e must assert, especially newly added columns or fields.
- For repeated rows/cards, locate the row/card first and then click/assert inside that locator:
  - `const row = page.getByTestId('item.<entity>').filter({ hasText: runtimePrimary });`
  - `await row.getByTestId('action.edit-<entity>').click();`
- For repeated table rows, keep assertions scoped to the row and then to the intended field/display anchor. Do not assert short, numeric, or repeated values with `row.getByText('10')`, `row.getByText('0')`, page-wide text selectors, or a guessed column index; they can match the wrong cell in the same row. Prefer `row.getByTestId('field.<entity>-<field>-display')` for every value that browser/e2e must assert.
- Avoid `row.locator('td').nth(...)` for generated table assertions, especially immediately after adding, removing, or reordering columns. Column-index assertions are allowed only when the test first derives the index from the visible table header or when an existing stable table contract explicitly fixes that order. If a new visible column is required, add a field/display anchor to that cell and assert through the anchor instead of guessing the numeric index.
- Do not use `.first()`, `.last()`, or `.nth()` merely to hide duplicate matches from ambiguous locators. Use `.nth()` only when it represents a stable, intentionally selected element inside a specific row/card. If Playwright strict mode reports duplicate text matches inside a row, repair the selector by scoping to the intended field/cell rather than changing application code or accepting any match.

- Native `<select>` option checks: do not use `toBeVisible()` on `<option>` elements. Options are often reported as hidden by the browser even when the select can choose them. For asynchronously loaded options, first assert the select is visible, then wait for the option to be present, for example `await expect(select.locator('option', { hasText: expectedLabel })).toHaveCount(1);`, and then call `await select.selectOption({ label: expectedLabel });` or select by a known value.
- Async select flow: when a test changes data that feeds a select and then selects a new option, wait until that select contains the new option before selecting it. Do not replace this with page-wide text checks; the proof must be scoped to the select control.
- Option data setup: a browser test must select an option that is known to be present. Either use an option already loaded from fixture/API data, or create the option in the same test flow and wait for the select to refresh before selecting it. Avoid hard-coded option labels/values that are not tied to fixtures or runtime-created data.
- Runtime-related filter values: when a browser flow creates or edits a record with a related value, later filter assertions must use that record's current related id/value. Do not pick `options[0]`, the first API fixture, or a hard-coded label unless the runtime record is known to use it. Keep the selected id/value in a parent-scope variable and update it after edit steps.
- Avoid chained selector strings for row actions, especially `[data-prototype-id="item.<entity>"] >> text=${title} >> [data-prototype-id="action.edit-<entity>"]`; this is fragile and can search below the text node instead of the row.
- Treat create/edit/delete/search/filter/tab/navigation as async UI state transitions. Wait for a positive visible result before count or absence assertions. For search/filter changes, wait for the runtime-owned expected row/card that matches the new criteria to be visible before reading `count()`. Before full-list count assertions, explicitly reset search/filter state and wait for every runtime-owned row/card that the next assertion depends on, not just one arbitrary row.
- When a visible Clear/Reset control exists, browser/e2e should exercise that real control from a non-empty search/filter state. Do not pre-empty the input before clicking Clear, because that can hide a stale-state reset bug in the application code. After clicking Clear/Reset, assert that every resettable input/control is visibly empty or reset, then wait for at least two runtime-owned rows/cards that prove the list is no longer filtered whenever the flow has full-list/reset semantics. Use records that differ on the active search/filter dimension, for example two records with different values on the active filter dimension. A single matching row plus `count >= 1` is not enough to prove that Clear restored the unfiltered list.
- For explicit multi-field search requirements, browser coverage must follow the user wording. If users must search by several named fields, the generated UI and e2e must demonstrate every named search dimension, or one generic search input that demonstrably matches all of them. Each search step must use a value that is currently visible in a runtime-owned row/card, fill/clear the search input deliberately, wait for that row/card to be visible after the search transition, and only then read `count()` if a count helps.
- After editing a record, use the current user-visible values for later row lookup/search assertions. This applies to any changed field used as a locator or search dimension, not only the primary display field. If an edit changes another visible field, later assertions/searches for that field must use the edited value or a stable id; do not search by the old value unless the UI intentionally still displays it.
- Keep runtime values that cross `test.step(...)` boundaries in test-function scope. Declare values that will be reused later before the steps, update them when the UI edit changes the record, and avoid introducing variables in one step that are referenced by another step.
- If a test edits a field that is later used as a filter value, update the parent-scope runtime variable and filter by that current value/id. Do not filter by the first fixture option or an old value and then expect the edited runtime row to remain visible.
- Await Playwright async locator APIs before numeric assertions: `const count = await locator.count(); expect(count).toBeGreaterThan(0);`
- Do not add browser tests for unrequested behavior. For example, do not add delete/confirmation, empty-state, minimal-field, or multi-record edge-case tests unless they are explicitly required and represented in the validation plan. Backend pytest is the normal place for API edge cases.
- Avoid global negative assertions against old text in persistent lists unless the test fully controls the dataset and scopes the old row uniquely.
- For filtered-list behavior, assert a runtime-owned matching row is visible. Use an explicit empty-state assertion only if the UI provides one, or a count assertion only after the dataset is controlled and state has settled. Do not change the list loading UI merely to make a premature count assertion pass; fix the test wait unless the requirement specifies loading behavior.



## Mutable related-value filter flows

When a browser/e2e flow creates a record and later edits a field or relationship that affects a search/filter dimension, every later filter assertion must use the record's current post-edit value/id for that dimension. Alternatively, perform the filter assertion before the edit step, or create a separate runtime-owned record dedicated to the filter assertion.

Do not filter by an initial related value, a first fixture option, or a pre-edit label while expecting a record that was edited to a different related value to remain visible. Keep runtime values in test-function scope, update them immediately after the UI edit succeeds, and base later API/UI filter assertions on those updated variables.

If a flow verifies both old and new related values, make the expectation explicit: the edited record should disappear from the old-value filter and appear under the new-value filter. Do not mix these two assertions accidentally in the same step.

### Runtime expectation ledger

For mutable browser/e2e flows, keep a small runtime expectation ledger in the test body. This is not a framework helper; it can be a few parent-scope variables or a plain object. The ledger should store only values that later steps depend on for row lookup, display assertions, search, or filters.

Use one canonical current value per dimension:

```javascript
const runtimeRecord = {
  primaryText: runtimePrimaryText,
  relatedId: initialRelatedId,
  relatedFilterValue: initialRelatedFilterValue,
};
```

When an edit changes a relationship or a field that affects a later filter/search assertion, update the same ledger variables immediately after the edit succeeds and before any later filter step:

```javascript
await test.step('edit a related value', async () => {
  runtimeRecord.relatedId = editedRelatedId;
  runtimeRecord.relatedFilterValue = editedRelatedFilterValue;
  await form.getByTestId('field.<entity>-related-id').selectOption(runtimeRecord.relatedId);
  await form.getByTestId('action.edit-<entity>').click();
  await expect(row.getByTestId('field.<entity>-related-value-display')).toHaveText(runtimeRecord.relatedFilterValue);
});

await test.step('filter by the current related value', async () => {
  await filter.getByTestId('field.<entity>-related-filter').selectOption(runtimeRecord.relatedFilterValue);
  await expect(page.getByTestId('item.<entity>').filter({ hasText: runtimeRecord.primaryText })).toBeVisible();
});
```

Do not recompute later filter values from the first available fixture, the first `<option>`, or an earlier variable after the record has been edited. Before every filter/search step that expects the mutable record to remain visible, perform a quick mental check: “Does this filter value equal the record's current displayed/API value after the latest edit?” If not, update the ledger or move the filter check before the edit.

If the flow intentionally validates the old filter value after an edit, assert the opposite behavior explicitly: the edited record should not be visible under the old value and should be visible under the new current value.

## Submit success signals

After a create/edit submit, wait for the requested domain outcome rather than an optional UI cleanup side effect.

Preferred success waits:
- created row/card is visible with the runtime-owned values;
- edited row/card is visible with the edited value;
- the relevant visible state changed as requested;
- filter/search result contains the runtime-owned row.

Do not add `await expect(form).not.toBeVisible()` as a generic race fix. Use that assertion only when the requirement or approved UI design explicitly says the form must close after submit. A generated form may remain open for additional entry or editing, and that should not fail the e2e flow.

## Enumerated-value display assertions

For enumerated fields, keep API values and visible labels aligned deliberately. If the UI renders a user-facing label, browser/e2e must assert that label rather than assuming the raw API value is shown. If the UI is expected to show raw values, render exactly those raw values. Prefer stable anchors such as `field.<entity>-<field>` for controls and visible row text or auxiliary field-display anchors for row attributes.

Do not repair a failed enumerated-value assertion by adding waits when the actual problem is value/label mismatch. First inspect the UI rendering and align the test with the intended user-visible value, or align the UI rendering with the acceptance criterion.


## Search/filter wait contract

After filling a search box or selecting a filter, the next assertion should normally be a positive visible-state assertion for a runtime-owned row/card that is expected to match the new criteria:

```javascript
await filter.getByTestId('field.<entity>-<filter-field>').selectOption(runtimeFilterValue);
const expectedRow = page.getByTestId('item.<entity>').filter({ hasText: editedTitle });
await expect(expectedRow).toBeVisible();
const count = await page.getByTestId('item.<entity>').count();
expect(count).toBeGreaterThan(0);
```

Avoid this pattern:

```javascript
await filter.getByTestId('field.<entity>-<filter-field>').selectOption(runtimeFilterValue);
expect(await page.getByTestId('item.<entity>').count()).toBeGreaterThan(0); // races loading/rendering
```

A transient zero count while the frontend reloads data is not itself an application requirement violation. Repair the Playwright wait first; change loading/rendering behavior only when the acceptance criteria require that UX.

When clearing a search/filter after checking a specific dimension, the reset itself is also asynchronous. For a small controlled browser journey with two runtime-owned records, wait for both rows/cards by their unique visible values before asserting a full-list count:

```javascript
await search.getByTestId('control.clear-search').click();
await expect(page.getByTestId('item.<entity>').filter({ hasText: runtimeValueA })).toBeVisible();
await expect(page.getByTestId('item.<entity>').filter({ hasText: runtimeValueB })).toBeVisible();
const count = await page.getByTestId('item.<entity>').count();
expect(count).toBeGreaterThanOrEqual(2);
```

The clear/reset step should represent what a demonstrator would do: leave the search/filter value active, click the visible Clear/Reset control, and verify every relevant field/control reset plus unfiltered rows. Avoid `fill('')` immediately before clicking Clear unless the actual requirement is to test manual text deletion rather than the Clear control.

Avoid using count as the only proof that a reset completed. For reset/full-list proof, first wait for two runtime-owned rows/cards with different search/filter values to be visible. Counts may be asserted only after those rows are visible. If the reset step only verifies the same row that matched the previous filter, it can pass while the list is still filtered.

When a later search dimension depends on an edited field, keep the current value explicit:

```javascript
let currentSearchValue = runtimeSearchValue;

await test.step('edit a searchable field', async () => {
  currentSearchValue = `Runtime search ${Date.now()}`;
  await form.getByTestId('field.<entity>-<field>').fill(currentSearchValue);
  await form.getByTestId('action.edit-<entity>').click();
  await expect(page.getByTestId('item.<entity>').filter({ hasText: currentSearchValue })).toBeVisible();
});

await test.step('search by the edited field', async () => {
  await search.getByTestId('field.<entity>-search-query').fill('');
  await search.getByTestId('field.<entity>-search-query').fill(currentSearchValue);
  const matchingRow = page.getByTestId('item.<entity>').filter({ hasText: currentSearchValue });
  await expect(matchingRow).toBeVisible();
  const matchingCount = await page.getByTestId('item.<entity>').count();
  expect(matchingCount).toBeGreaterThanOrEqual(1);
});
```

Do not declare a changed search value inside one `test.step(...)` and reference it from a different step. Also do not search by a pre-edit value after the edit changed the visible value. Do not replace the positive row wait with a count-only assertion; a zero count after a search can indicate either a race or that the UI search implementation does not actually cover the searched field.
