# Backend pytest rules

Read `instructions/testing/test-method-catalog.md` first and use the matching catalog method. For this kit, most backend feature API tests should use `backend.pytest.api.mutable-state`.

Backend tests should validate public backend behavior without changing implementation files at test time.

- Use FastAPI `TestClient` for API contract tests in this kit.
- For new generated FastAPI API routes that read or mutate JSON/mock storage, implement the test seam in the API layer: `get_<entity>_service()` plus `Depends(get_<entity>_service)` in route handlers.
- Pytest fixtures should import the provider directly from the API module, for example `from app.api.<entity> import get_<entity>_service`, and override that exact function with `app.dependency_overrides[get_<entity>_service] = lambda: <Service>(storage_path=temp_file)` before requests are sent.
- The public API paths used by backend pytest should match the kit route wiring. For new generated FastAPI JSON features, use `/api/<resources>` in tests, implement the route module as `APIRouter(prefix="/<resources>")`, and include it from `main.py` with `prefix="/api"`. If all feature API tests return 404, inspect `main.py` and the router prefix before changing test expectations.
- Clear `app.dependency_overrides` in fixture teardown or a `finally` block.
- Initialize a known dataset per test or fixture; do not depend on records created by earlier tests or on tracked mock storage state.
- Use temp directories/files for storage fixtures. Do not symlink over tracked mock files and do not rewrite implementation `.py` files from fixtures.
- When reviewing generated service code, verify that injected test resources keep their identity. A service that stores only `Path(storage_path).name`, recreates a production repository, replaces a fake client with a real client, or falls back to a module-level singleton will share state or hit production-like resources across tests. For JSON storage, keep the full injected path.
- Prefer passing the temp storage path into the service constructor in the override lambda. Avoid generating tests that create a default production-backed service and then call a custom `set_test_storage(...)` mutator unless that mutator is part of the approved pattern. Constructor injection makes it harder to accidentally read/write tracked mock storage.
- Do not discover dependency providers through FastAPI route internals such as `app.routes[...]`, `.dependencies`, `dependant`, or router indexes. Route order is framework/internal state and is not a stable test seam.
- Do not use route-module monkeypatching for new generated FastAPI code when a provider can be added. Route-module replacement is only a legacy fallback for existing code that the file plan does not allow you to refactor.
- Match the generated API request contract: use `json=` for create/update endpoints that accept Pydantic request bodies, and use query params only for list/search/filter endpoints. Backend pytest and frontend calls must use the same request shape and the same query parameter names. If the API parameter is named `search`, tests must pass `params={"search": value}`; if it is named `q`, every layer must use `q`. Use `params=...` rather than raw query-string concatenation so values with `+`, spaces, `&`, `%`, or `#` are encoded correctly.
- Match framework behavior: FastAPI/Pydantic request schema errors usually return 422; use 400 only for explicit domain validation implemented after schema parsing.
- Keep baseline smoke checks separate. Do not add feature CRUD/search assertions to `backend/tests/test_smoke.py`; create or extend the planned feature test file instead.
## Multi-resource dependency overrides

For API tests that cover relationships between resources, override every service provider involved in the request path.

Example: if one API endpoint returns a display value resolved from a related resource service, override both the primary-resource provider and the related-resource provider so they share the same temp-storage fixture. Do not create related records in one temp file while the API resolves display values from the default tracked mock storage.


For composed primary/related services, the primary provider must still be overrideable with the test-owned primary storage. A good test seam is to override `get_primary_service` with `PrimaryService(storage_path=temp_primary, related_service=test_related_service)`. If the endpoint also exposes `get_related_service`, override it as well only when the endpoint or provider uses it directly.

A backend API test should fail if overriding the primary provider does not control the records returned by the endpoint. That usually means the endpoint constructed a replacement primary service with default storage instead of using the injected primary service.

Do not repair a failing related-resource test by switching to only `app.dependency_overrides[get_related_service]` if the endpoint creates a new primary service with default storage. That pattern reads production/mock primary records instead of the test records.

Use fixture teardown to clear overrides after the request sequence.

## Extending existing test files

When a slice adds coverage to an existing backend test file, keep the existing tests unless the requirement explicitly removes the behavior they cover. Add new tests near related coverage or make the smallest targeted edits. Do not replace an existing multi-test file with only the current slice tests.

If a validation plan labels a check as `create_new_test` but the target test file already exists, treat it as an extension case: preserve the file and add missing tests, and record the mismatch in the implementation or repair report. A genuinely new test file should use a path that does not already exist.

