# Architecture Add-on: React + FastAPI + JSON browser stack profile

This profile combines the active layer add-ons for the `react-python-json-browser` kit:

- React/browser frontend;
- Python/FastAPI backend;
- local JSON/mock storage;
- browser/e2e validation.

## Cross-layer rule

Keep frontend and backend loosely coupled through simple API/action functions. The frontend should call the public API shape owned by the backend layer; it should not read backend storage files directly.

Use this profile as an overview only. Layer-specific rules live in:

- `instructions/core/architecture-addons/frontend/react-browser.md`;
- `instructions/core/architecture-addons/backend/python-fastapi.md`;
- `instructions/core/architecture-addons/storage/json.md`.
