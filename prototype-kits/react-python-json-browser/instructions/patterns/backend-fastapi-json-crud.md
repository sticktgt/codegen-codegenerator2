# Pattern: FastAPI + JSON storage CRUD

Use this pattern for small JSON-backed backend features with API, service, model, and mock storage artifacts.

## Recommended shape

- Keep the API layer thin: request/response validation and route wiring belong in `backend/app/api/...`; business logic and storage access belong in `backend/app/services/...`.
- Give the service an explicit storage injection point, usually `__init__(storage_path: Path | str | None = None)`. The default path must point to the exact mock JSON file listed in `file_plan.json`, and tests must be able to pass a temp path.
- Expose a small API dependency/provider such as `get_<entity>_service()` and use `Depends(...)` in route handlers. This lets pytest replace the service through `app.dependency_overrides` without changing implementation files.
- Use only the planned mock/storage JSON filename. If the plan lists `backend/app/storage/notes_json_mock.json`, do not also create `notes_mock.json` or any other alias/seed file.
- Pick one JSON shape and keep it consistent, for example `{ "notes": [] }` for a collection or `[]` for a generic item list.
- Pick one in-memory representation per service method and keep it consistent. If methods return Pydantic objects, use attributes and save with `model_dump(mode="json")`; if methods use dictionaries internally, convert to Pydantic models only at API boundaries.
- Serialize Pydantic models with JSON-compatible values before writing to disk. For Pydantic v2, use `model_dump(mode="json")` when the model contains datetime, UUID, or other non-primitive values.
- Avoid module-level mutable state that makes tests share records between cases. A module-level route service is acceptable only if tests can replace the exact route-module service object before requests are made; otherwise prefer `Depends(...)`.

## FastAPI validation behavior

- FastAPI/Pydantic request-model validation errors normally return HTTP 422.
- Use HTTP 400 only for manual domain validation after schema parsing.
- Backend tests must match this behavior unless the requirement explicitly says otherwise.

## Route and prefix consistency

- Choose one public API shape and use it consistently across backend tests and frontend calls.
- If `main.py` includes `notes_router` with `prefix="/api"`, and the router itself uses `prefix="/notes"`, clients should call `/api/notes`.
- Avoid defining both `/notes` and `/api/notes` unless the requirement explicitly needs compatibility aliases.
- Search can be either `GET /api/notes?q=...` or `GET /api/notes/search?q=...`, but tests and UI must use the same endpoint.

## Mutable-state dependency testability

Use the catalog method `backend.pytest.api.mutable-state` for feature API tests. The FastAPI `get_<entity>_service()` + `app.dependency_overrides[...]` shape is the preferred example for this kit, not a global rule for every future backend stack.
