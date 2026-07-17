# Pattern: FastAPI + JSON storage CRUD

Use this pattern for small JSON-backed backend features with API, service, model, and mock storage artifacts.

## Recommended shape

- Keep the API layer thin: request/response validation and route wiring belong in `backend/app/api/...`; business logic and storage access belong in `backend/app/services/...`.
- Give the service an explicit resource injection point. For this JSON-storage pattern it is usually `__init__(storage_path: Path | str | None = None)`. The default path must point to the exact mock JSON file listed in `file_plan.json`, and tests must be able to pass a temp path. Preserve the injected resource identity for all reads/writes; never collapse it to a basename, default resource, global singleton, or another canonical storage filename, or tests will silently share tracked storage.
- Expose a small API dependency/provider such as `get_<entity>_service()` and use `Depends(...)` in route handlers. For new generated FastAPI JSON-backed routes in this kit, this provider pattern is required because `backend.pytest.api.mutable-state` tests depend on `app.dependency_overrides` for isolated storage.
- Use only the planned mock/storage JSON filename. If the plan lists `backend/app/storage/<resource>_json_mock.json`, do not also create `<resource>_mock.json` or any other alias/seed file. The default service path may be this planned file, but injected test resources must keep their identity and must not be replaced by the planned default.
- Pick one JSON shape and keep it consistent, for example `{ "items": [] }` for a collection or `[]` for a generic item list.
- Pick one in-memory representation per service method and keep it consistent. If methods return Pydantic objects, use attributes and save with `model_dump(mode="json")`; if methods use dictionaries internally, convert to Pydantic models only at API boundaries.
- Serialize Pydantic models with JSON-compatible values before writing to disk. For Pydantic v2, use `model_dump(mode="json")` when the model contains datetime, UUID, or other non-primitive values.
- Avoid module-level mutable state that makes tests share records between cases. A module-level route service is acceptable only if tests can replace the exact route-module service object before requests are made; otherwise prefer `Depends(...)`.


## Injected resource contract

For JSON-backed services, storage helpers and services must accept either the planned storage filename/path or an explicit temp path from tests. Treat `Path`/absolute/full paths as the exact storage target. Do not convert injected storage paths to only the file name before reading/writing. This is the JSON-storage example of the broader kit rule: any injected test resource handle, locator, repository, adapter, client, or config must be used as supplied and must not be replaced by a default resource or global singleton.

For new JSON-backed services, prefer constructor injection over post-construction mutation:

```python
def get_resource_service() -> ResourceService:
    return ResourceService()

# in tests
app.dependency_overrides[get_resource_service] = lambda: ResourceService(storage_path=temp_file)
```

Avoid patterns such as `service.set_test_storage(temp_file)` unless existing code already requires them. If such a setter exists, it must still preserve the full temp path and must not store only `temp_file.name`.

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
- In this React/FastAPI JSON kit, the standard public API path is `/api/<resources>`. Prefer this wiring:
  - API module: `router = APIRouter(prefix="/<resources>", tags=["<resources>"])`
  - `backend/app/main.py`: `app.include_router(<resources>_router, prefix="/api")`
  - clients/tests: `/api/<resources>`
- Do not split the prefix inconsistently, for example tests call `/api/<resources>` while `main.py` includes the router without `prefix="/api"` and the router only has `prefix="/<resources>"`. That produces working code only after repair.
- Do not duplicate `/api` in both the router and `main.py` unless the generated tests and frontend are deliberately aligned to that exact shape. Prefer the standard split above for new generated artifacts.
- Avoid defining both `/<resources>` and `/api/<resources>` unless the requirement explicitly needs compatibility aliases.
- Search can be either `GET /api/<resources>?q=...` or `GET /api/<resources>/search?q=...`, but tests and UI must use the same endpoint.


## Multi-resource provider composition

When an API endpoint returns or filters a primary resource using data from a related resource, keep the primary service/provider as the owner of primary storage and compose the related service through dependency injection.

Preferred FastAPI shape:

```python
def get_related_service() -> RelatedService:
    return RelatedService()

def get_primary_service(
    related_service: RelatedService = Depends(get_related_service),
) -> PrimaryService:
    return PrimaryService(related_service=related_service)

@router.get("")
def list_primary(
    service: PrimaryService = Depends(get_primary_service),
    related_id: str | None = None,
):
    return service.list_primary(related_id=related_id)
```

Do not fix a related-resource lookup by creating a fresh `PrimaryService(related_service=...)` inside the route handler while dropping `Depends(get_primary_service)`. That loses the primary storage override used by tests and often leaks default mock data into API responses.

If a display field needs external data, populate it in the service/API mapping. Do not make it a Pydantic `computed_field` unless it can be computed only from fields already present on that same model.

## Response enrichment coverage

When a related or derived field is part of the public response model, keep enrichment consistent across every endpoint or service method that returns that model in the validated flow. A typical CRUD resource may return the model from list, detail, create, and update operations. Prefer a single helper such as `_enrich_<entity>_response(...)` or `_with_related_display_fields(...)` used by all relevant methods. If you choose operation-specific logic, update every relevant operation explicitly.

Do not fix only the list response when tests or UI refresh logic also read detail or update responses. Do not make tests require detail/update enrichment while implementation only enriches list. If the approved file plan is too narrow to update the needed owner, record the mismatch in `implementation_report.json` rather than silently editing unplanned files.

- If an endpoint response must expose a new field, relationship id, or related display value through a Pydantic model/DTO/schema, the owning model/DTO/schema file is part of the implementation contract and should be in the file plan. Do not sneak response model changes into an unplanned file just because API/service/tests need the field.

## Mutable-state dependency testability

Use the catalog method `backend.pytest.api.mutable-state` for feature API tests. In this FastAPI kit, that method means `get_<entity>_service()` + `Depends(...)` in the API module and `app.dependency_overrides[...]` in pytest fixtures. For future non-FastAPI stacks, add a separate method or example rather than weakening this contract.
