Implement the current slice using the approved plan.

Read:
- prototype/input/file_plan.json
- prototype/input/validation_plan.json, if present
- prototype/input/requirements.json
- prototype/input/scheme_model.json
- prototype/input/run_input.json, if present
- prototype/input/implementation_slice.json
- prototype/input/kit.yaml
- prototype/input/generation-rules.yaml
- prototype/input/architecture-contract.yaml
- instructions/architecture.md
- instructions/coding-rules.md
- instructions/validation-rules.md
- instructions/implementation-patterns.md
- relevant pattern files listed in instructions/implementation-patterns.md for artifact types present in file_plan.json
- instructions/testing/test-method-catalog.md, if creating or updating any validation test
- instructions/testing/backend-pytest.md, if creating or updating backend pytest tests
- instructions/testing/browser-e2e.md, if creating or updating browser/e2e tests

Canonical instruction paths:
- Runtime workspace copies live under `instructions/...` at the workspace root.
- Markdown instructions are available from the workspace-root `instructions/` tree.
- Use `prototype/input/...` only for JSON/YAML run inputs and machine-readable contracts.

Rules:

Pipeline phase output discipline:
- Use prototype/input/file_plan.json as the only allowed file plan.
- Before the first Write/Edit, derive the exact writable path set from file_plan.json and validation_plan.json. Keep this checklist in your working notes and only write paths from that set plus required prototype/output reports.
- Treat common baseline/config files as read-only unless explicitly writable in file_plan.json: backend/tests/test_smoke.py, backend/requirements.txt, frontend/package.json, frontend/playwright.config.js, frontend/vite.config.js.
- Do not infer additional files from design_delta or naming symmetry. If a new scheme element is screen-internal, implement it only inside its owning artifact when that artifact is allowed by file_plan.json.
- Do not create, edit, rename, or delete files outside file_plan.json.
- For mock/storage JSON files, use exactly the storage path listed in file_plan.json. Do not create alias, fallback, seed, or shortened-name storage files such as `notes_mock.json` when the plan lists `notes_json_mock.json`. Update service defaults, API code, tests, and UI assumptions to use the planned path or test-owned temp paths.
- Respect file policies in file_plan.json:
  - must_create: create the file if it does not exist.
  - may_modify / modify_allowed: modify only if needed.
  - no_change / may_read / read_only: read only; do not edit.

File operation discipline:
- For any file-plan item with operation `create` or policy `must_create`, do not read the target file first. It is expected to be missing. Create it with Write.
- For any file-plan item with operation `modify` or policy `may_modify`, read the existing file and use Edit only with exact text. If the existing file is empty, use Write as an intentional full-file replacement.
- Do not convert a planned modify of a skeleton/integration file into a new file creation.
- For any existing empty or whitespace-only file that must be replaced entirely, use Write for an intentional full-file replacement; never call Edit with an empty `oldString`. This commonly applies to skeleton package files such as `__init__.py`, but the rule is general.
- Use Edit only when modifying an existing file and you have the exact old text to replace.
- Do not treat failed reads of planned create files as a validation problem; create the planned files.
- Do not run the full validation suite from OpenCode implementation. The official validation is performed later by the pipeline. Do not run `tools/run_validation.py` from implementation. Use only minimal, phase-local diagnostics when necessary, such as Python syntax checks for generated backend files.
- For frontend diagnostics, do not use `node --check` on `.jsx` files or Playwright spec files. JSX and Playwright ESM syntax are handled by the configured Vite/Playwright commands, not by raw Node syntax checking.
- Do not rewrite the whole application.
- Do not implement requirements outside the current scenario/run input slice.
- If `run_input.json` is present, use it only as requirement context; do not infer extra writable files from it beyond file_plan.json.
- Preserve existing accepted behavior by default. If the file plan marks an existing artifact as read-only/no_change, reuse it rather than repurposing it.
- For confirm/cancel flows, keep existing destructive actions/API wrappers stable unless file_plan.json explicitly allows and explains changing them.
- If the slice extends existing behavior, prefer wrappers, UI state, or new artifacts over changing the stable responsibility of an existing action/API/service.
- New dependencies are allowed only when file_plan.json explicitly includes the relevant package/config files as writable and the plan explains why the dependency is needed. Do not invent unplanned dependency files.
- If a planned test or implementation would be better with a missing dependency but package/config files are not writable, use available kit dependencies when reasonable or report the limitation in implementation_report.json for replanning.
- Do not use react-router-dom, axios, or undeclared external packages.
- Match existing frontend integration contracts exactly. Inspect `frontend/src/App.jsx` before editing `routeRegistry.js`; for the current kit, route entries must provide `component: ScreenComponent` because App reads `routes[0].component`. Do not use `element` or invent navigation links unless the baseline app actually consumes/renders them.
- Use backend imports rooted at app.*, not backend.app.*.
- If a validation test file is listed in file_plan.json, follow its policy, `validation_intent`, and any `test_method_id`/catalog guidance:
  - `validation_intent: "rerun_existing"` with `read_only`/`read`: do not edit the test file; it is an existing regression check to be rerun by validation.
  - `validation_intent: "extend_existing_test"`: update the existing test file only for the missing acceptance-criteria coverage.
  - `validation_intent: "create_new_test"`: create the planned test file only if file_plan.json allows it.
  - `validation_intent: "rerun_behavior_test"` with read-only/read: do not edit the browser/e2e test file; it is existing coverage.
  - `validation_intent: "extend_behavior_test"`: update the planned browser/e2e test only if file_plan.json allows it.
  - `validation_intent: "create_behavior_test"`: create the planned browser/e2e test only if file_plan.json allows it and the kit capability is enabled.
