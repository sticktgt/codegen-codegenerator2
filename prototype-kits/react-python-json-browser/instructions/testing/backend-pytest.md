# Backend pytest rules

Use these rules when creating or repairing backend tests for this kit.

- Prefer the simplest executable test style that proves the requirement and fits the current application shape. For ordinary FastAPI CRUD behavior, synchronous `TestClient` tests are usually sufficient.
- Async pytest tests, plugins, or other additional test dependencies are allowed when they are technically useful and the dependency is already available, or when the approved file plan explicitly includes the relevant package/dependency file change.
- Do not invent dependency changes from inside a test file. If a missing dependency would be the better solution but package files are not writable in the approved file plan, use available kit dependencies or report the limitation for replanning.
- Keep dependency choices requirement-driven. Do not add a plugin only to compensate for a test design that can be expressed clearly with existing tools.
- Isolate local storage and fixtures. Tests must not leave tracked mock JSON files changed after they run.
- Do not implement test isolation by editing implementation source files on disk from a pytest fixture. This is fragile, leaks across tests, and can leave the workspace changed.
- Prefer dependency injection, constructor parameters, route-module service replacement, FastAPI dependency overrides, or an explicit app/service factory.
- For services that cache storage paths, clients, or singletons at import time, patch or construct the actual service object used by the route so each test really uses the isolated fixture. Patching a function after a singleton has already captured its value is not enough.
- Avoid module-level `TestClient` when the test must replace app dependencies per test. Create the client inside the fixture after dependency overrides or monkeypatches are installed.
- Each test should start from a known dataset, normally an empty temp JSON file or a small temp seed written inside that test/fixture. Do not depend on records created by earlier tests.
- Test expectations must match the implemented requirement semantics. For example, a search test should only expect records that contain the query according to the documented search behavior.


Reference examples:

- `instructions/testing/examples/backend-json-storage-pytest.md` shows one way to isolate JSON-backed storage in backend API tests. Adapt it to the generated service/API shape; do not copy names blindly.
