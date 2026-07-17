# Browser Playwright validation review additions

Additional reads and rules:
- instructions/testing/browser-playwright-methods.md
- instructions/testing/browser-e2e.md
- Does each browser/e2e check prove a user-visible requirement rather than duplicating backend API edge cases?
- Does the planned UI implementation expose stable anchors for the browser flow it expects to test?
- If a table/list field is newly displayed or changed, prefer a display anchor plan over guessed column indexes. Treat missing preferred anchors as a warning unless the plan would make the e2e impossible or flaky by design.
