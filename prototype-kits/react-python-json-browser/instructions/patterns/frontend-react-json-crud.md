# Pattern: React JSON CRUD/list/search screen

Use this pattern for small React screens backed by the kit FastAPI JSON CRUD service.

## Component shape

- Keep route wiring in `frontend/src/routes/routeRegistry.js` or another planned integration file.
- Match the current kit route registry contract exactly. In this kit `frontend/src/App.jsx` reads `routes[0].component`; generated route entries must use `component: ScreenComponent`, not `element`, and should not invent navigation links unless the template actually renders navigation. Prefer the existing app entry route (`/`) unless the baseline template already supports real client routing for the planned path.
- Keep the main user journey in the planned screen file. For simple CRUD/list/search screens, create/edit handlers may be screen-internal instead of separate action files.
- Use a widget file for reusable visual/input pieces only when planned, such as `NoteSearch.jsx`.
- Match the backend public API path exactly. If FastAPI exposes `/api/notes`, the frontend must call `/api/notes`.

## Anchors and controls

- Put the `screen.*` anchor on the screen root only once.
- Put the `widget.*` anchor on the widget root only once.
- Put scheme `action.*` anchors on the actual controls that perform the action.
- For create/edit forms, distinguish opener, form scope, and submitter:
  - opener: auxiliary anchor such as `control.open-create-note`;
  - form scope: auxiliary anchor such as `form.note` when fields and submit controls need stable scoping;
  - submitter: scheme action anchor such as `action.create-note` or `action.edit-note`.
  If the UI has both an opener and a submitter, these anchors must be different and the browser test must use the same contract.
- Do not invent suffixed scheme ids such as `action.create-note-submit`.
- If one submit button switches modes, use static literal alternatives: `data-prototype-id={editing ? 'action.edit-note' : 'action.create-note'}`.
- For repeated rows/cards, add an auxiliary item anchor such as `data-prototype-id="item.note"`; repeated item anchors are allowed and are used for scoped browser actions.

## Browser-flow testability

Design the UI so the catalog methods in `instructions/testing/test-method-catalog.md` can be used directly:

- A create flow has a stable opener and a scoped submit action.
- A repeated record can be located by an item/card anchor and runtime-owned text.
- The edit action is inside the item/card for the record it edits.
- Search/filter input lives inside the search widget anchor.
- After create/edit/search/filter, the UI exposes a visible row/card state that tests can wait for before count or absence assertions. For filters, the visible state should be a runtime-owned row/card that is expected to match the active filter.
- After an edit changes any visible value used to locate or search a row, subsequent UI assertions should locate/search by the current edited value or by a stable id, not by the pre-edit value. This applies to email/phone/status/category/date fields as well as title/name.

Avoid page designs where browser tests must rely on global text matches, ambiguous `Create`/`Edit` buttons, or hidden implicit state transitions.

## Form and field testability anchors

For generated React forms in this kit, expose stable auxiliary anchors in addition to scheme anchors:

- Form scope: `data-prototype-id="form.<entity>"` on the visible form or form-like container.
- Field controls: `data-prototype-id="field.<entity>-<field>"` on each input/select/textarea used by browser/e2e.
- Opener control: `data-prototype-id="control.open-create-<entity>"` on a button that only opens the form.
- Submit/save control: exact scheme action anchor such as `action.create-<entity>` or `action.edit-<entity>`.
- Repeated rows/cards: `data-prototype-id="item.<entity>"`.

These `form.*`, `field.*`, `control.*`, and `item.*` anchors are auxiliary testability anchors, not scheme elements. They help Playwright use stable scoped locators and avoid fragile label/text/CSS chains. Use accessible labels too where reasonable, but do not make generated e2e depend on label text being an ancestor of the input.

Browser/e2e should fill fields like this:

