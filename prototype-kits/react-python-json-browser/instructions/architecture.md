# Architecture Rules

This kit is a small React + Python/FastAPI-style prototype with local JSON/mock storage and browser/e2e validation.

The architecture rules are the primary source of truth for planning and implementation. Python pipeline code may check machine-readable safety boundaries, but it must not reinterpret architectural meaning, invent artifact names, or repair a planner's semantic decisions.

## Three different states

Keep these concepts separate:

1. **Requirement intent**
   - Comes from `prototype/input/run_input.json` and `requirements.json`.
   - Describes what the user wants and acceptance criteria.
   - Does not prescribe file names, file policies, or implementation details.

2. **Scheme context**
   - Comes from `prototype/input/scheme_model.json`.
   - Contains logical elements such as screens, widgets, actions, APIs, services, data, and mocks.
   - A scheme element being present does not prove that its implementation file already exists.

3. **Implementation state**
   - Comes from the actual workspace file tree.
   - Determines whether a planned artifact should be `create`, `modify`, or `read`.

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

## Planning rule

The planner must produce a plan that is already consistent with these rules:

- use the architecture contract for artifact types and allowed paths;
- inspect the workspace file tree before deciding `create` vs `modify`;
- create new owned artifacts only when a new artifact is needed;
- modify existing skeleton/integration files only for wiring;
- do not rely on Python validation to fix artifact types or operations.

## UI anchor invariant

Stable UI anchors are part of the architecture contract for generated prototypes. A frontend screen file that owns a `screen.*` scheme element must put that anchor on the screen root/outermost JSX element. A frontend widget file that owns a `widget.*` scheme element must put that anchor on the widget root/outermost JSX element.

Do not duplicate the same direct `screen.*` or `widget.*` anchor elsewhere in the same source file, for example on both the root container and a nested heading. Browser/e2e tests may use strict locators for these anchors, so duplicate root anchors are invalid even when the UI visually renders correctly.

## Validation rule

Static Python checks may verify format, path safety, allowed roots, forbidden files, UI anchor invariants, and test execution results. They do not own architectural design. If a plan is semantically wrong, the model must correct the plan by following these architecture rules.
