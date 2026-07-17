# Architecture Add-on: local JSON/mock storage

This add-on applies the core architecture rules to a local JSON/mock storage layer.

## Owned artifacts

| Scheme / responsibility | Artifact type | Directory / pattern |
|---|---|---|
| Storage adapter / mock data / storage init | `backend_storage` | `backend/app/storage/{snake_name}.py`, `backend/app/storage/{snake_name}_mock.json`, `backend/app/storage/__init__.py` |

## Existing skeleton and integration files

| Existing file | Artifact type | Operation |
|---|---|---|
| `backend/app/storage/__init__.py` | `backend_storage` | `modify` |
| Existing `__init__.py` package markers | owning package/layer artifact type | `modify` only if needed |

Use local JSON/mock storage for this kit unless the approved file plan explicitly changes the storage approach. Preserve injected test storage paths exactly; do not collapse them to a basename, default mock file, global singleton, or another canonical storage filename.
