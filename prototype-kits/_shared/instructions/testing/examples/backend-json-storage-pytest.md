# Example: isolated FastAPI JSON-storage pytest

Use this example with `backend.pytest.api.mutable-state`. Replace `<resource>` names, request fields, and paths with those from the approved scheme and file plans.

```python
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.resources import get_resource_service
from app.main import app
from app.services.resource_service import ResourceService


@pytest.fixture
def client(tmp_path) -> Iterator[TestClient]:
    storage_file = tmp_path / "resources.json"
    storage_file.write_text('{"items": []}', encoding="utf-8")

    app.dependency_overrides[get_resource_service] = (
        lambda: ResourceService(storage_path=storage_file)
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_create_resource(client: TestClient):
    response = client.post(
        "/api/resources",
        json={"primary": "A", "secondary": "B"},
    )

    assert response.status_code == 201
    assert response.json()["primary"] == "A"


def test_update_resource(client: TestClient):
    create_response = client.post(
        "/api/resources",
        json={"primary": "A", "secondary": "B"},
    )
    resource_id = create_response.json()["id"]

    response = client.put(
        f"/api/resources/{resource_id}",
        json={"primary": "A updated"},
    )

    assert response.status_code == 200
    assert response.json()["primary"] == "A updated"
```

Legacy fallback is allowed only when the approved file plan cannot change an existing API module to use FastAPI `Depends(...)`: patch the exact route-module object that endpoints call.

Do not infer the provider from FastAPI route internals. This is unstable and should not be generated:

```python
# Wrong: route order and route internals are not the dependency contract.
app.dependency_overrides[app.routes[1].dependencies[0].dependency] = override_service
```

Do not lose temp-path isolation inside the service:

```python
# Wrong: temp files from different tests collapse to the same tracked filename.
self._storage_filename = Path(storage_file).name
```

Use the injected resource as supplied. For JSON storage, use the full injected path for reads and writes.

New generated FastAPI JSON-backed code should use the provider/dependency-override shape above. Use `json=` for create/update when the public API accepts JSON bodies and query parameters only for list/search/filter operations. Do not patch a helper or class that the endpoint no longer uses, and do not rewrite implementation files from the test fixture.

```python
from app.api import resources as resources_api


@pytest.fixture
def client(tmp_path, monkeypatch):
    service = ResourceService(storage_path=tmp_path / "resources.json")
    monkeypatch.setattr(resources_api, "resource_service", service)
    yield TestClient(app)
```

Smoke tests remain baseline import/health checks. Do not add feature CRUD/search assertions to `backend/tests/test_smoke.py`.
