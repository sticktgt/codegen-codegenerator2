# Kit implementation patterns

Use this file as the index for implementation patterns in this kit. Patterns are reusable recipes for common artifact combinations. They are guidance for implementation shape and testability, not additional writable-file permissions.

Always obey `prototype/input/file_plan.json` first. Read only the pattern files that match artifact types or validation files in the approved file plan.

## Pattern selection

- If the file plan contains `backend_api`, `backend_service`, `backend_model`, or `backend_storage` for a JSON-backed CRUD feature, read `instructions/patterns/backend-fastapi-json-crud.md`.
- If the file plan contains `frontend_screen`, `frontend_widget`, `frontend_action`, or `frontend_behavior` for a React CRUD/list/search flow, read `instructions/patterns/frontend-react-json-crud.md`.
- If the file plan contains backend pytest files for JSON-backed API behavior, also use `instructions/testing/backend-pytest.md` and the backend pytest example.
- If the file plan contains browser/e2e behavior tests, also use `instructions/testing/browser-e2e.md` and the anchored Playwright example.

## How to use patterns

- Adapt names, paths, route prefixes, scheme ids, and labels to the current file plan and requirements.
- Do not copy examples blindly when the approved file plan uses different paths or artifact ownership.
- Do not add files just because a pattern mentions them. If a useful file is not in `file_plan.json`, report the limitation instead of creating it.
- Prefer the implementation shape that makes the planned validation straightforward without test-time source rewrites or cross-test state.
