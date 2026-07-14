Repair validation failures or file-boundary failures for the current slice.

Read:
- prototype/output/repair_context.json, if present; use it as the compact repair entry point
- prototype/output/changed_files.json, if present
- prototype/output/validation_result.json, if present
- prototype/output/ui_static_check_result.json, if present
- validation logs referenced by validation_result.json, if present
- prototype/input/file_plan.json
- prototype/input/requirements.json
- prototype/input/scheme_model.json
- prototype/input/run_input.json, if present
- prototype/input/implementation_slice.json
- prototype/input/architecture-contract.yaml, if needed
- instructions/architecture.md, if needed
- instructions/repair-rules.md, if needed
- instructions/validation-rules.md, if needed
- instructions/implementation-patterns.md, if the failure is a recurring implementation/testability mismatch
- relevant pattern files listed in instructions/implementation-patterns.md for the failed artifact types, if applicable
- instructions/testing/test-method-catalog.md, if repairing validation tests or implementation/testability mismatches
- instructions/testing/backend-pytest.md, if repairing backend pytest tests
- instructions/testing/examples/backend-json-storage-pytest.md, if backend test storage isolation is failing
- instructions/testing/browser-e2e.md, if repairing browser/e2e tests
- instructions/testing/examples/browser-anchored-flow-playwright.md, if Playwright selector or flow stability is failing

Canonical instruction paths:
- Runtime workspace copies live under `instructions/...` at the workspace root.
- Markdown instructions are available from the workspace-root `instructions/` tree.
- Use `prototype/input/...` only for JSON/YAML run inputs and machine-readable contracts.

Rules:

Pipeline phase output discipline:
- The goal is working generated code that satisfies the rules, not just a better failure report. Use the established testing methods from `instructions/testing/test-method-catalog.md`; do not invent a new local testing style when a catalog method matches the failure. Diagnostics exist to choose the next targeted repair.
- Fix only validation failures and file-boundary violations for the current scenario/run input slice.
- Treat file-boundary violations from `prototype/output/changed_files.json` as root repair targets. Before changing tests for validation failures, check `unexpected_files`, `policy_violations`, and `missing_required_*`; remove or revert unplanned files first, then keep the implementation using only planned paths. If an unexpected file duplicates a planned storage/mock file, delete the unexpected duplicate and update all references to the planned file.
- If `run_input.json` is present, use it only as requirement context; do not infer extra writable files from it beyond file_plan.json.
- Use prototype/input/file_plan.json as the only allowed file plan for implementation changes.
- Do not create new files outside file_plan.json.
- Add or change dependencies only when file_plan.json explicitly marks the relevant package/config files as writable. Otherwise repair with available kit dependencies or report the limitation.
- Respect validation intent in file_plan.json. If a test file has `validation_intent: "rerun_existing"` or `"rerun_behavior_test"`, or a read-only/no_change policy, do not edit it; fix implementation or report the validation limitation instead.
- During repair, add browser/e2e dependencies or tasks only when file_plan.json explicitly allows the relevant package/task files to change. If frontend behavior validation needs a missing runner and those files are not writable, report the kit limitation.
- Do not modify `frontend/package.json` merely to satisfy ad-hoc diagnostics such as raw Node ESM checks. Only change package/config files when the canonical validation failure genuinely requires it and file_plan.json allows it.
- If tests changed tracked mock storage or runtime fixtures, repair the tests to use isolated temporary data or exact restoration; do not treat fixture mutation as an implementation change.
- For backend test isolation failures, follow `instructions/testing/test-method-catalog.md` and `instructions/testing/backend-pytest.md`: for new generated FastAPI JSON-backed routes, route handlers should use `Depends(get_<entity>_service)`, and tests should import that provider directly from the API module and use `app.dependency_overrides[get_<entity>_service]` with test-owned temp storage. If a generated test uses `app.routes[...]`, `.dependencies`, router order, or other FastAPI internals to find the provider, replace it with a direct provider import. Do not keep retrying pytest against shared tracked mock storage and do not rewrite implementation source files from pytest fixtures.
- If validation failure appears to require a missing dependency, add it only when the package file is explicitly writable in file_plan.json; otherwise adjust unsupported generated tests to available dependencies or report the limitation.
- If backend pytest fails because frontend/backend/tests disagree on request shape or query parameter names, repair the API, frontend API calls, and backend pytest to one contract. For this kit, generated browser-backed CRUD create/update should use JSON request bodies with Pydantic request models; list/search/filter should use query params. Keep query parameter names exact across layers (`q` vs `search` mismatches are failures), and encode query values through `params`/`URLSearchParams` when values may contain `+`, spaces, `&`, `%`, or `#`.
- If feature API tests return 404 for `/api/<resources>`, inspect `backend/app/main.py` and the API router prefix before changing tests. For new JSON-backed FastAPI features in this kit, repair toward `APIRouter(prefix="/<resources>")` plus `app.include_router(router, prefix="/api")`, with frontend and tests calling `/api/<resources>`.
- If backend pytest fails because a generated test imported an unavailable plugin such as `pytest_asyncio`, either use the planned dependency change when package files are writable, or rewrite the test to available kit dependencies such as synchronous FastAPI `TestClient`.
- Do not change scope or implement new requirements.
- Preserve existing behavior.
- If changed_files.json lists unexpected files created by this run, remove them.
- If changed_files.json lists unexpected modifications to files outside file_plan.json, revert those files to their previous/baseline content.
- If changed_files.json lists policy violations for no_change/read_only files, revert those changes.

