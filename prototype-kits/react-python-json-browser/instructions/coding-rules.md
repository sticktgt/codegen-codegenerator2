# Coding Rules

- Keep implementation simple and readable.
- Prefer explicit code over generic abstractions.
- Do not add frameworks not already present in the template unless the active file plan explicitly allows dependency changes.
- Use local JSON/mock data.
- Keep frontend and backend loosely coupled through simple API/action functions.

## Backend import rules

When writing code inside the `backend` application, use imports from the `app` package, not from `backend.app`.

Correct:
- `from app.api.notes import router`
- `from app.services.note_service import NoteService`
- `from app.models.note import Note`

Incorrect:
- `from backend.app.api.notes import router`
- `from backend.app.services.note_service import NoteService`
- `from backend.app.models.note import Note`

Backend validation runs from the `backend` directory with `PYTHONPATH=.`, so `app.*` is the import root.

## Frontend dependency rules

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
