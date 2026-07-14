# Example: anchored Playwright CRUD/list/search flow

Use this example with catalog methods:
- `web.e2e.playwright.crud-list-search-flow`
- `web.e2e.playwright.form-submit-flow`
- `web.e2e.playwright.item-action-flow`
- `web.e2e.playwright.async-state-transition`
- `web.e2e.playwright.filtered-list-flow`

```js
import { expect, test } from '@playwright/test';

test('user can create, edit, list, and search records', async ({ page }) => {
  const runtimeTitle = `Runtime title ${Date.now()}`;
  const runtimeBody = `Runtime body ${Date.now()}`;
  const updatedTitle = `${runtimeTitle} updated`;
  let currentTitle = runtimeTitle;
  const currentBody = runtimeBody;

  // Use the real app entry. In this kit the template renders routes[0].component at the app root.
  await page.goto('/');
  await expect(page.getByTestId('screen.note-list')).toBeVisible();

  // Open the form through an auxiliary control. This is not the create action.
  await page.getByTestId('control.open-create-note').click();
  const form = page.getByTestId('form.note').filter({ has: page.getByTestId('action.create-note') });
  await expect(form).toBeVisible();
  await form.getByTestId('field.note-title').fill(runtimeTitle);
  await form.getByTestId('field.note-content').fill(runtimeBody);
  await form.getByTestId('action.create-note').click();
  // Do not assert that the form closes unless the requirement says it must.
  // The success signal is the created row/card becoming visible.

  const createdRow = page.getByTestId('item.note').filter({ hasText: runtimeTitle });
  await expect(createdRow).toBeVisible();
  await expect(createdRow).toContainText(runtimeBody);

  // For repeated rows/cards, scope the action inside the row.
  await createdRow.getByTestId('action.edit-note').click();
  const editForm = page.getByTestId('form.note').filter({ has: page.getByTestId('action.edit-note') });
  await expect(editForm).toBeVisible();
  currentTitle = updatedTitle;
  await editForm.getByTestId('field.note-title').fill(currentTitle);
  await editForm.getByTestId('action.edit-note').click();

  const updatedRow = page.getByTestId('item.note').filter({ hasText: currentTitle });
  await expect(updatedRow).toBeVisible();

  const search = page.getByTestId('widget.note-search').getByRole('textbox');
  await search.fill(currentTitle);
  await expect(updatedRow).toBeVisible();

  // If the requirement names several searchable fields, cover the user-visible dimensions.
  // For a single generic search box, use current values from different fields (for example title and body).
  await search.fill('');
  await search.fill(currentBody);
  const bodySearchRow = page.getByTestId('item.note').filter({ hasText: currentBody });
  await expect(bodySearchRow).toBeVisible();
  const bodySearchCount = await page.getByTestId('item.note').count();
  expect(bodySearchCount).toBeGreaterThanOrEqual(1);

  await search.fill('');
  await expect(updatedRow).toBeVisible();
  // If this flow created a contrast row for search, wait for that runtime-owned row too
  // before asserting a full-list count.
  // await expect(contrastRow).toBeVisible();

  // Values reused across test.step(...) sections should be declared in the parent test scope
  // and updated when an edit changes a field used later for search/lookup.

  // If a status/category filter exists, wait for a matching runtime-owned row before count assertions.
  const filter = page.getByTestId('widget.note-search');
  const statusFilter = filter.getByTestId('field.note-status-filter');
  if (await statusFilter.count()) {
    await statusFilter.selectOption('in_progress');
    await expect(updatedRow).toBeVisible();
  }

  const rowCount = await page.getByTestId('item.note').count();
  expect(rowCount).toBeGreaterThan(0);
});
```


## Table row value assertions

When the UI renders a table, locate the runtime-owned row first, then assert the intended field or table cell. Do not use `row.getByText()` for short numeric values such as stock quantity, price fragments, or repeated status/category labels. Those values can appear in multiple cells and cause strict-mode failures.

Prefer a stable field/display anchor when the UI provides one:

```js
const productRow = page.getByTestId('item.product').filter({ hasText: currentSku });
await expect(productRow.getByTestId('field.product-stock-quantity-display')).toHaveText(String(currentStock));
```

If the generated table does not provide per-field display anchors, use the known column inside the scoped row:

```js
const productRow = page.getByTestId('item.product').filter({ hasText: currentSku });
await expect(productRow.locator('td').nth(4)).toContainText(String(currentStock));
```

Avoid ambiguous text checks for repeated values:

```js
await expect(productRow.getByText('10')).toBeVisible(); // Wrong: may match several cells.
```

Avoid this fragile row-action selector:

```js
await page.click(`[data-prototype-id="item.note"] >> text=${runtimeTitle} >> [data-prototype-id="action.edit-note"]`);
```

Instead locate the row first and click the action inside it:

```js
const row = page.getByTestId('item.note').filter({ hasText: runtimeTitle });
await row.getByTestId('action.edit-note').click();
```


Avoid using optional form disappearance as a generic success wait:

```js
await form.getByTestId('action.create-note').click();
await expect(form).not.toBeVisible(); // Wrong unless closing the form is required behavior.
```

Prefer the requested domain outcome:

```js
await form.getByTestId('action.create-note').click();
const createdRow = page.getByTestId('item.note').filter({ hasText: runtimeTitle });
await expect(createdRow).toBeVisible();
```


## Clear/reset search example

For a generated Clear/Reset control, test the actual user action from a non-empty state. Do not pre-empty the input before clicking Clear. When a category/status/type filter is present, create or use two runtime-owned rows in different filter values and prove both return after reset:

```javascript
await test.step('Clear search and verify unfiltered list', async () => {
  const search = page.getByTestId('widget.customer-search');

  // Enter a real non-empty search state first.
  await search.getByTestId('field.customer-search-query').fill(currentEmail);
  await search.getByRole('button', { name: 'Search' }).click();
  await expect(page.getByTestId('item.customer').filter({ hasText: currentEmail })).toBeVisible();

  // Click the product Clear control. Do not pre-empty the input.
  await search.getByTestId('control.clear-search').click();
  await expect(search.getByTestId('field.customer-search-query')).toHaveValue('');

  // Prove reset with two runtime-owned rows, including one that was not visible under the search.
  await expect(page.getByTestId('item.customer').filter({ hasText: currentName })).toBeVisible();
  await expect(page.getByTestId('item.customer').filter({ hasText: secondName })).toBeVisible();
});
```