File operation discipline:
- Use Write for intentional full-file replacement of empty or whitespace-only files; never call Edit with an empty `oldString`.
- Use Edit only when modifying an existing file and you have the exact old text to replace.
- Do not run the full validation suite from OpenCode repair. Do not run `tools/run_validation.py` from repair. The pipeline runs official validation after repair and remains the source of truth.
- Treat repair as one controlled attempt inside a pipeline repair loop: use `prototype/output/repair_context.json` and validation logs, make one coherent targeted change set, write `repair_report.json`, then hand control back to the pipeline. If more failures remain and repair attempts are available, the next repair will receive a refreshed `repair_context.json`.
- Use `prototype/output/validation_result.json`, `prototype/output/validation.stdout.log`, `prototype/output/validation.stderr.log`, and the already-collected failure snippets to diagnose the repair. If `validation_result.json` contains `stages` or `failed_stages`, review every failed stage before editing.
- Prioritize validation failures by dependency order. If `root_failed_stages` is present, repair those first. If a failed stage has `blocked_by_failed_stages` or appears under `downstream_failed_stages`, treat it as secondary context until the upstream stage is fixed. Do not change frontend/e2e code merely because browser tests fail while backend smoke/pytest or frontend build is failing, unless the browser failure is clearly independent (for example, a selector strict-mode error unrelated to backend data/API availability).
- If the failure matches a kit implementation pattern, use that pattern to repair the implementation/test shape instead of adding another one-off workaround.
- If a focused diagnostic is truly needed, run only a narrow command directly related to the changed file, such as one backend pytest file, a syntax check for Python files, or at most one focused Playwright invocation for the exact failing spec. Avoid full install/build/e2e cycles from inside repair.
- Do not repeatedly run expensive diagnostics such as `npm run test:e2e` or broad `pytest` loops inside repair. Use the already captured validation logs, make a targeted change, optionally run one narrow check, and let the pipeline's official post-repair validation decide the result. If the runner hands control back because the diagnostic budget was exceeded, that is not success by itself; it means the pipeline will validate the current changes and, if needed, run the next repair attempt with updated context.
- Do not repeatedly reset or rewrite planned mock storage data merely to make a browser run pass locally. Repair the service/test isolation or browser flow so validation is repeatable.
- Do not use `node --check` on `.jsx` files or Playwright spec files. JSX and Playwright ESM syntax are validated by `npm run build` and `npm run test:e2e`.

