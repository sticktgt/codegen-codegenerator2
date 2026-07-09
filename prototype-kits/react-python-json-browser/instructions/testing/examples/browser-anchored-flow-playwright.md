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

  await screen.getByRole('button', { name: /create/i }).click();
  await screen.getByLabel(/title/i).fill(title);
  await screen.getByRole('button', { name: /save/i }).click();

  const itemRow = screen.getByText(title).locator('..');
  await expect(itemRow).toBeVisible();

  await itemRow.getByRole('button', { name: /edit/i }).click();
  await screen.getByLabel(/title/i).fill(editedTitle);
  await screen.getByRole('button', { name: /save/i }).click();

  await expect(screen.getByText(editedTitle, { exact: true })).toBeVisible();
});
```

Key ideas:

- `getByTestId` uses `data-prototype-id` in this kit because Playwright config sets `testIdAttribute`.
- Locators are scoped through the owning screen or row.
- Test data is runtime-unique, so validation can rerun after repair without colliding with earlier data.
- The flow does not depend on records created by another e2e test.
- The browser test verifies behavior through the UI. It does not read backend storage files or assert private mock JSON contents.