```javascript
await page.getByTestId('control.open-create-task').click();
const form = page.getByTestId('form.task');
await form.getByTestId('field.task-title').fill(runtimeTitle);
await form.getByTestId('field.task-status').selectOption('todo');
await form.getByTestId('action.create-task').click();
```

Avoid this brittle pattern:

```javascript
await page.getByTestId('action.create-task').click();
const form = page.getByTestId('screen.task-board');
await form.getByText('Title:').locator('input[type="text"]').fill(runtimeTitle);
```

## Search dimension coverage

Do not reduce an explicit multi-field search requirement to the first convenient field. If requirements say users can search by several fields such as name, email, or phone, implement one of these demo-safe UI shapes:

- a single free-text search input whose backend/service search checks all named fields; or
- explicit user-visible controls for each named field.

The browser/e2e flow must prove the same user-visible search dimensions. For a small list of named fields, exercise each one at least once with runtime-owned records. Backend API support for extra query parameters is not enough if the UI only exposes search by one field.

When a generic search box covers multiple fields, the screen implementation must apply the same search query to all named user-visible fields or call an API that does so. Do not implement the UI filter for name/email while the requirement and test also demonstrate phone, category, code, or another field. The e2e should wait for a row containing the same field value it searched for before using any count assertion.

Search/filter reset controls must perform a real user-visible reset. When the UI has a Clear/Reset control, its handler should clear every user-visible search/filter state and reload the unfiltered list using explicit reset arguments. Do not rely on React state having updated synchronously before calling a loader that reads state. Prefer a loader shaped like `fetchItems({ query = '', category = '' })`, then implement reset as `setSearchQuery(''); setCategoryFilter(''); fetchItems({ query: '', category: '' });`. Avoid `setSearchQuery(''); setCategoryFilter(''); fetchItems();` when `fetchItems()` reads `searchQuery` or `categoryFilter` from React state; that can leave the list filtered even though the controls look cleared. The user should be able to click Clear while search/filter controls are non-empty and immediately see the unfiltered runtime-owned rows/cards.


Recommended shape for multi-control search/filter screens:

```javascript
const fetchItems = async ({ query = searchQuery, category = categoryFilter } = {}) => {
  const params = new URLSearchParams();
  if (query) params.append('q', query);
  if (category) params.append('category', category);
  const response = await fetch(`/api/items?${params}`);
  if (response.ok) setItems(await response.json());
};

const handleClearSearch = () => {
  setSearchQuery('');
  setCategoryFilter('');
  fetchItems({ query: '', category: '' });
};
```



## Browser flow scope

For a single create/edit/list/search screen, keep the generated browser test to the requested user journey. Do not add delete/confirmation, empty-state, minimal-field, or multi-record edge-case browser tests unless the current requirements explicitly ask for them. When search/filter is involved, create only the runtime-owned records needed for the flow, wait for the expected filtered row/card after changing filters, and clear filter state before any full-list count assertion.


## Submit and visible outcome contract

Generated CRUD/list/search screens should expose a visible domain outcome after create/edit so browser/e2e can wait on behavior instead of implementation details. Good outcomes include the created row/card, edited title/name, edited status/category, or filtered result.

Do not require the screen to close or hide a form after submit unless the requirement says so. If the form remains open, reset, or switches between create/edit modes, tests should still assert the domain outcome through `item.<entity>` rows/cards rather than assuming `form.<entity>` disappears.

## Enum/status display assertions

For enum/status/category fields, keep API values and visible labels aligned deliberately. If the UI renders human labels such as `In progress`, browser/e2e must assert that visible label, not the raw API value `in_progress`. If the UI is expected to show raw values, render exactly those raw values. Prefer stable attribute anchors such as `field.<entity>-status` for form controls and visible row text or auxiliary field display anchors for row attributes.

Do not repair a failed status assertion by adding waits when the actual problem is value/label mismatch. First inspect the UI rendering and align the test with the intended user-visible value, or align the UI rendering with the acceptance criterion.