- `prototype/output/repair_report.json` is an output of this repair phase and normally does not exist at phase start. Do not read it as an input before writing it.
- Write prototype/output/repair_report.json.
- Update prototype/output/change_manifest.json if your repair changes implementation files.


Architecture contract requirement:
- Follow `prototype/input/architecture-contract.yaml` for artifact types, allowed roots, path placement, test capabilities, dependency policy, and UI anchor conventions.
- Do not invent file placement rules outside the contract.

Workspace path discipline:
- Treat the current working directory as the workspace root.
- Read and write `prototype/input/...` and `prototype/output/...` relative to the workspace root.
- Source files listed in `changed_files.json`, `ui_static_check_result.json`, and validation logs are workspace-root paths such as `frontend/src/...` or `backend/app/...`; do not prefix them with `prototype/output/`.
- Never use `/runs/<run-name>/prototype/...`; the valid path is `/runs/<run-name>/workspace/prototype/...` when an absolute path is unavoidable.
- Do not read from run-level `input/` or `output/` unless the prompt explicitly asks for a diagnostics-only fallback.


Validation repair note:
- `ui_static` is a non-file validation check. Do not create or modify test files for `ui_static`; repair missing or duplicate anchors in the allowed UI artifact.
- Anchor repairs are file-scoped: add a missing action anchor only to a file whose file-plan item directly lists that `action.*` scheme element and that contains the actual UI control for the action. Do not add unrelated action anchors to widgets or containers merely to satisfy a cross-file requirement context.
- If `ui_static` reports `duplicate_unique_ui_anchor`, keep the direct `screen.*` or `widget.*` anchor only on the owning root/outermost JSX element and remove the duplicate from nested headings, labels, wrappers, or controls.
- Browser/e2e behavior tests may be repaired only when they are present in `file_plan.json` with a behavior validation intent and an allowed frontend behavior test path.
- If Playwright cannot find `getByTestId('...')` while `ui_static` passed, first check whether Playwright is configured with `testIdAttribute: 'data-prototype-id'`. If it is not configured, either use explicit `[data-prototype-id="..."]` locators or repair the planned config file when it is writable.
- If Playwright cannot see the planned screen after navigation while `ui_static` passed, inspect `App.jsx` and `routeRegistry.js` before changing the test. For this kit, `App.jsx` renders `routes[0].component`; repair `routeRegistry.js` to use `component` instead of `element`, and do not click a navigation link unless the app actually renders that link.
- If Playwright reports a strict mode violation for `page.locator('text=...')`, repair the behavior test to scope assertions through the relevant screen/widget/action anchor and use accessible selectors such as `getByRole(..., { name, exact: true })`. Do not merely add `.first()` unless the requirement intentionally accepts any matching element.
- If Playwright reports strict mode or duplicate matches inside a repeated row/card because the test asserts a short, numeric, or repeated value with `getByText()` (for example stock quantity `10`, `0`, a price fragment, status, category, or code), repair the selector, not the product behavior. Locate the runtime-owned row/card first, then assert the intended field/cell with a stable display anchor or scoped `row.locator('td').nth(<known-column-index>)`. Do not use `.first()`/`.last()` just to silence duplicate matches.
- If Playwright e2e fails because a test reads `backend/app/storage/*.json` from the frontend working directory, repair the test to verify behavior through the UI or public API instead of reading private backend files.
- If validation after repair fails because a previous browser run mutated local JSON mock storage, repair the behavior tests so mutating flows create and operate on runtime-unique test-owned records instead of seed records or fixed test titles.
- If `ui_static` reports advisory browser/e2e hygiene warnings, use them as context only. Repair the browser/e2e test file when Playwright or validation output confirms the warning is connected to an actual failure.


Common fast repairs to prefer over broad diagnostic loops:

