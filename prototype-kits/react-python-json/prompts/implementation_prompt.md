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

Rules:
- Use prototype/input/file_plan.json as the only allowed file plan.
- Do not infer additional files from design_delta or naming symmetry. If a new scheme element is screen-internal, implement it only inside its owning artifact when that artifact is allowed by file_plan.json.
- Do not create, edit, rename, or delete files outside file_plan.json.
- Respect file policies in file_plan.json:
  - must_create: create the file if it does not exist.
  - may_modify / modify_allowed: modify only if needed.
  - no_change / may_read / read_only: read only; do not edit.
- Do not rewrite the whole application.
- Do not implement requirements outside the current scenario/run input slice.
- If `run_input.json` is present, use it only as requirement context; do not infer extra writable files from it beyond file_plan.json.
- Preserve existing accepted behavior by default. If the file plan marks an existing artifact as read-only/no_change, reuse it rather than repurposing it.
- For confirm/cancel flows, keep existing destructive actions/API wrappers stable unless file_plan.json explicitly allows and explains changing them.
- If the slice extends existing behavior, prefer wrappers, UI state, or new artifacts over changing the stable responsibility of an existing action/API/service.
- Do not add dependencies or edit package files unless explicitly allowed in file_plan.json.
- If a planned test or implementation appears to require a missing dependency, do not add it; report the limitation in implementation_report.json.
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
- If validation_plan.json proposes a test file that is not present in file_plan.json, do not create it; report the limitation.
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
- If the UI control, screen, or widget cannot reasonably have an anchor, document the deviation in `implementation_report.json`; do not silently omit it.

Workspace path discipline:
- Treat the current working directory as the workspace root.
- Read and write `prototype/input/...` and `prototype/output/...` relative to the workspace root.
- Never use `/runs/<run-name>/prototype/...`; the valid path is `/runs/<run-name>/workspace/prototype/...` when an absolute path is unavoidable.
- Do not read from run-level `input/` or `output/` unless the prompt explicitly asks for a diagnostics-only fallback.
