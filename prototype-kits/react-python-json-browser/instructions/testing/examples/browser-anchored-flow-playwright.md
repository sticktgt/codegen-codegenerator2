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
  await editForm.getByTestId('field.note-title').fill(updatedTitle);
  await editForm.getByTestId('action.edit-note').click();

  const updatedRow = page.getByTestId('item.note').filter({ hasText: updatedTitle });
  await expect(updatedRow).toBeVisible();

  const search = page.getByTestId('widget.note-search').getByRole('textbox');
  await search.fill(updatedTitle);
  await expect(updatedRow).toBeVisible();

  await search.fill('');
  await expect(updatedRow).toBeVisible();

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
