# Backend pytest rules

Read `instructions/testing/test-method-catalog.md` first and use the matching catalog method. For this kit, most backend feature API tests should use `backend.pytest.api.mutable-state`.

Backend tests should validate public backend behavior without changing implementation files at test time.

- Use FastAPI `TestClient` for API contract tests in this kit.
- For new generated FastAPI API routes that read or mutate JSON/mock storage, implement the test seam in the API layer: `get_<entity>_service()` plus `Depends(get_<entity>_service)` in route handlers.
- Pytest fixtures should import the provider directly from the API module, for example `from app.api.<entity> import get_<entity>_service`, and override that exact function with `app.dependency_overrides[get_<entity>_service] = lambda: <Service>(storage_path=temp_file)` before requests are sent.
- Clear `app.dependency_overrides` in fixture teardown or a `finally` block.
- Initialize a known dataset per test or fixture; do not depend on records created by earlier tests or on tracked mock storage state.
- Use temp directories/files for storage fixtures. Do not symlink over tracked mock files and do not rewrite implementation `.py` files from fixtures.
- When reviewing generated service code, verify that injected test resources keep their identity. A service that stores only `Path(storage_path).name`, recreates a production repository, replaces a fake client with a real client, or falls back to a module-level singleton will share state or hit production-like resources across tests. For JSON storage, keep the full injected path.
- Do not discover dependency providers through FastAPI route internals such as `app.routes[...]`, `.dependencies`, `dependant`, or router indexes. Route order is framework/internal state and is not a stable test seam.
- Do not use route-module monkeypatching for new generated FastAPI code when a provider can be added. Route-module replacement is only a legacy fallback for existing code that the file plan does not allow you to refactor.
- Match the generated API request contract: use `json=` for create/update endpoints that accept Pydantic request bodies, and use query params only for list/search/filter endpoints. Backend pytest and frontend calls must use the same request shape.
- Match framework behavior: FastAPI/Pydantic request schema errors usually return 422; use 400 only for explicit domain validation implemented after schema parsing.
- Keep baseline smoke checks separate. Do not add feature CRUD/search assertions to `backend/tests/test_smoke.py`; create or extend the planned feature test file instead.
