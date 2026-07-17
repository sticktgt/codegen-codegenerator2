# Pattern: JSON storage CRUD

Use this pattern for local JSON/mock storage adapters and JSON-backed service persistence.

## JSON storage shape

- Use only the planned mock/storage JSON filename. If the plan lists `backend/app/storage/<resource>_json_mock.json`, do not also create `<resource>_mock.json` or any other alias/seed file. The default service path may be this planned file, but injected test resources must keep their identity and must not be replaced by the planned default.
- Pick one JSON shape and keep it consistent, for example `{ "items": [] }` for a collection or `[]` for a generic item list.
- Pick one in-memory representation per service method and keep it consistent. If methods return Pydantic objects, use attributes and save with `model_dump(mode="json")`; if methods use dictionaries internally, convert to Pydantic models only at API boundaries.
- Serialize Pydantic models with JSON-compatible values before writing to disk. For Pydantic v2, use `model_dump(mode="json")` when the model contains datetime, UUID, or other non-primitive values.

## Injected resource contract

For JSON-backed services, storage helpers and services must accept either the planned storage filename/path or an explicit temp path from tests. Treat `Path`/absolute/full paths as the exact storage target. Do not convert injected storage paths to only the file name before reading/writing. This is the JSON-storage example of the broader kit rule: any injected test resource handle, locator, repository, adapter, client, or config must be used as supplied and must not be replaced by a default resource or global singleton.

For new JSON-backed services, prefer constructor injection over post-construction mutation:

```python
def get_resource_service() -> ResourceService:
    return ResourceService()

# in tests
app.dependency_overrides[get_resource_service] = lambda: ResourceService(storage_path=temp_file)
```

Avoid patterns such as `service.set_test_storage(temp_file)` unless existing code already requires them. If such a setter exists, it must still preserve the full temp path and must not store only `temp_file.name`.

Preferred service shape:

```python
class ItemService:
    def __init__(self, storage_path: Path | str | None = None):
        self._storage_path = Path(storage_path) if storage_path is not None else DEFAULT_STORAGE_PATH

    def _read_items(self) -> list[Item]:
        data = read_json_storage(self._storage_path)
        ...
```

Avoid:

```python
self._storage_filename = Path(storage_path).name  # Wrong: loses temp directory isolation.
```


## Diagnostic storage hygiene

Local JSON files under tracked application storage are runtime fixtures, not generated feature artifacts. Tests and diagnostics that mutate data must use test-owned temporary storage, dependency overrides, or explicit restoration. Do not leave tracked storage changes behind after pytest, browser, or manual diagnostic runs.
