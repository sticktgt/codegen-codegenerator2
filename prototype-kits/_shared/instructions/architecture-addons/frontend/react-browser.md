# Architecture Add-on: React browser frontend

This add-on applies the core architecture rules to the React/browser frontend layer.

## Owned artifacts

| Scheme / responsibility | Artifact type | Directory / pattern |
|---|---|---|
| Screen / primary view | `frontend_screen` | `frontend/src/screens/{PascalName}Screen.jsx` |
| Reusable UI widget | `frontend_widget` | `frontend/src/widgets/{PascalName}.jsx` |
| Frontend user/API action | `frontend_action` | `frontend/src/actions/{PascalName}.js` |
| Browser/e2e validation | `frontend_behavior_test` | `frontend/e2e/{snake_name}.spec.js` or `frontend/e2e/{PascalName}.spec.js` |

## Existing skeleton and integration files

A greenfield slice starts from a kit skeleton, not from an empty directory. Existing skeleton/integration files must be modified, not created.

| Existing file | Artifact type | Operation |
|---|---|---|
| `frontend/src/routes/routeRegistry.js` | `frontend_integration` | `modify` |
| `frontend/src/App.jsx` | `frontend_integration` | `modify` only when needed |

## UI anchor invariant

Stable UI anchors are part of the architecture contract for generated prototypes. A frontend screen file that owns a `screen.*` scheme element must put that anchor on the screen root/outermost JSX element. A frontend widget file that owns a `widget.*` scheme element must put that anchor on the widget root/outermost JSX element.

Do not duplicate the same direct `screen.*` or `widget.*` anchor elsewhere in the same source file, for example on both the root container and a nested heading. Browser/e2e tests may use strict locators for these anchors, so duplicate root anchors are invalid even when the UI visually renders correctly.
