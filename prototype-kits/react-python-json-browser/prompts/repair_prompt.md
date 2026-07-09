Repair validation failures or file-boundary failures for the current slice.

Read:
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
- Do not repair backend test isolation by rewriting implementation source files from inside a pytest fixture. Instead patch or inject the actual dependency used by the route, construct an isolated service instance, use dependency overrides, or make an allowed implementation repair that exposes a clean injection point.
- If test data accumulates across backend tests, ensure the fixture runs for every test and that each test request is served by the isolated service/storage for that test. Check for module-level service singletons and global TestClient/app objects that may have captured old dependencies.
- If validation failure appears to require a missing dependency, add it only when the package file is explicitly writable in file_plan.json; otherwise adjust unsupported generated tests to available dependencies or report the limitation.
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
- Use `prototype/output/validation_result.json`, `prototype/output/validation.stdout.log`, `prototype/output/validation.stderr.log`, and the already-collected failure snippets to diagnose the repair. If `validation_result.json` contains `stages` or `failed_stages`, review every failed stage before editing.
- Prioritize validation failures by dependency order. If `root_failed_stages` is present, repair those first. If a failed stage has `blocked_by_failed_stages` or appears under `downstream_failed_stages`, treat it as secondary context until the upstream stage is fixed. Do not change frontend/e2e code merely because browser tests fail while backend smoke/pytest or frontend build is failing, unless the browser failure is clearly independent (for example, a selector strict-mode error unrelated to backend data/API availability).
- If the failure matches a kit implementation pattern, use that pattern to repair the implementation/test shape instead of adding another one-off workaround.
- If a focused diagnostic is truly needed, run only a narrow command directly related to the changed file, such as one backend pytest file or a syntax check for Python files; avoid full install/build/e2e cycles from inside repair.
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
- Never use `/runs/<run-name>/prototype/...`; the valid path is `/runs/<run-name>/workspace/prototype/...` when an absolute path is unavoidable.
- Do not read from run-level `input/` or `output/` unless the prompt explicitly asks for a diagnostics-only fallback.


Validation repair note:
- `ui_static` is a non-file validation check. Do not create or modify test files for `ui_static`; repair missing or duplicate anchors in the allowed UI artifact.
- Anchor repairs are file-scoped: add a missing action anchor only to a file whose file-plan item directly lists that `action.*` scheme element and that contains the actual UI control for the action. Do not add unrelated action anchors to widgets or containers merely to satisfy a cross-file requirement context.
- If `ui_static` reports `duplicate_unique_ui_anchor`, keep the direct `screen.*` or `widget.*` anchor only on the owning root/outermost JSX element and remove the duplicate from nested headings, labels, wrappers, or controls.
- Browser/e2e behavior tests may be repaired only when they are present in `file_plan.json` with a behavior validation intent and an allowed frontend behavior test path.
- If Playwright cannot find `getByTestId('...')` while `ui_static` passed, first check whether Playwright is configured with `testIdAttribute: 'data-prototype-id'`. If it is not configured, either use explicit `[data-prototype-id="..."]` locators or repair the planned config file when it is writable.
- If Playwright reports a strict mode violation for `page.locator('text=...')`, repair the behavior test to scope assertions through the relevant screen/widget/action anchor and use accessible selectors such as `getByRole(..., { name, exact: true })`. Do not merely add `.first()` unless the requirement intentionally accepts any matching element.
- If Playwright e2e fails because a test reads `backend/app/storage/*.json` from the frontend working directory, repair the test to verify behavior through the UI or public API instead of reading private backend files.
- If validation after repair fails because a previous browser run mutated local JSON mock storage, repair the behavior tests so mutating flows create and operate on runtime-unique test-owned records instead of seed records or fixed test titles.
- If `ui_static` reports advisory browser/e2e hygiene warnings, use them as context only. Repair the browser/e2e test file when Playwright or validation output confirms the warning is connected to an actual failure.
