# Backend pytest method catalog

## backend.pytest.api.mutable-state

Use for Python backend API behavior when endpoints read or mutate JSON files, SQLite files, in-memory repositories, mock adapters, or other external/mutable state.

Contract for this FastAPI kit:
- Test through the public API using `TestClient`.
- Generated API routes that use mutable state must expose a provider function such as `get_<entity>_service()` in the API module.
- Route handlers must receive the service through `Depends(get_<entity>_service)`. Do not hide the service only in a module-level singleton that tests cannot override.
- Feature pytest fixtures must import the provider function directly from the API module and override that exact function: `from app.api.<entity> import get_<entity>_service`; `app.dependency_overrides[get_<entity>_service] = lambda: <Service>(storage_path=temp_file)`.
- Generated browser-backed CRUD APIs must use one request payload contract across backend, frontend, and pytest. For this kit, `POST` create and `PUT`/`PATCH` update endpoints should accept JSON request bodies through Pydantic request models; `GET` list/search/filter endpoints may use query parameters. Frontend `fetch` calls and backend pytest must use the same shape (`json=`/JSON body for create/update, `params`/query string for list filters).
- For new FastAPI JSON-backed resources in this kit, use one standard public path: `/api/<resources>`. Implement it as router `prefix="/<resources>"` plus `app.include_router(router, prefix="/api")`; backend pytest and frontend calls should use `/api/<resources>`. Do not silently adapt tests to an unplanned route-prefix mismatch.
- Clear dependency overrides in fixture teardown.
- Do not introspect FastAPI route internals to find dependencies. Never use `app.routes[...]`, `.dependencies`, `dependant`, or route-order indexes as the key for `app.dependency_overrides`; these are framework internals, not the provider contract.
- Each test or fixture owns a fresh temp storage path. Do not symlink or overwrite tracked mock JSON files.
- The service/storage layer must preserve the injected test resource identity. Do not let implementation convert an injected temp path, repository, adapter, client, or config to a basename, default resource, global singleton, or planned production mock; that breaks test isolation even when dependency override is correct. For JSON storage this means using the full injected path for reads and writes.
- Do not rewrite implementation `.py` files from pytest fixtures and do not depend on records created by earlier tests.
- Backend pytest files must import or define every direct symbol they use in fixtures and test function bodies. If a test constructs model objects such as `<Entity>(...)` directly, import the model explicitly from its owning module; do not assume implementation-module imports are visible to the test.

Use this method for API edge cases, request validation, not-found cases, and most negative cases. Do not move these edge cases into browser/e2e unless they are explicitly user-visible UI behavior.

For future non-FastAPI stacks, add a separate method or stack-specific example instead of weakening this kit method.

## backend.pytest.service.unit

Use for pure service/model logic that is not primarily an HTTP contract and does not need the app router.

Expected shape:
- Instantiate the service/model directly with isolated dependencies.
- Test deterministic inputs and outputs.
- Avoid filesystem/network state unless the service responsibility is specifically about that adapter.

## backend.smoke.import-health

Use only to rerun baseline import/health/route sanity checks already present in the kit.

Expected shape:
- `backend/tests/test_smoke.py` is normally read-only rerun coverage.
- Do not create, extend, or modify smoke tests for feature-specific API behavior.
- Feature behavior belongs in a feature API test such as `backend/tests/test_<feature>_api.py` or in a service test when appropriate.
