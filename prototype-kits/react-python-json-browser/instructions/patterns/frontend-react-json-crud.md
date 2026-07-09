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
- Put `action.*` anchors on the actual clickable controls that perform those actions.
- For repeated row actions, each edit button may share `data-prototype-id="action.edit-note"`; browser tests should scope to the row containing the runtime-created record before clicking.

## Browser-flow testability

- Browser/e2e tests should create their own runtime-unique records before editing or searching for them.
- Do not depend on mutable seed records such as "Welcome Note" or "Shopping List" for mutating flows, and avoid empty-state tests unless the test controls the dataset through public API or an isolated test fixture.
- Scope assertions through screen/widget anchors and through the row/card containing the runtime-owned title. Avoid page-wide `getByText(runtimeText)` when title/content may duplicate; first locate the record row/card, then assert heading/content inside that row/card with exact matching.
- Verify behavior through visible UI state or public API behavior. Do not read backend JSON storage files from Playwright.

## Common first-pass mistakes to avoid

- Frontend calls `/notes` while backend exposes `/api/notes`, or vice versa.
- Search test uses a query string that does not actually match the seeded title/content.
- E2E test clicks the first edit button instead of the edit button inside the row for the record it created.
- Tests use fixed titles, causing reruns or repair loops to collide with previous data.
