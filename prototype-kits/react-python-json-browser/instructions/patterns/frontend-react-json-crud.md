# Pattern: React JSON CRUD/list/search screen

Use this pattern for small React screens backed by the kit FastAPI JSON CRUD service.

## Component shape

- Keep route wiring in `frontend/src/routes/routeRegistry.js` or another planned integration file.
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
- After an edit changes the title/name used to locate a row, subsequent UI assertions should locate the row by the edited value or by a stable id, not by the pre-edit value.

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

## Browser flow scope

For a single create/edit/list/search screen, keep the generated browser test to the requested user journey. Do not add delete/confirmation, empty-state, minimal-field, or multi-record edge-case browser tests unless the current requirements explicitly ask for them. When search/filter is involved, create only the runtime-owned records needed for the flow, wait for the expected filtered row/card after changing filters, and clear filter state before any full-list count assertion.


## Submit and visible outcome contract

Generated CRUD/list/search screens should expose a visible domain outcome after create/edit so browser/e2e can wait on behavior instead of implementation details. Good outcomes include the created row/card, edited title/name, edited status/category, or filtered result.

Do not require the screen to close or hide a form after submit unless the requirement says so. If the form remains open, reset, or switches between create/edit modes, tests should still assert the domain outcome through `item.<entity>` rows/cards rather than assuming `form.<entity>` disappears.

## Enum/status display assertions

For enum/status/category fields, keep API values and visible labels aligned deliberately. If the UI renders human labels such as `In progress`, browser/e2e must assert that visible label, not the raw API value `in_progress`. If the UI is expected to show raw values, render exactly those raw values. Prefer stable attribute anchors such as `field.<entity>-status` for form controls and visible row text or auxiliary field display anchors for row attributes.

Do not repair a failed status assertion by adding waits when the actual problem is value/label mismatch. First inspect the UI rendering and align the test with the intended user-visible value, or align the UI rendering with the acceptance criterion.
