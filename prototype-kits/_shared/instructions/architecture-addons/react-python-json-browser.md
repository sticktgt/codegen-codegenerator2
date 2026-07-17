# React + Python + JSON Browser Architecture Add-on

This add-on applies the core architecture rules to the active `react-python-json-browser` kit: React frontend, Python/FastAPI-style backend, local JSON/mock storage, and browser/e2e validation.

## Layers and owned artifacts

New owned artifacts are created in their layer-specific directories:

| Scheme / responsibility | Artifact type | Directory / pattern |
|---|---|---|
| Screen / primary view | `frontend_screen` | `frontend/src/screens/{PascalName}Screen.jsx` |
| Reusable UI widget | `frontend_widget` | `frontend/src/widgets/{PascalName}.jsx` |
| Frontend user/API action | `frontend_action` | `frontend/src/actions/{PascalName}.js` |
| Backend API resource | `backend_api` | `backend/app/api/{snake_resource}.py` |
| Backend service/component | `backend_service` | `backend/app/services/{snake_name}.py` |
| Backend data model | `backend_model` | `backend/app/models/{snake_name}.py` |
| Storage adapter / mock data / storage init | `backend_storage` | `backend/app/storage/{snake_name}.py`, `backend/app/storage/{snake_name}_mock.json`, `backend/app/storage/__init__.py` |
| Backend pytest validation | `backend_test` | `backend/tests/test_{snake_name}.py` |
| Browser/e2e validation | `frontend_behavior_test` | `frontend/e2e/{snake_name}.spec.js` or `frontend/e2e/{PascalName}.spec.js` |

## Existing skeleton and integration files

A greenfield slice starts from a kit skeleton, not from an empty directory. Existing skeleton/integration files must be modified, not created.

| Existing file | Artifact type | Operation |
|---|---|---|
| `frontend/src/routes/routeRegistry.js` | `frontend_integration` | `modify` |
| `frontend/src/App.jsx` | `frontend_integration` | `modify` only when needed |
| `backend/app/main.py` | `backend_integration` | `modify` |
| `backend/app/storage/__init__.py` | `backend_storage` | `modify` |
| Existing `__init__.py` package markers | owning package/layer artifact type | `modify` only if needed |

Do not classify `backend/app/storage/__init__.py` as `backend_integration`. In this kit `backend_integration` means `backend/app/main.py`.

## Cross-layer rule

Keep frontend and backend loosely coupled through simple API/action functions. Use local JSON/mock storage for this kit unless the approved file plan explicitly changes the storage approach.

## UI anchor invariant

Stable UI anchors are part of the architecture contract for generated prototypes. A frontend screen file that owns a `screen.*` scheme element must put that anchor on the screen root/outermost JSX element. A frontend widget file that owns a `widget.*` scheme element must put that anchor on the widget root/outermost JSX element.

Do not duplicate the same direct `screen.*` or `widget.*` anchor elsewhere in the same source file, for example on both the root container and a nested heading. Browser/e2e tests may use strict locators for these anchors, so duplicate root anchors are invalid even when the UI visually renders correctly.
