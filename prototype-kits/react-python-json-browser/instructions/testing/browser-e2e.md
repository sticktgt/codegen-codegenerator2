# Browser/e2e rules

Read `instructions/testing/test-method-catalog.md` first and use the matching Playwright method. For a single CRUD/list/search screen, the default is `web.e2e.playwright.crud-list-search-flow` plus the form, item-action, filtered-list, async-state, and count methods where relevant.

Browser/e2e tests validate user-visible behavior through the browser. They should be small, stable, and scoped to UI contracts.

- Prefer one compact browser spec for a related flow instead of one spec per requirement when the same screen state covers them. For `web.e2e.playwright.crud-list-search-flow`, implement one main `test(...)` with `test.step(...)` sections; do not generate many independent Playwright tests that share mutable backend/browser state.
- Use runtime-unique test data created by the test through the UI. Do not depend on mutable seed records for mutating flows.
- Use `data-prototype-id` anchors and accessible roles/names. Do not read backend JSON storage files from Playwright.
- Opener controls and submit actions are different: click an auxiliary opener such as `control.open-create-<entity>`, then scope the submit/save click to the visible form and submit action anchor. The opener is not the scheme action; the submit/save control is. If the UI uses a separate open-create button, do not put `action.create-<entity>` on that opener and do not make the test click `action.create-<entity>` to open the form.
- Generated forms should expose a stable auxiliary form anchor such as `form.<entity>` when tests need to scope fields and submit controls. Generated form fields should expose auxiliary field anchors such as `field.<entity>-title`, `field.<entity>-status`, and `field.<entity>-due-date`.
- For repeated rows/cards, locate the row/card first and then click/assert inside that locator:
  - `const row = page.getByTestId('item.note').filter({ hasText: runtimeTitle });`
  - `await row.getByTestId('action.edit-note').click();`
- Avoid chained selector strings for row actions, especially `[data-prototype-id="item.note"] >> text=${title} >> [data-prototype-id="action.edit-note"]`; this is fragile and can search below the text node instead of the row.
- Treat create/edit/delete/search/filter/tab/navigation as async UI state transitions. Wait for a positive visible result before count or absence assertions. For search/filter changes, wait for the runtime-owned expected row/card that matches the new criteria to be visible before reading `count()`. Before full-list count assertions, explicitly reset search/filter state and wait for a known row/card to be visible.
- After editing a record, use the edited user-visible value for later row lookup/search assertions. Do not keep locating the row by the old title unless the UI intentionally still displays that old value.
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
