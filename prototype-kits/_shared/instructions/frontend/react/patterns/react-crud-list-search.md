# Pattern: React CRUD/list/search screen

Use this pattern for small React screens backed by a public API. Backend storage technology is intentionally out of scope for this frontend pattern.

## Component shape

- Keep route wiring in `frontend/src/routes/routeRegistry.js` or another planned integration file.
- Match the current kit route registry contract exactly. In this kit `frontend/src/App.jsx` reads `routes[0].component`; generated route entries must use `component: ScreenComponent`, not `element`, and should not invent navigation links unless the template actually renders navigation. Prefer the existing app entry route (`/`) unless the baseline template already supports real client routing for the planned path.
- Keep the main user journey in the planned screen file. For simple CRUD/list/search screens, create/edit handlers may be screen-internal instead of separate action files.
- Use a widget file for reusable visual/input pieces only when planned, such as `ResourceSearch.jsx`.
- Match the backend public API path exactly. If FastAPI exposes `/api/<resources>`, the frontend must call `/api/<resources>`.

## Search dimension coverage

Do not reduce an explicit multi-field search requirement to the first convenient field. If requirements name several searchable fields, implement one of these demo-safe UI shapes:

- a single free-text search input whose backend/service search checks all named fields; or
- explicit user-visible controls for each named field.

The browser/e2e flow must prove the same user-visible search dimensions. For a small list of named fields, exercise each one at least once with runtime-owned records. Backend API support for extra query parameters is not enough if the UI only exposes search by one field.

When a generic search box covers multiple fields, the screen implementation must apply the same search query to all named user-visible fields or call an API that does so. Do not implement the UI filter for only a subset while the requirement and test name additional search dimensions. The e2e should wait for a row containing the same field value it searched for before using any count assertion.

Search/filter reset controls must perform a real user-visible reset. When the UI has a Clear/Reset control, its handler should clear every user-visible search/filter state and reload the unfiltered list using explicit reset arguments. Do not rely on React state having updated synchronously before calling a loader that reads state. Prefer a loader shaped like `fetchResources({ query = '', filter = '' })`, then implement reset as `setSearchQuery(''); setFilterValue(''); fetchResources({ query: '', filter: '' });`. Avoid `setSearchQuery(''); setFilterValue(''); fetchResources();` when `fetchResources()` reads `searchQuery` or `filterValue` from React state; that can leave the list filtered even though the controls look cleared. The user should be able to click Clear while search/filter controls are non-empty and immediately see the unfiltered runtime-owned rows/cards.


Recommended shape for multi-control search/filter screens:

```javascript
const fetchResources = async ({ query = searchQuery, filter = filterValue } = {}) => {
  const params = new URLSearchParams();
  if (query) params.append('q', query);
  if (filter) params.append('filter', filter);
  const response = await fetch(`/api/<resources>?${params}`);
  if (response.ok) setResources(await response.json());
};

const handleClearSearch = () => {
  setSearchQuery('');
  setFilterValue('');
  fetchResources({ query: '', filter: '' });
};
```

## Browser flow scope

For a single create/edit/list/search screen, keep the generated browser test to the requested user journey. Do not add delete/confirmation, empty-state, minimal-field, or multi-record edge-case browser tests unless the current requirements explicitly ask for them. When search/filter is involved, create only the runtime-owned records needed for the flow, wait for the expected filtered row/card after changing filters, and clear filter state before any full-list count assertion.

## Submit and visible outcome contract

Generated CRUD/list/search screens should expose a visible domain outcome after create/edit so browser/e2e can wait on behavior instead of implementation details. Good outcomes include the created row/card, an edited visible field, a changed related value, or the expected filtered result.

Do not require the screen to close or hide a form after submit unless the requirement says so. If the form remains open, reset, or switches between create/edit modes, tests should still assert the domain outcome through `item.<entity>` rows/cards rather than assuming `form.<entity>` disappears.

## Enumerated-value display assertions

For enumerated fields, keep API values and visible labels aligned deliberately. If the UI renders a user-facing label, browser/e2e must assert that label rather than assuming the raw API value is shown. If the UI is expected to show raw values, render exactly those raw values. Prefer stable anchors such as `field.<entity>-<field>` for controls and visible row text or auxiliary field-display anchors for row attributes.

Do not repair a failed enumerated-value assertion by adding waits when the actual problem is value/label mismatch. First inspect the UI rendering and align the test with the intended user-visible value, or align the UI rendering with the acceptance criterion.
