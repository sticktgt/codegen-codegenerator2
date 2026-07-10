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

  await page.goto('/');
  await expect(page.getByTestId('screen.note-list')).toBeVisible();

  // Open the form through an auxiliary control. This is not the create action.
  await page.getByTestId('control.open-create-note').click();
  const form = page.locator('form').filter({ has: page.getByTestId('action.create-note') });
  await expect(form).toBeVisible();
  await form.getByLabel('Title').fill(runtimeTitle);
  await form.getByLabel('Content').fill(runtimeBody);
  await form.getByTestId('action.create-note').click();

  const createdRow = page.getByTestId('item.note').filter({ hasText: runtimeTitle });
  await expect(createdRow).toBeVisible();
  await expect(createdRow).toContainText(runtimeBody);

  // For repeated rows/cards, scope the action inside the row.
  await createdRow.getByTestId('action.edit-note').click();
  const editForm = page.locator('form').filter({ has: page.getByTestId('action.edit-note') });
  await expect(editForm).toBeVisible();
  await editForm.getByLabel('Title').fill(updatedTitle);
  await editForm.getByTestId('action.edit-note').click();

  const updatedRow = page.getByTestId('item.note').filter({ hasText: updatedTitle });
  await expect(updatedRow).toBeVisible();

  const search = page.getByTestId('widget.note-search').getByRole('textbox');
  await search.fill(updatedTitle);
  await expect(updatedRow).toBeVisible();

  await search.fill('');
  await expect(updatedRow).toBeVisible();
  const rowCount = await page.getByTestId('item.note').count();
  expect(rowCount).toBeGreaterThan(0);
});
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
