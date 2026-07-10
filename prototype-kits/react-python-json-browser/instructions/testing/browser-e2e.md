# Browser/e2e rules

Read `instructions/testing/test-method-catalog.md` first and use the matching Playwright method. For a single CRUD/list/search screen, the default is `web.e2e.playwright.crud-list-search-flow` plus the form, item-action, filtered-list, async-state, and count methods where relevant.

Browser/e2e tests validate user-visible behavior through the browser. They should be small, stable, and scoped to UI contracts.

- Prefer one compact browser spec for a related flow instead of one spec per requirement when the same screen state covers them.
- Use runtime-unique test data created by the test through the UI. Do not depend on mutable seed records for mutating flows.
- Use `data-prototype-id` anchors and accessible roles/names. Do not read backend JSON storage files from Playwright.
- Opener controls and submit actions are different: click an auxiliary opener such as `control.open-create-note`, then scope the submit/save click to the visible form or to the submit action anchor.
- For repeated rows/cards, locate the row/card first and then click/assert inside that locator:
  - `const row = page.getByTestId('item.note').filter({ hasText: runtimeTitle });`
  - `await row.getByTestId('action.edit-note').click();`
- Avoid chained selector strings for row actions, especially `[data-prototype-id="item.note"] >> text=${title} >> [data-prototype-id="action.edit-note"]`; this is fragile and can search below the text node instead of the row.
- Treat create/edit/delete/search/filter/tab/navigation as async UI state transitions. Wait for a positive visible result before count or absence assertions.
- Await Playwright async locator APIs before numeric assertions: `const count = await locator.count(); expect(count).toBeGreaterThan(0);`.
- Avoid global negative assertions against old text in persistent lists unless the test fully controls the dataset and scopes the old row uniquely.
- For filtered-list behavior, assert a runtime-owned matching row is visible. Use an explicit empty-state assertion only if the UI provides one, or a count assertion only after the dataset is controlled and state has settled.
