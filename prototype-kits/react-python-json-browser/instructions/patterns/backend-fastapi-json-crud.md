# Pattern: FastAPI + JSON storage CRUD

Use this pattern for small JSON-backed backend features with API, service, model, and mock storage artifacts.

## Recommended shape

- Keep the API layer thin: request/response validation and route wiring belong in `backend/app/api/...`; business logic and storage access belong in `backend/app/services/...`.
- Give the service an explicit storage injection point, usually `__init__(storage_path: Path | str | None = None)`. The default path must point to the exact mock JSON file listed in `file_plan.json`, and tests must be able to pass a temp path.
- Use only the planned mock/storage JSON filename. If the plan lists `backend/app/storage/notes_json_mock.json`, do not also create `notes_mock.json` or any other alias/seed file.
- Keep JSON helpers in the planned storage module/package. They should create parent directories when saving and return a known empty shape when the file is missing or empty.
- Pick one JSON shape and keep it consistent, for example `{ "notes": [] }` for a notes collection or `[]` for a generic item list. Tests, service, and seed data must use the same shape.
- Pick one in-memory representation per service method and keep it consistent. If `get_all_notes()` returns Pydantic `Note` objects, update/delete/search code must use object attributes such as `note.id`, and save with `note.model_dump(mode="json")`; do not later treat those objects as dictionaries like `note["id"]`. If the service works with dictionaries internally, convert to Pydantic models only at API boundaries.
- Serialize Pydantic models with JSON-compatible values before writing to disk. For Pydantic v2, use `model_dump(mode="json")` when the model contains datetime, UUID, or other non-primitive values.
- Avoid module-level mutable state that makes tests share records between cases. A module-level route service is acceptable only if tests can replace the route module's service object with an isolated instance.

## FastAPI validation behavior

- FastAPI/Pydantic request-model validation errors normally return HTTP 422.
- Use HTTP 400 only for manual domain validation that happens after the request body has already passed schema validation.
- Backend tests must match this behavior. For example, a request missing a required Pydantic field should usually expect 422, not 400.
- If the requirement explicitly asks for 400 on invalid input, implement explicit validation and tests consistently; otherwise prefer FastAPI defaults.

## Route and prefix consistency

- Choose one public API shape and use it consistently across backend tests and frontend calls.
- If `main.py` includes `notes_router` with `prefix="/api"`, and the router itself uses `prefix="/notes"`, clients should call `/api/notes`.
- Avoid defining both `/notes` and `/api/notes` unless the requirement explicitly needs compatibility aliases.
- Search can be either `GET /api/notes?q=...` or `GET /api/notes/search?q=...`, but tests and UI must use the same endpoint.

## Testability checklist

Before writing tests, confirm:

- The service can be constructed with a temp storage path, or the route module service object can be replaced.
- The test client is created after dependency replacement if the app or route captures dependencies.
- Each test starts from a known dataset and does not depend on records created by earlier tests.
- Tests do not rewrite implementation `.py` files to change storage paths.
- Test expectations match FastAPI/Pydantic behavior, including 422 for request schema validation failures.
