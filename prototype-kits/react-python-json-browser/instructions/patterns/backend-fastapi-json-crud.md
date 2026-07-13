# Pattern: FastAPI + JSON storage CRUD

Use this pattern for small JSON-backed backend features with API, service, model, and mock storage artifacts.

## Recommended shape

- Keep the API layer thin: request/response validation and route wiring belong in `backend/app/api/...`; business logic and storage access belong in `backend/app/services/...`.
- Give the service an explicit resource injection point. For this JSON-storage pattern it is usually `__init__(storage_path: Path | str | None = None)`. The default path must point to the exact mock JSON file listed in `file_plan.json`, and tests must be able to pass a temp path. Preserve the injected resource identity for all reads/writes; never collapse it to a basename, default resource, global singleton, or another canonical storage filename, or tests will silently share tracked storage.
- Expose a small API dependency/provider such as `get_<entity>_service()` and use `Depends(...)` in route handlers. For new generated FastAPI JSON-backed routes in this kit, this provider pattern is required because `backend.pytest.api.mutable-state` tests depend on `app.dependency_overrides` for isolated storage.
- Use only the planned mock/storage JSON filename. If the plan lists `backend/app/storage/notes_json_mock.json`, do not also create `notes_mock.json` or any other alias/seed file. The default service path may be this planned file, but injected test resources must keep their identity and must not be replaced by the planned default.
- Pick one JSON shape and keep it consistent, for example `{ "notes": [] }` for a collection or `[]` for a generic item list.
- Pick one in-memory representation per service method and keep it consistent. If methods return Pydantic objects, use attributes and save with `model_dump(mode="json")`; if methods use dictionaries internally, convert to Pydantic models only at API boundaries.
- Serialize Pydantic models with JSON-compatible values before writing to disk. For Pydantic v2, use `model_dump(mode="json")` when the model contains datetime, UUID, or other non-primitive values.
- Avoid module-level mutable state that makes tests share records between cases. A module-level route service is acceptable only if tests can replace the exact route-module service object before requests are made; otherwise prefer `Depends(...)`.


## Injected resource contract

For JSON-backed services, storage helpers and services must accept either the planned storage filename/path or an explicit temp path from tests. Treat `Path`/absolute/full paths as the exact storage target. Do not convert injected storage paths to only the file name before reading/writing. This is the JSON-storage example of the broader kit rule: any injected test resource handle, locator, repository, adapter, client, or config must be used as supplied and must not be replaced by a default resource or global singleton.

Preferred service shape:

```python
class ItemService:
    def __init__(self, storage_path: Path | str | None = None):
        self._storage_path = Path(storage_path) if storage_path is not None else DEFAULT_STORAGE_PATH

    def _read_items(self) -> list[Item]:
        data = read_json_storage(self._storage_path)
        ...
```

Avoid:

```python
self._storage_filename = Path(storage_path).name  # Wrong: loses temp directory isolation.
```

## Request payload contract

For generated browser-backed CRUD APIs in this kit, keep one HTTP request shape across API implementation, frontend calls, and backend pytest:

- `POST /api/<resources>` create: JSON request body using a Pydantic create/request model.
- `PUT` or `PATCH /api/<resources>/{id}` update: JSON request body using a Pydantic update/request model with optional fields when partial update is supported.
- `GET /api/<resources>` list/search/filter: query parameters are appropriate for search text, status/category filters, pagination, and sort options.

Do not implement create/update as individual FastAPI query parameters when the generated React form submits JSON. Do not test create/update with `params=` while the frontend sends a JSON body, or vice versa. The backend API tests are the contract for the frontend request shape.

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

Use the catalog method `backend.pytest.api.mutable-state` for feature API tests. In this FastAPI kit, that method means `get_<entity>_service()` + `Depends(...)` in the API module and `app.dependency_overrides[...]` in pytest fixtures. For future non-FastAPI stacks, add a separate method or example rather than weakening this contract.
