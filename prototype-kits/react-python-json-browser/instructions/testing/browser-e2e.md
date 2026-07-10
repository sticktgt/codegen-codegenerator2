# Browser/e2e test rules

Use these rules when creating or repairing Playwright tests for this kit.

## Scope

- Keep browser/e2e coverage small and stable. For a single CRUD/list/search screen, prefer one compact spec that proves the main user journey instead of many independent spec files for every requirement.
- One spec file may contain one main flow or a few short independent flows, and the validation plan may link that file to multiple requirements.
- Let backend pytest cover API edge cases, validation errors, and most negative cases. Browser/e2e should focus on user-visible integration: create/edit/list/search through the UI.
- Avoid empty-state tests, exhaustive case-sensitivity tests, and other checks that require a guaranteed clean dataset unless the test controls the dataset via public API/setup or an isolated fixture.
- Do not make one browser test depend on records created by another browser test. Within a single test, create a runtime-unique record before editing or searching for it.

- Browser tests verify behavior through the running frontend. Do not replace them with static assertions.
- Do not inspect backend implementation files from browser/e2e tests. Avoid reading or asserting `backend/app/storage/*.json` from Playwright. Prove behavior through visible UI state and, only when needed, through the public API exposed to the browser.
- Prototype UI anchors use `data-prototype-id`. The template Playwright config sets `testIdAttribute: 'data-prototype-id'`, so `page.getByTestId('screen.note-list')` and `page.getByTestId('action.create-note')` are valid anchor locators in this kit.
- If a run uses a different Playwright config that does not set `testIdAttribute`, locate prototype anchors explicitly with `page.locator('[data-prototype-id="..."]')` instead of assuming `getByTestId` will work.
- Scope locators through stable UI anchors when that makes the assertion unambiguous: screen, widget, or action anchors are preferable to broad page-level text matches.
- Prefer accessible locators such as `getByRole(..., { name, exact: true })` for headings, buttons, inputs, and links when the accessible name is stable.
- Do not use unscoped `getByRole('button', { name: 'Create' })` on a page that also has a "Create Note"/"New note" opener. Either scope to the visible form, or give the submit control a unique accessible name such as "Save note" / "Create note" and use `exact: true`.
- If the UI has both an opener and a submitter, the scheme `action.create-*` anchor should be on the control that actually submits/creates. Use the exact scheme id such as `action.create-note`, not a derived id like `action.create-note-submit`. Use a non-scheme auxiliary id such as `control.open-create-note` for the opener if needed. A stable create flow is: click `control.open-create-note` → scope the visible form → fill fields → click the form submitter or `action.create-note`.
- Avoid broad page-level text locators when the same visible text can appear in headings, cards, paragraphs, or labels.
- Mutating tests must be repeatable across validation reruns and repair loops. Use runtime-unique test-owned data for create/edit/search/delete-like flows.
- Do not edit, delete, or depend on mutable seed records for mutating flows. Create a test-owned record first, then operate on that record.
- Avoid browser assertions that depend on initial seed records such as "Welcome Note" unless the test controls the dataset through a public API setup step or an isolated fixture. For this kit, prefer an initially empty or irrelevant dataset and runtime-created records.
- Keep tests within the planned frontend behavior test files. Browser runner dependencies or package scripts may be added only when the approved file plan explicitly allows those package files to change.
- Match the existing frontend module style. Do not change `frontend/package.json` just to make ad-hoc Node syntax checks or ESM imports work; use the existing Playwright/Vite runner or write tests in the module style already supported by the template.
- Do not run `node --check` directly on `.jsx` React files or Playwright spec files with ESM imports. JSX and Playwright tests are validated by `npm run build` and `npm run test:e2e` through the kit's configured tools.
- During repair, avoid repeated `npm run test:e2e` loops. The pipeline runs official e2e validation after repair; use validation logs and narrow checks rather than repeatedly executing the full browser suite.


Reference examples:

- `instructions/testing/examples/browser-anchored-flow-playwright.md` shows an anchored, runtime-unique browser flow. Adapt ids, labels, and interactions to the generated UI.
