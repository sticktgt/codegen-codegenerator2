# Example: browser/e2e flow with prototype anchors

This is a reference pattern, not a mandatory implementation. Adapt ids, roles, and labels to the generated UI.

```javascript
import { test, expect } from '@playwright/test';

test('user can create and edit an item', async ({ page }) => {
  const suffix = Date.now();
  const title = `E2E item ${suffix}`;
  const editedTitle = `E2E item edited ${suffix}`;

  await page.goto('/');

  const screen = page.getByTestId('screen.item-list');
  await expect(screen).toBeVisible();

  await screen.getByTestId('control.open-create-item').click();
  const form = screen.getByTestId('form.item');
  await form.getByLabel(/title/i).fill(title);
  await form.getByRole('button', { name: /save item/i, exact: true }).click();

  const itemRow = screen.getByTestId('item.row').filter({ hasText: title });
  await expect(itemRow).toBeVisible();

  await itemRow.getByRole('button', { name: /edit/i, exact: true }).click();
  await form.getByLabel(/title/i).fill(editedTitle);
  await form.getByRole('button', { name: /save item/i, exact: true }).click();

  await expect(screen.getByTestId('item.row').filter({ hasText: editedTitle })).toBeVisible();
});
```

Key ideas:

- `getByTestId` uses `data-prototype-id` in this kit because Playwright config sets `testIdAttribute`.
- Locators are scoped through the owning screen, form, or row.
- The create opener and create submitter have different anchors/names, so the test never has to guess between "Create" and "Create Note".
- Test data is runtime-unique, so validation can rerun after repair without colliding with earlier data.
- The flow does not depend on records created by another e2e test.
- The browser test verifies behavior through the UI. It does not read backend storage files or assert private mock JSON contents.