- For non-file checks such as `ui_static`, do not create any test file; just implement the required UI anchors in the allowed UI artifact.
- Otherwise do not create tests.
- Do not modify `backend/tests/test_smoke.py` for feature-specific API behavior. If smoke is present in file_plan.json as anything other than read-only/rerun coverage, report the conflict in `implementation_report.json` rather than extending smoke.
- For Playwright repeated item actions, first locate the item/card and then call actions inside that locator. Avoid chained `>> text=... >>` selector strings for row actions.
- For Playwright assertions inside repeated table/list rows, first locate the runtime-owned row/card, then assert the intended field/cell. Do not use `getByText()` for short, numeric, or repeated values such as stock quantities, prices, status/category labels, or codes. Prefer field display anchors or scoped table cells such as `row.locator('td').nth(<known-column-index>)`. Do not use `.first()`/`.last()` to hide ambiguous matches.
- For generated forms, add auxiliary `form.<entity>` and `field.<entity>-<field>` anchors and use them in browser/e2e. Do not write tests that locate inputs via `getByText('Label').locator('input')` or by global form roles.
- For `web.e2e.playwright.crud-list-search-flow`, create one compact user-journey test with `test.step(...)`, not many independent browser tests that share mutable state. Do not add browser coverage for unrequested behavior such as delete/confirmation or multi-record edge cases.

