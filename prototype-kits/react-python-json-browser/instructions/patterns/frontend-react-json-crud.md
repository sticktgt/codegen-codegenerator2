# Pattern: React CRUD/list/search screen for JSON-backed prototypes

Use this pattern for a browser prototype screen that lists records, creates records, edits records, and filters/searches records through the backend API.

## Recommended shape

- Keep backend API calls in small functions or action files only when those files are in `file_plan.json`; otherwise keep screen-internal handlers inside the planned screen artifact.
- Use the same API route shape as the backend tests. Do not invent a different prefix in the frontend.
- Load records when the screen mounts and refresh state after create/edit operations through the public API response or by reloading the list.
- Keep local form state separate from list state. Reset form state after successful create/edit.
- Implement search either by calling the backend search endpoint or by filtering the loaded list, according to the requirement and backend API shape. Do not mix both shapes in tests and UI.

## Anchor and selector shape

- Put the `screen.*` anchor on the screen root element only once.
- Put the `widget.*` anchor on the widget root element only once.
- Put `action.*` anchors on the actual clickable controls that perform those actions. For create, put `action.create-*` on the final submit/save control that creates the record, not on the opener that only shows the form.
- Use the exact scheme id for action anchors. Do not invent derived ids such as `action.create-note-submit` when the scheme id is `action.create-note`.
- If one submit control switches between create and edit modes, render static literal alternatives, for example `data-prototype-id={editing ? 'action.edit-note' : 'action.create-note'}`, or render separate conditional buttons with literal anchors.
- If the UI has a separate "open create form" button, do not give it the same scheme action anchor as the submit button. Use an auxiliary non-scheme anchor such as `data-prototype-id="control.open-create-note"` or a distinct accessible name.
- Keep the opener and submitter accessible names distinct. For example, use "Create Note" for the opener and "Save note"/"Create" inside a scoped form for the submitter; browser tests must scope the submit click to the form.
- For repeated row actions, each edit button may share `data-prototype-id="action.edit-note"`; browser tests should scope to the row containing the runtime-created record before clicking.

## Browser-flow testability

- Prefer one compact browser spec for the CRUD/list/search screen that proves the main user journey: create a runtime-owned record, see it in the list, edit it, and search/filter for it. Use backend pytest for detailed API edge cases.
- Browser/e2e tests should create their own runtime-unique records before editing or searching for them.
- Do not depend on mutable seed records such as "Welcome Note" or "Shopping List" for mutating flows. Avoid browser tests whose primary assertion is that a seed record is visible on initial load; this is fragile across validation reruns and repair loops unless the test controls the dataset through public API setup or an isolated fixture.
- Prefer a single browser journey that creates one or two runtime-owned records and then verifies list/edit/search behavior for those records. Do not add separate seed/empty-state/browser edge-case tests when backend pytest already covers the API behavior.
- Do not split every small acceptance criterion into a separate browser spec if those checks share the same screen state. Multiple validation checks may reference the same browser spec file.
- Scope assertions and clicks through screen/widget/form/row anchors. Avoid page-wide `getByText(runtimeText)` when title/content may duplicate; first locate the record row/card, then assert heading/content inside that row/card with exact matching.
- Avoid ambiguous submit selectors. A selector like `getByRole('button', { name: 'Create' })` can match both an opener named "Create Note" and a submitter named "Create". Browser tests should first open the form through `control.open-create-note`, then scope the submit button through the visible form or click `getByTestId('action.create-note')` when that anchor is on the submit control.
- If the UI has repeated records, give each rendered row/card a stable auxiliary anchor such as `data-prototype-id="item.note"` or an equivalent accessible role/name, then scope row actions and row assertions inside that row/card. Auxiliary item anchors are not scheme ids and may repeat across list items.
- Verify behavior through visible UI state or public API behavior. Do not read backend JSON storage files from Playwright.

## Common first-pass mistakes to avoid

- Frontend calls `/notes` while backend exposes `/api/notes`, or vice versa.
- Search test uses a query string that does not actually match the seeded title/content.
- E2E test clicks the first edit button instead of the edit button inside the row for the record it created.
- E2E test changes a failing `Create` submit selector to the `Create Note` opener, so the form opens but the record is never submitted. Scope the submit button to the form instead.
- Tests use fixed titles, causing reruns or repair loops to collide with previous data.
