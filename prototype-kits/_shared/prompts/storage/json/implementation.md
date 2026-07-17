# Local JSON storage implementation additions

Additional reads and rules:
- instructions/backend/storage-json.md
- instructions/backend/patterns/fastapi-json-crud.md
- instructions/testing/examples/backend-json-storage-pytest.md, when backend storage isolation is relevant

- For mock/storage JSON files, use exactly the storage path listed in file_plan.json. Do not create alias, fallback, seed, or shortened-name storage files such as `<resource>_mock.json` when the plan lists `<resource>_json_mock.json`. Update service defaults, API code, tests, and UI assumptions to use the planned path or test-owned temp paths.
- Generated or modified tests must use isolated temporary data/fixtures. Do not leave tracked mock storage files such as backend/app/storage/*.json changed after tests run.
- Backend pytest tests must follow `instructions/testing/test-method-catalog.md` and `instructions/testing/backend-pytest.md`. For new generated FastAPI JSON-backed API routes, implement the catalog method `backend.pytest.api.mutable-state`: route handlers use `Depends(get_<entity>_service)`, and tests import that provider directly from the API module and use `app.dependency_overrides[get_<entity>_service]` with test-owned temp storage. Never discover the provider through `app.routes[...]`, `.dependencies`, router order, or other FastAPI internals. Do not use shared tracked mock storage for feature tests. Preserve injected test resources exactly: do not collapse an injected path/handle/adapter/config to a basename, default resource, global singleton, or production mock. Do not rewrite implementation source files from pytest fixtures.
- For JSON-backed service tests, prefer constructor-injected temp storage via the FastAPI dependency override. The service must use the full injected temp path for reads/writes, not `Path(...).name` or the planned mock filename.
