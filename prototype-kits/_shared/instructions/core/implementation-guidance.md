# Implementation Guidance Index

Use these patterns as reusable kit guidance. They are not a permission system: `prototype/input/file_plan.json` remains the only source of writable files.

Principle:
- Keep pattern text as principle + kit-specific example.
- Do not turn one demo failure into a global rule; when a detail is specific to FastAPI, JSON storage, React, or Playwright, say so explicitly.
- When a new recurring situation appears, add a short catalog/pattern entry instead of scattering duplicate reminders across prompts.

Relevant files for this kit:
- `instructions/testing/test-method-catalog.md` — canonical testing methods for backend, UI static, and browser/e2e validation.
- `instructions/backend/patterns/fastapi-api-crud.md` — FastAPI API/service/route CRUD pattern.
- `instructions/backend/patterns/related-response-enrichment.md` — related/derived response-field enrichment pattern.
- `instructions/backend/patterns/json-storage-crud.md` — JSON storage persistence pattern.
- `instructions/frontend/patterns/react-crud-list-search.md` — React CRUD/list/search screen pattern.
- `instructions/frontend/patterns/react-stable-anchors.md` — React stable UI anchor pattern.
- `instructions/testing/backend-pytest.md` — pytest-specific implementation rules.
- `instructions/testing/browser-e2e.md` — Playwright-specific implementation rules.

Selection guidance:
- If the file plan includes backend API/service/model/storage artifacts, read the backend CRUD pattern.
- If the file plan includes React screen/widget/action artifacts, read the frontend CRUD pattern.
- If the file plan creates or modifies `backend/tests/*.py`, read the test method catalog and backend pytest rules before reporting implementation complete; the backend pytest import/symbol gate is mandatory for those files.
- If the validation plan includes browser/e2e files, read the test method catalog and browser/e2e rules.

Optional OpenCode skill:
- `.opencode/skills/prototype-crud-flow/SKILL.md` exposes a compact cross-layer CRUD checklist through the native skill tool. It is supplementary only; the canonical instruction files above remain authoritative and the pipeline must still work when the skill is not loaded.
