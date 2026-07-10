# Backend pytest rules

Read `instructions/testing/test-method-catalog.md` first and use the matching catalog method. For this kit, most backend feature API tests should use `backend.pytest.api.mutable-state`.

Backend tests should validate public backend behavior without changing implementation files at test time.

- Use FastAPI `TestClient` or the kit's equivalent API client for API contract tests.
- For mutable/external dependencies, use the seam selected by the implementation pattern: FastAPI dependency override, app/service factory, constructor injection, repository interface, or exact route-module service replacement.
- Prefer FastAPI `Depends(get_<entity>_service)` plus `app.dependency_overrides[get_<entity>_service] = ...` for new FastAPI API routes in this kit.
- Initialize a known dataset per test or fixture; do not depend on records created by earlier tests or on tracked mock storage state.
- Use temp directories/files for storage fixtures. Do not symlink over tracked mock files and do not rewrite implementation `.py` files from fixtures.
- Clear dependency overrides and monkeypatches after each test using fixtures/finalizers.
- Match framework behavior: FastAPI/Pydantic request schema errors usually return 422; use 400 only for explicit domain validation implemented after schema parsing.
- Keep baseline smoke checks separate. Do not add feature CRUD/search assertions to `backend/tests/test_smoke.py`; create or extend the planned feature test file instead.