- Generated or modified tests must use isolated temporary data/fixtures. Do not leave tracked mock storage files such as backend/app/storage/*.json changed after tests run.
- Backend pytest tests must follow `instructions/testing/test-method-catalog.md` and `instructions/testing/backend-pytest.md`. For new generated FastAPI JSON-backed API routes, implement the catalog method `backend.pytest.api.mutable-state`: route handlers use `Depends(get_<entity>_service)`, and tests import that provider directly from the API module and use `app.dependency_overrides[get_<entity>_service]` with test-owned temp storage. Never discover the provider through `app.routes[...]`, `.dependencies`, router order, or other FastAPI internals. Do not use shared tracked mock storage for feature tests. Preserve injected test resources exactly: do not collapse an injected path/handle/adapter/config to a basename, default resource, global singleton, or production mock. Do not rewrite implementation source files from pytest fixtures.
- Keep the HTTP request payload contract consistent across backend API, frontend calls, and backend pytest. For generated browser-backed CRUD in this kit, create/update endpoints should accept JSON request bodies and tests/frontend should use JSON for create/update; list/search/filter should use query parameters. Query parameter names must match exactly across API, frontend, and pytest: do not let one layer use `q` while another uses `search`. When values can contain `+`, spaces, `&`, `%`, or `#`, use encoded query params (`params=...` in pytest/TestClient, `URLSearchParams` or equivalent in frontend) instead of raw URL concatenation.
- Browser/e2e tests must follow `instructions/testing/test-method-catalog.md` and `instructions/testing/browser-e2e.md`: use repeatable test-owned data, scoped prototype anchors, awaited Playwright async locator APIs, and visible-state waits after async UI transitions before derived assertions. After editing a record, locate/assert/search by the current edited value or a stable id, not by the old value for any changed field. Keep runtime values that are reused across `test.step(...)` sections in parent test scope; do not reference variables declared only inside another step. After create/edit submit, wait for the requested domain outcome such as a created or edited row/card; do not assert optional form disappearance unless form closing is an explicit requirement. Do not inspect backend storage files directly from Playwright.
- For this kit, wire FastAPI resources as `/api/<resources>` using `APIRouter(prefix="/<resources>")` in the API module and `app.include_router(router, prefix="/api")` in `backend/app/main.py`; keep backend pytest and frontend fetch URLs on the same public path.
- For JSON-backed service tests, prefer constructor-injected temp storage via the FastAPI dependency override. The service must use the full injected temp path for reads/writes, not `Path(...).name` or the planned mock filename.
- For multi-field search browser coverage, after each search query fill, wait for a runtime-owned row/card containing the searched current value before using count assertions.
- If a requirement says users can search by multiple fields (for example name, email, or phone), implement and test that user-visible capability. Either make one free-text search search across all named fields, or render explicit controls for those fields; do not expose only a name search while the API privately supports email/phone search.
- If validation_plan.json proposes a test file that is not present in file_plan.json, do not create it; report the limitation.
- Use the kit implementation patterns selected by instructions/implementation-patterns.md when they match the approved file plan. Patterns are implementation guidance only; they do not grant permission to create files outside file_plan.json.
- Write prototype/output/implementation_report.json.
- Write prototype/output/change_manifest.json.

The implementation report must include changed files, related requirements, related scheme elements, and any deviations from the file plan.

change_manifest.json shape:
{
  "changes": [
    {
      "requirement_ids": ["REQ-..."],
      "scheme_element_ids": ["..."],
      "file": "relative/path",
      "change_type": "create|modify|delete",
      "location_hint": "short human-readable location",
      "summary": "what changed"
    }
  ]
}


Architecture contract requirement:
- Follow `prototype/input/architecture-contract.yaml` for artifact types, allowed roots, path placement, test capabilities, dependency policy, and UI anchor conventions.
- Do not invent file placement rules outside the contract.

UI implementation requirement:
- For every new or changed web UI control that directly implements a scheme action, add a stable `data-prototype-id` anchor using the exact scheme element id, for example `data-prototype-id="action.delete-note"`.
- This applies to buttons, links, form controls, confirmation controls, cancel/confirm actions, tabs, and other clickable controls introduced or behaviorally changed by the slice.
- For every created or modified frontend screen file whose file-plan item contains a `screen.*` scheme element, ensure the screen root/outermost JSX element has `data-prototype-id` with that exact `screen.*` id, for example `data-prototype-id="screen.note-list"`. Preserve an existing screen anchor if it already exists.
- For every created or modified frontend widget file whose file-plan item contains a `widget.*` scheme element, ensure the widget root/outermost JSX element has `data-prototype-id` with that exact `widget.*` id, for example `data-prototype-id="widget.note-count-summary"`.
- Use each direct `screen.*` or `widget.*` root anchor only once per source file. Do not repeat the same screen/widget anchor on nested headings, wrappers, labels, or controls; browser tests may locate these anchors in strict mode.
- Anchor obligations are scoped to the current file-plan item: do not add unrelated action anchors to a widget just because the same requirement also uses actions in a screen. Put action anchors on the actual UI controls that implement those actions, usually in the screen or component that renders the buttons/form controls.
- Use exact scheme ids for action anchors. Do not create suffixed variants such as `action.create-note-submit`; if a button changes between create/edit modes, use static literal alternatives such as `data-prototype-id={editing ? 'action.edit-note' : 'action.create-note'}` or separate conditional buttons with literal anchors.
- If the UI control, screen, or widget cannot reasonably have an anchor, document the deviation in `implementation_report.json`; do not silently omit it.

Workspace path discipline:
- Treat the current working directory as the workspace root.
- Read and write `prototype/input/...` and `prototype/output/...` relative to the workspace root.
- Never use `/runs/<run-name>/prototype/...`; the valid path is `/runs/<run-name>/workspace/prototype/...` when an absolute path is unavoidable.
- Do not read from run-level `input/` or `output/` unless the prompt explicitly asks for a diagnostics-only fallback.

- For enum/status/category fields in browser/e2e, assert the intended user-visible display value. Do not assume the raw API value such as `in_progress` is rendered if the UI formats it as a human label such as `In progress`; align UI rendering and Playwright assertions deliberately.


Browser/e2e first-pass self-check:
- If the create UI uses a separate opener button, render `control.open-create-<entity>` on the opener and render `action.create-<entity>` only on the submit/save control inside `form.<entity>`.
- The generated Playwright spec must click the opener control and then scope the submit action inside the visible form; do not make the same `action.create-*` anchor serve both roles.
- After search/filter changes, wait for the expected runtime-owned row/card to be visible before using `count()` or absence assertions.
- If a search/filter Clear or Reset control is generated, implement it as a real reset: clear all relevant UI state and reload unfiltered results using explicit empty query/filter arguments. Do not call a loader that reads stale React state immediately after `setState`. Prefer a loader that accepts overrides, e.g. `fetchItems({ query: '', category: '' })` for reset.
