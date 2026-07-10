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
```

Fallback only when the implementation does not use FastAPI `Depends(...)`: patch the exact route-module object that endpoints call. Do not patch a helper or class that is no longer used by the endpoint, and do not rewrite implementation files from the test fixture.

```python
from app.api import notes as notes_api

@pytest.fixture
def client(tmp_path, monkeypatch):
    service = NoteService(storage_path=tmp_path / "notes.json")
    monkeypatch.setattr(notes_api, "note_service", service)
    yield TestClient(app)
```

Smoke tests remain baseline import/health checks. Do not add feature CRUD/search assertions to `backend/tests/test_smoke.py`.
