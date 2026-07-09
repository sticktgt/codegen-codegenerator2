# Example: backend pytest with isolated JSON storage

This is a reference pattern, not a mandatory implementation. Adapt names and injection points to the generated application.

The important point is that the API route must use the same isolated service/storage that the test inspects. Do not rewrite implementation source files from a pytest fixture.

```python
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.item_service import ItemService
from app.api import items as items_module


@pytest.fixture
def client_with_temp_storage(tmp_path, monkeypatch):
    storage_file = tmp_path / "items.json"
    storage_file.write_text("[]", encoding="utf-8")

    # Construct a fresh service using the temp storage for this test.
    service = ItemService(storage_path=storage_file)

    # Patch the dependency object actually used by the route module.
    # If the generated app uses FastAPI dependencies, use app.dependency_overrides instead.
    monkeypatch.setattr(items_module, "item_service", service)

    # Create the client after patching dependencies when the app/route captures state.
    client = TestClient(app)
    return client, storage_file


def read_items(storage_file):
    return json.loads(storage_file.read_text(encoding="utf-8"))


def test_create_item(client_with_temp_storage):
    client, storage_file = client_with_temp_storage

    response = client.post("/items", json={"title": "Example"})

    assert response.status_code in (200, 201)
    assert read_items(storage_file)[0]["title"] == "Example"
```

Key ideas:

- Each test gets a fresh temp storage file.
- The test injects the service/path before calling the API.
- The assertion reads the same isolated storage used by the API.
- No tracked mock JSON file is mutated.
- No implementation `.py` file is rewritten by the test fixture.
- If the generated service cannot accept `storage_path`, patch or construct the actual dependency used by the route module instead of assuming a path monkeypatch affects an already-created singleton.
- If dependency injection is not possible, it is often better to repair the implementation to expose a small injection point than to make tests patch source files on disk.
