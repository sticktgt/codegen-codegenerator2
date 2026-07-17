# Architecture Add-on: Python / FastAPI backend

This add-on applies the core architecture rules to the Python/FastAPI backend layer.

## Owned artifacts

| Scheme / responsibility | Artifact type | Directory / pattern |
|---|---|---|
| Backend API resource | `backend_api` | `backend/app/api/{snake_resource}.py` |
| Backend service/component | `backend_service` | `backend/app/services/{snake_name}.py` |
| Backend data model | `backend_model` | `backend/app/models/{snake_name}.py` |
| Backend pytest validation | `backend_test` | `backend/tests/test_{snake_name}.py` |

## Existing skeleton and integration files

| Existing file | Artifact type | Operation |
|---|---|---|
| `backend/app/main.py` | `backend_integration` | `modify` |
| Existing `__init__.py` package markers | owning package/layer artifact type | `modify` only if needed |

Do not classify `backend/app/storage/__init__.py` as `backend_integration`. In this kit `backend_integration` means `backend/app/main.py`.

## API boundary

Keep the API layer thin: request/response validation and route wiring belong in `backend/app/api/...`; business logic and storage access belong in `backend/app/services/...`.
