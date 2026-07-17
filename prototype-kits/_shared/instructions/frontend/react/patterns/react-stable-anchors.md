# Pattern: React stable anchors

Use this pattern to make generated React UI testable through stable prototype anchors.

## Anchors and controls

- Put the `screen.*` anchor on the screen root only once.
- Put the `widget.*` anchor on the widget root only once.
- Put scheme `action.*` anchors on the actual controls that perform the action.
- For create/edit forms, distinguish opener, form scope, and submitter:
  - opener: auxiliary anchor such as `control.open-create-<entity>`;
  - form scope: auxiliary anchor such as `form.<entity>` when fields and submit controls need stable scoping;
  - submitter: scheme action anchor such as `action.create-<entity>` or `action.edit-<entity>`.
  If the UI has both an opener and a submitter, these anchors must be different and the browser test must use the same contract.
- Do not invent suffixed scheme ids such as `action.create-<entity>-submit`.
- If one submit button switches modes, use static literal alternatives: `data-prototype-id={editing ? 'action.edit-<entity>' : 'action.create-<entity>'}`.
- For repeated rows/cards, add an auxiliary item anchor such as `data-prototype-id="item.<entity>"`; repeated item anchors are allowed and are used for scoped browser actions. For every displayed value that generated browser/e2e must assert, add an auxiliary display anchor such as `data-prototype-id="field.<entity>-<field>-display"` inside that row/card.

## Browser-flow testability

Design the UI so the catalog methods in `instructions/testing/test-method-catalog.md` can be used directly:

- A create flow has a stable opener and a scoped submit action.
- A repeated record can be located by an item/card anchor and runtime-owned text.
- The edit action is inside the item/card for the record it edits.
- Search/filter input lives inside the search widget anchor.
- After create/edit/search/filter, the UI exposes a visible row/card state that tests can wait for before count or absence assertions. For filters, the visible state should be a runtime-owned row/card that is expected to match the active filter.
- After an edit changes any visible value used to locate or search a row, subsequent UI assertions should locate/search by the current edited value or by a stable id, not by the pre-edit value. This applies to every changed field that participates in later row lookup, search, filtering, or visible assertions.

Avoid page designs where browser tests must rely on global text matches, ambiguous `Create`/`Edit` buttons, or hidden implicit state transitions.

## Form and field testability anchors

For generated React forms in this kit, expose stable auxiliary anchors in addition to scheme anchors:

- Form scope: `data-prototype-id="form.<entity>"` on the visible form or form-like container.
- Field controls: `data-prototype-id="field.<entity>-<field>"` on each input/select/textarea used by browser/e2e.

- Async option selects: when a form contains a `<select>` whose options are loaded or changed asynchronously, keep the option list in the component state that renders the select and refresh that list after the action that changes the options succeeds. Do not refresh only the main list while leaving select options stale.
  If a sibling or child component can create/update records that feed the select options, connect its success callback to the option-list refresh (or append the returned option to local state). Refreshing only an unrelated list is not enough; the select must receive the new option before the user/test can choose it.
- Select option semantics: the option `value` may be an internal id while the visible label is a user-facing value. The UI should render stable option labels for users, and browser tests should select by label or known value without assuming the label equals the stored id.
- Opener control: `data-prototype-id="control.open-create-<entity>"` on a button that only opens the form.
- Submit/save control: exact scheme action anchor such as `action.create-<entity>` or `action.edit-<entity>`.
- Repeated rows/cards: `data-prototype-id="item.<entity>"`.
- Repeated row/card display values used by browser/e2e: `data-prototype-id="field.<entity>-<field>-display"`.

These `form.*`, `field.*`, `control.*`, and `item.*` anchors are auxiliary testability anchors, not scheme elements. They help Playwright use stable scoped locators and avoid fragile label/text/CSS chains. Use accessible labels too where reasonable, but do not make generated e2e depend on label text being an ancestor of the input.

Browser/e2e should fill fields like this:

```javascript
await page.getByTestId('control.open-create-<entity>').click();
const form = page.getByTestId('form.<entity>');
await form.getByTestId('field.<entity>-primary').fill(runtimePrimary);
await form.getByTestId('field.<entity>-<select-field>').selectOption(runtimeOptionValue);
await form.getByTestId('action.create-<entity>').click();
```

Avoid this brittle pattern:

```javascript
await page.getByTestId('action.create-<entity>').click();
const form = page.getByTestId('screen.<entity>-list');
await form.getByText('Primary field:').locator('input[type="text"]').fill(runtimePrimary);
```
