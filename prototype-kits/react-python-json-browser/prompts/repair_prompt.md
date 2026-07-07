Repair validation failures or file-boundary failures for the current slice.

Read:
- prototype/output/changed_files.json, if present
- prototype/output/validation_result.json, if present
- validation logs referenced by validation_result.json, if present
- prototype/input/file_plan.json
- prototype/input/requirements.json
- prototype/input/scheme_model.json
- prototype/input/run_input.json, if present
- prototype/input/implementation_slice.json

Rules:
- Fix only validation failures and file-boundary violations for the current scenario/run input slice.
- If `run_input.json` is present, use it only as requirement context; do not infer extra writable files from it beyond file_plan.json.
- Use prototype/input/file_plan.json as the only allowed file plan for implementation changes.
- Do not create new files outside file_plan.json.
- Do not add dependencies or edit package files unless explicitly allowed in file_plan.json.
- Respect validation intent in file_plan.json. If a test file has `validation_intent: "rerun_existing"` or `"rerun_behavior_test"`, or a read-only/no_change policy, do not edit it; fix implementation or report the validation limitation instead.
- Do not add browser/e2e dependencies or tasks during repair. If frontend behavior validation needs a missing runner, report the kit limitation unless file_plan.json explicitly allows dependency/task changes.
- If tests changed tracked mock storage or runtime fixtures, repair the tests to use isolated temporary data or exact restoration; do not treat fixture mutation as an implementation change.
- If validation failure appears to require a missing dependency, do not add it unless the package file is explicitly writable in file_plan.json; instead remove/adjust unsupported generated tests or report the limitation.
- Do not change scope or implement new requirements.
- Preserve existing behavior.
- If changed_files.json lists unexpected files created by this run, remove them.
- If changed_files.json lists unexpected modifications to files outside file_plan.json, revert those files to their previous/baseline content.
- If changed_files.json lists policy violations for no_change/read_only files, revert those changes.
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
- `ui_static` is a non-file validation check. Do not create or modify test files for `ui_static`; repair missing anchors in the allowed UI artifact.
- Browser/e2e behavior tests may be repaired only when they are present in `file_plan.json` with a behavior validation intent and an allowed frontend behavior test path.
