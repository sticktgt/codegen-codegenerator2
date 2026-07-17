# React Frontend Rules

Use only dependencies declared in `frontend/package.json`.

Do not import or use `react-router-dom`, `axios`, UI frameworks, state-management libraries, routing libraries, CSS frameworks, or any other external package unless it is already declared in `frontend/package.json`.

Do not edit `frontend/package.json` or add npm dependencies unless the active file plan explicitly allows that file and dependency change.

For this prototype kit, routing is implemented only through:
- `frontend/src/routes/routeRegistry.js`
- `frontend/src/App.jsx`

Do not use:
- `BrowserRouter`
- `Routes`
- `Route`
- `Link`
- `NavLink`
- `useNavigate`
- `useParams`
- any router hooks

For HTTP calls, use the browser `fetch` API inside the listed files. Do not create API client helper files unless they are explicitly listed in the active file plan.
