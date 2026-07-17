# Browser Playwright implementation additions

Additional reads and rules:
- instructions/testing/browser-playwright-methods.md
- instructions/testing/browser-e2e.md, if creating or updating browser/e2e tests
- Browser/e2e tests must use repeatable test-owned data, scoped prototype anchors, awaited Playwright async locator APIs, and visible-state waits after async UI transitions before derived assertions. Treat `data-prototype-id` as the kit's generic stable UI contract. Do not inspect backend storage files directly from Playwright.
- For repeated item actions, first locate the item/card and then call actions inside that locator. Avoid chained `>> text=... >>` selector strings for row actions.
- For every new or changed visible value that the browser/e2e spec must assert, add a row/card display anchor such as `field.<entity>-<field>-display` in the generated UI and assert it with `row.getByTestId(...)`. Avoid `row.locator('td').nth(...)` unless the test derives the index from the visible header or an existing table contract explicitly fixes the column order.
- For generated forms, add auxiliary `form.<entity>` and `field.<entity>-<field>` anchors and use them in browser/e2e. Do not write tests that locate inputs via `getByText('Label').locator('input')` or by global form roles.
- For native HTML `<select>` controls with asynchronously loaded options, wait for the select itself and for the expected option text/value to be present in the DOM; do not assert `toBeVisible()` on `<option>` elements.
- If a requirement names multiple searchable fields, implement and test that user-visible capability. Either make one free-text search cover all named fields, or render explicit controls for them.
- For enumerated fields in browser/e2e, assert the intended user-visible display value rather than assuming the raw API value is rendered.
- For mutable create/edit flows, keep any search/filter value that depends on edited fields or relationships in parent-scope variables or a small runtime expectation object. Update that same current value immediately after the edit succeeds. Later filter assertions must use the current value/id, not an initial fixture option, first loaded option, or stale pre-edit value.
- Before finishing any modified Playwright spec, do a final current-state pass: for each later search/filter assertion that expects a runtime-edited row/card to be visible, verify that the filter value was taken from the row/card's current post-edit state. If the filter uses an old value intentionally, assert that the edited row/card is absent under the old value and present under the new current value.
