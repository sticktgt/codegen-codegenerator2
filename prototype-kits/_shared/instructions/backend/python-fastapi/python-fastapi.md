# Python / FastAPI Backend Rules

## Backend import rules

When writing code inside the `backend` application, use imports from the `app` package, not from `backend.app`.

Correct:
- `from app.api.<resource> import router`
- `from app.services.<resource>_service import ResourceService`
- `from app.models.<resource> import Resource`

Incorrect:
- `from backend.app.api.<resource> import router`
- `from backend.app.services.<resource>_service import ResourceService`
- `from backend.app.models.<resource> import Resource`

Backend validation runs from the `backend` directory with `PYTHONPATH=.`, so `app.*` is the import root.
