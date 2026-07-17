---
name: prototype-crud-flow
description: Optional checklist for implementing or repairing a React frontend plus FastAPI and local JSON CRUD slice in the active prototype kit. Use only when the approved file plan contains both frontend and backend CRUD artifacts.
compatibility: opencode
metadata:
  kit: react-python-json-browser
  status: experimental-noncritical
---

# Prototype CRUD Flow

Use this as a compact cross-layer checklist. Canonical files under `instructions/` remain authoritative.

1. Read `instructions/core/architecture.md`, `instructions/core/architecture-addons/stack/react-python-json-browser.md`, and the relevant layer add-ons under `instructions/core/architecture-addons/`.
2. Keep every source edit inside `prototype/input/file_plan.json`.
3. For backend work, follow `instructions/backend/python-fastapi.md`, `instructions/backend/storage-json.md`, `instructions/backend/patterns/fastapi-api-crud.md`, `instructions/backend/patterns/related-response-enrichment.md`, and `instructions/backend/patterns/json-storage-crud.md`.
4. For frontend work, follow `instructions/frontend/react.md`, `instructions/frontend/patterns/react-crud-list-search.md`, and `instructions/frontend/patterns/react-stable-anchors.md`.
5. Select validation methods from `instructions/testing/test-method-catalog.md` and load only the relevant backend or browser test rules.
6. Write the required structured phase reports; skill loading does not replace any prompt or report requirement.
