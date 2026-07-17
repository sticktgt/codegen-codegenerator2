# Browser Playwright planning additions

Additional reads and rules:
- instructions/testing/browser-playwright-methods.md
- instructions/testing/browser-e2e.md
- Use browser/e2e only for user-visible journeys and behavior that cannot be proven by backend pytest or static anchors alone.
- For a single CRUD/list/search screen, prefer one compact `web.e2e.playwright.crud-list-search-flow` with `test.step(...)` sections rather than many independent tests sharing mutable state.
- Plan `ui_static` separately for anchor presence; browser/e2e proves behavior.
