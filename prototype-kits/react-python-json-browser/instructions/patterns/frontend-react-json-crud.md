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
- For create/edit forms, distinguish opener and submitter:
  - opener: auxiliary anchor such as `control.open-create-note`;
  - submitter: scheme action anchor such as `action.create-note` or `action.edit-note`.
- Do not invent suffixed scheme ids such as `action.create-note-submit`.
- If one submit button switches modes, use static literal alternatives: `data-prototype-id={editing ? 'action.edit-note' : 'action.create-note'}`.
- For repeated rows/cards, add an auxiliary item anchor such as `data-prototype-id="item.note"`; repeated item anchors are allowed and are used for scoped browser actions.

## Browser-flow testability

Design the UI so the catalog methods in `instructions/testing/test-method-catalog.md` can be used directly:

- A create flow has a stable opener and a scoped submit action.
- A repeated record can be located by an item/card anchor and runtime-owned text.
- The edit action is inside the item/card for the record it edits.
- Search/filter input lives inside the search widget anchor.
- After create/edit/search, the UI exposes a visible row/card state that tests can wait for before count or absence assertions.

Avoid page designs where browser tests must rely on global text matches, ambiguous `Create`/`Edit` buttons, or hidden implicit state transitions.
