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
- instructions/testing/backend-pytest.md, if creating or updating backend pytest tests
- instructions/testing/browser-e2e.md, if creating or updating browser/e2e tests

Canonical instruction paths:
- Runtime workspace copies live under `instructions/...` at the workspace root.
- Markdown instructions are available from the workspace-root `instructions/` tree.
- Use `prototype/input/...` only for JSON/YAML run inputs and machine-readable contracts.

Rules:

Pipeline phase output discipline:
- Use prototype/input/file_plan.json as the only allowed file plan.
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
- Use backend imports rooted at app.*, not backend.app.*.
- If a validation test file is listed in file_plan.json, follow its policy and `validation_intent`:
  - `validation_intent: "rerun_existing"` with `read_only`/`read`: do not edit the test file; it is an existing regression check to be rerun by validation.
  - `validation_intent: "extend_existing_test"`: update the existing test file only for the missing acceptance-criteria coverage.
  - `validation_intent: "create_new_test"`: create the planned test file only if file_plan.json allows it.
  - `validation_intent: "rerun_behavior_test"` with read-only/read: do not edit the browser/e2e test file; it is existing coverage.
  - `validation_intent: "extend_behavior_test"`: update the planned browser/e2e test only if file_plan.json allows it.
  - `validation_intent: "create_behavior_test"`: create the planned browser/e2e test only if file_plan.json allows it and the kit capability is enabled.
- For non-file checks such as `ui_static`, do not create any test file; just implement the required UI anchors in the allowed UI artifact.
- Otherwise do not create tests.
- Generated or modified tests must use isolated temporary data/fixtures. Do not leave tracked mock storage files such as backend/app/storage/*.json changed after tests run.
- Backend tests must not edit implementation source files on disk as a fixture strategy. Do not rewrite service modules from tests to change a storage path. Prefer constructing/injecting the service with a temporary path, monkeypatching the actual route-module dependency before requests, dependency overrides, or an explicit app/service factory when the generated implementation supports it.
- If a backend route keeps a module-level service instance, tests that replace that service must patch the route module object that the endpoint actually uses; patching a helper function after the singleton has been created is not enough.
- Backend pytest tests should use the simplest style that proves the requirement. Synchronous FastAPI `TestClient` is usually enough for ordinary API behavior, but async pytest plugins or other test dependencies are allowed when already available or when file_plan.json explicitly allows the package-file change.
- For JSON-backed services, prefer an implementation shape that is testable without modifying source files at test time: for example a service constructor parameter, dependency function, or route-level service object that tests can replace with an isolated instance.
- Browser/e2e tests for local JSON-backed prototypes must follow `instructions/testing/browser-e2e.md`: use repeatable test-owned data for mutating flows, avoid cross-test state dependencies, use prototype anchors through the configured `data-prototype-id` test id attribute, avoid broad locators when duplicate visible text is likely, and do not inspect backend storage files directly from Playwright.
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