- If Playwright cannot find `control.open-create-<entity>`, inspect the UI before changing the test. When there is a separate open-create button, repair the UI to use `control.open-create-<entity>` and keep `action.create-<entity>` on the submit/save control inside `form.<entity>`.
- If a passed or failing search implementation only exposes one UI search field while the requirement names several searchable fields, repair the UI/search service and e2e so the user-visible search capability covers those named fields. Do not treat backend-only query support as sufficient browser behavior coverage.
- If search/filter e2e fails with count 0, count 1 vs expected 2, or missing rows immediately after changing or clearing a filter/search input, first repair the Playwright flow to wait for the expected runtime-owned row/card(s) to be visible after that transition. For clear/reset steps, ensure the UI clears all relevant search/filter controls and the test waits for each runtime-owned row it expects before count assertions. Do not change product loading/rendering behavior only to satisfy a premature count assertion unless the requirement explicitly defines that loading UX.
- If a Clear/Reset button leaves the list filtered or the test proves reset only with the same row that was already visible, inspect the product handler and e2e together. In React, do not call a loader that reads old search/filter state immediately after `setState('')`; pass explicit reset values to the loader. Update e2e to click the real Clear/Reset control from a non-empty state and prove reset with two runtime-owned rows/cards that differ on the active search/filter dimension.
- If multi-field search e2e still gets count 0 after a row wait was expected, inspect whether the UI search implementation actually searches the named field. Backend-only support is not sufficient when the requirement is user-visible search. Repair the UI/API call and e2e together so each searched value is a current visible value in a runtime-owned row/card.
- Mutable-state test isolation: ensure API requests in tests use the isolated dependency prepared by the test fixture; add or use a small allowed provider/factory/injection seam rather than patching unrelated helpers.
- Playwright async locator assertions: await locator async APIs before numeric assertions, for example `const count = await locator.count(); expect(count)...`.
- Post-edit assertions: if an edit changes any value later used to locate/search a row/card, switch later row lookup/search assertions to the current edited value or a stable id. This applies to phone/email/status/category/date as well as title/name. When repairing such a test, keep reused values in the parent test scope and avoid introducing `ReferenceError` by declaring a variable inside one `test.step(...)` and using it in another.
- Async UI transition races: after form submit, create/edit/delete, search/filter changes, or clearing inputs, wait for the expected visible domain outcome before count or absence assertions. Do not add `expect(form).not.toBeVisible()` as a generic submit wait unless form closing is explicit required behavior; a form may validly remain open.


Repair reminders for tests:
- Do not repair feature API failures by editing smoke tests. Use the feature test method and dependency seam selected by the catalog.
- For Playwright repeated item actions, use a row/card locator first, then click the action inside that row/card. Avoid chained `>> text=... >>` selector strings.
- If Playwright cannot fill a form field because the test uses `getByText('Label').locator('input')`, repair the UI/test to use `form.<entity>` and `field.<entity>-<field>` anchors rather than adding waits or changing label text.
- If one compact browser flow was expanded into many independent tests with shared mutable state, reduce it back to the requested user journey unless file_plan/validation_plan explicitly require those separate browser cases.
- Do not repair a failed browser test by adding unrequested behavior coverage such as delete/confirmation, empty-state, minimal-field, or multi-record edge cases.
- After async UI transitions, wait for a positive visible state before count or absence assertions. Prefer created/edited row visibility over optional UI cleanup state such as hiding a form.

- For enum/status/category fields in browser/e2e, assert the intended user-visible display value. Do not assume the raw API value such as `in_progress` is rendered if the UI formats it as a human label such as `In progress`; align UI rendering and Playwright assertions deliberately.

- Backend isolation failures: if tests still share records after dependency override, inspect whether the service preserves the injected resource identity. Do not let the service collapse an injected temp path, repository, adapter, client, or config to a basename, default resource, global singleton, or production mock. In the JSON-storage example this means using the full injected path for reads and writes.
