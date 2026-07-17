# Browser Playwright repair additions

Additional reads and rules:
- instructions/testing/browser-playwright-methods.md
- instructions/testing/browser-e2e.md
- If Playwright cannot find `getByTestId('...')` while `ui_static` passed, first check whether Playwright is configured with `testIdAttribute: 'data-prototype-id'`. If not, use explicit `[data-prototype-id="..."]` locators or repair the planned config file when writable.
- If Playwright cannot see the planned screen after navigation while `ui_static` passed, inspect `App.jsx` and `routeRegistry.js` before changing the test. For this kit, `App.jsx` renders `routes[0].component`.
- If strict mode or duplicate matches happen inside repeated rows/cards, locate the runtime-owned row/card first, then assert the intended field through a stable display anchor. Do not silence ambiguity with `.first()`, `.last()`, or a guessed table-cell index.
- If `selectOption(...)` fails, inspect whether the option is loaded/created in the current flow and whether the component refreshed its option list after the data-changing action.
- If search/filter e2e fails with premature counts, repair the Playwright flow to wait for expected runtime-owned row/card(s) after the transition before count or absence assertions.
- If a filter e2e expects a runtime-owned row after an edit, verify that the filter value is the row's current post-edit value/id. Repair stale pre-edit filter variables before changing application code. Track the current expected values in one parent-scope variable/object and update it immediately after the edit succeeds.
- If the test reselects or recomputes a filter value from the first fixture option, first API record, first `<option>`, or an old variable after the runtime row was edited, treat that as the primary suspect. Use the edited row/card's current displayed/API value for the matching filter, or split the scenario into an old-value absence assertion followed by a new-value presence assertion.
- If a Clear/Reset flow is stale, repair both the UI handler and e2e where needed: reset all relevant state and prove reset with runtime-owned rows/cards that differ on the active dimension.
- If a table-cell index assertion reads the wrong column, prefer repairing the UI to add a stable display anchor and the spec to use that anchor. Use header-derived indexes only when a stable anchor is not practical and the table contract intentionally fixes order.
- Do not run repeated full browser/e2e diagnostics during one repair attempt. Use the official validation logs first; if a full browser run is still necessary, run it at most once, then restore or ignore generated browser artifacts and do not leave local storage/test-result mutations as semantic changes.
