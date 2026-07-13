# Example: FastAPI JSON storage pytest with isolated mutable state

Use this example with catalog method `backend.pytest.api.mutable-state`.

Preferred FastAPI shape for this kit:

```python
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.notes import get_note_service
from app.main import app
from app.services.note_service import NoteService


@pytest.fixture
def client(tmp_path: Path):
    storage_file = tmp_path / "notes.json"
    storage_file.write_text('{"notes": []}', encoding="utf-8")

    app.dependency_overrides[get_note_service] = lambda: NoteService(storage_path=storage_file)
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_create_note(client: TestClient):
    response = client.post("/api/notes", json={"title": "A", "content": "B"})

    assert response.status_code == 201
    assert response.json()["title"] == "A"


def test_update_note(client: TestClient):
    create_response = client.post("/api/notes", json={"title": "A", "content": "B"})
    note_id = create_response.json()["id"]

    response = client.put(f"/api/notes/{note_id}", json={"title": "A updated"})

    assert response.status_code == 200
    assert response.json()["title"] == "A updated"
```

Legacy fallback only when the approved file plan cannot change an existing API module to use FastAPI `Depends(...)`: patch the exact route-module object that endpoints call.

Do not infer the provider from FastAPI route internals. This is unstable and should not be generated:

```python
# Wrong: route order and route internals are not the dependency contract.
app.dependency_overrides[app.routes[1].dependencies[0].dependency] = override_get_item_service
```

Do not lose temp-path isolation inside the service. This also should not be generated:

```python
# Wrong: temp files from different tests collapse to the same tracked filename.
self._storage_filename = Path(storage_file).name
```

Use the injected resource as supplied instead. In this JSON-storage example, that means using the full injected path for reads and writes.

New generated FastAPI JSON-backed code should use the provider/dependency override shape above, not this fallback. Do not test create/update with query params when the frontend/API contract uses JSON bodies; use `json=` for create/update and query params for list/search filters. Do not patch a helper or class that is no longer used by the endpoint, and do not rewrite implementation files from the test fixture.

```python
from app.api import notes as notes_api

@pytest.fixture
def client(tmp_path, monkeypatch):
    service = NoteService(storage_path=tmp_path / "notes.json")
    monkeypatch.setattr(notes_api, "note_service", service)
    yield TestClient(app)
```

Smoke tests remain baseline import/health checks. Do not add feature CRUD/search assertions to `backend/tests/test_smoke.py`.
