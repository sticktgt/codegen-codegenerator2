# Example: anchored Playwright CRUD/list/search flow

Use this example with catalog methods:
- `web.e2e.playwright.crud-list-search-flow`
- `web.e2e.playwright.form-submit-flow`
- `web.e2e.playwright.item-action-flow`
- `web.e2e.playwright.async-state-transition`
- `web.e2e.playwright.filtered-list-flow`

Replace the neutral `resource` anchors and fields below with exact ids from the approved scheme and file plans.

```js
import { expect, test } from '@playwright/test';

test('user can create, edit, list, and search records', async ({ page }) => {
  const runtimePrimary = `Runtime primary ${Date.now()}`;
  const runtimeSecondary = `Runtime secondary ${Date.now()}`;
  let currentPrimary = runtimePrimary;
  const currentSecondary = runtimeSecondary;

  await page.goto('/');
  await expect(page.getByTestId('screen.resource-list')).toBeVisible();

  await page.getByTestId('control.open-create-resource').click();
  const form = page.getByTestId('form.resource').filter({
    has: page.getByTestId('action.create-resource'),
  });
  await expect(form).toBeVisible();
  await form.getByTestId('field.resource-primary').fill(runtimePrimary);
  await form.getByTestId('field.resource-secondary').fill(runtimeSecondary);
  await form.getByTestId('action.create-resource').click();

  const createdRow = page.getByTestId('item.resource').filter({ hasText: runtimePrimary });
  await expect(createdRow).toBeVisible();
  await expect(createdRow).toContainText(runtimeSecondary);

  await createdRow.getByTestId('action.edit-resource').click();
  const editForm = page.getByTestId('form.resource').filter({
    has: page.getByTestId('action.edit-resource'),
  });
  await expect(editForm).toBeVisible();
  currentPrimary = `${runtimePrimary} updated`;
  await editForm.getByTestId('field.resource-primary').fill(currentPrimary);
  await editForm.getByTestId('action.edit-resource').click();

  const updatedRow = page.getByTestId('item.resource').filter({ hasText: currentPrimary });
  await expect(updatedRow).toBeVisible();

  const search = page.getByTestId('widget.resource-search').getByRole('textbox');
  await search.fill(currentPrimary);
  await expect(updatedRow).toBeVisible();

  await search.fill('');
  await search.fill(currentSecondary);
  const secondaryRow = page.getByTestId('item.resource').filter({ hasText: currentSecondary });
  await expect(secondaryRow).toBeVisible();
  const filteredCount = await page.getByTestId('item.resource').count();
  expect(filteredCount).toBeGreaterThanOrEqual(1);
});
```

## Repeated value assertions

Locate the runtime-owned row first, then assert the intended field through a display anchor. Do not use an unscoped short numeric text value or guessed table-cell index that may match the wrong cell.

```js
const recordRow = page.getByTestId('item.resource').filter({ hasText: currentKey });
await expect(recordRow.getByTestId('field.resource-value-display')).toHaveText(String(currentValue));
```

If no field display anchor exists for a value that browser/e2e must assert, prefer fixing the generated UI to add one instead of guessing a table column index:

```jsx
<span data-prototype-id="field.resource-value-display">{resource.value}</span>
```

Then keep the assertion anchored:

```js
await expect(recordRow.getByTestId('field.resource-value-display')).toHaveText(String(currentValue));
```

Avoid chained row-action selectors:

```js
await page.click(`[data-prototype-id="item.resource"] >> text=${currentPrimary} >> [data-prototype-id="action.edit-resource"]`);
```

Prefer:

```js
const row = page.getByTestId('item.resource').filter({ hasText: currentPrimary });
await row.getByTestId('action.edit-resource').click();
```

Do not use optional form disappearance as a generic success wait. Prefer the requested visible domain outcome, such as the created or edited row.

## Clear/reset search example

Exercise the real Clear/Reset control from a non-empty state and prove that the unfiltered runtime-owned rows return:

```js
await test.step('clear search and verify unfiltered list', async () => {
  const search = page.getByTestId('widget.resource-search');

  await search.getByTestId('field.resource-search-query').fill(currentSearchValue);
  await search.getByRole('button', { name: 'Search' }).click();
  await expect(page.getByTestId('item.resource').filter({ hasText: currentSearchValue })).toBeVisible();

  await search.getByTestId('control.clear-search').click();
  await expect(search.getByTestId('field.resource-search-query')).toHaveValue('');

  await expect(page.getByTestId('item.resource').filter({ hasText: currentPrimary })).toBeVisible();
  await expect(page.getByTestId('item.resource').filter({ hasText: contrastPrimary })).toBeVisible();
});
```

## Native select with asynchronously loaded options

```js
const optionSelect = page.getByTestId('field.resource-choice');
await expect(optionSelect).toBeVisible();
await expect(optionSelect.locator('option', { hasText: optionLabel })).toHaveCount(1);
await optionSelect.selectOption({ label: optionLabel });
```

Do not assert `toBeVisible()` on a native `<option>` node; it may be selectable while reported as hidden.
