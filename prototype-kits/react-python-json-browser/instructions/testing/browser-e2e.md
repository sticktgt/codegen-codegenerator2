# Browser/e2e test rules

Use these rules when creating or repairing Playwright tests for this kit.

- Browser tests verify behavior through the running frontend. Do not replace them with static assertions.
- Do not inspect backend implementation files from browser/e2e tests. Avoid reading or asserting `backend/app/storage/*.json` from Playwright. Prove behavior through visible UI state and, only when needed, through the public API exposed to the browser.
- Prototype UI anchors use `data-prototype-id`. The template Playwright config sets `testIdAttribute: 'data-prototype-id'`, so `page.getByTestId('screen.note-list')` and `page.getByTestId('action.create-note')` are valid anchor locators in this kit.
- If a run uses a different Playwright config that does not set `testIdAttribute`, locate prototype anchors explicitly with `page.locator('[data-prototype-id="..."]')` instead of assuming `getByTestId` will work.
- Scope locators through stable UI anchors when that makes the assertion unambiguous: screen, widget, or action anchors are preferable to broad page-level text matches.
- Prefer accessible locators such as `getByRole(..., { name, exact: true })` for headings, buttons, inputs, and links when the accessible name is stable.
- Avoid broad page-level text locators when the same visible text can appear in headings, cards, paragraphs, or labels.
- Mutating tests must be repeatable across validation reruns and repair loops. Use runtime-unique test-owned data for create/edit/search/delete-like flows.
- Do not make one browser test depend on data created or changed by another browser test.
- Do not edit, delete, or depend on mutable seed records for mutating flows. Create a test-owned record first, then operate on that record.
- Keep tests within the planned frontend behavior test files. Browser runner dependencies or package scripts may be added only when the approved file plan explicitly allows those package files to change.
- Match the existing frontend module style. Do not change `frontend/package.json` just to make ad-hoc Node syntax checks or ESM imports work; use the existing Playwright/Vite runner or write tests in the module style already supported by the template.
- Do not run `node --check` directly on `.jsx` React files or Playwright spec files with ESM imports. JSX and Playwright tests are validated by `npm run build` and `npm run test:e2e` through the kit's configured tools.


Reference examples:

- `instructions/testing/examples/browser-anchored-flow-playwright.md` shows an anchored, runtime-unique browser flow. Adapt ids, labels, and interactions to the generated UI.
