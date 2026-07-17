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
- instructions/core/architecture.md, if needed
- instructions/core/repair.md, if needed
- instructions/core/file-boundaries.md
- instructions/core/pipeline-output.md
- instructions/core/implementation-guidance.md, if the failure is a recurring implementation/testability mismatch
- relevant pattern files listed in instructions/core/implementation-guidance.md for the failed artifact types, if applicable

Canonical instruction paths:
- Runtime workspace copies live under `instructions/...` at the workspace root.
- Markdown instructions are available from the workspace-root `instructions/` tree.
- Use `prototype/input/...` only for JSON/YAML run inputs and machine-readable contracts.

Rules:
- Do not use `todowrite` or `todoread`. Use `repair_report.json` and, when implementation files change, `change_manifest.json` as the structured repair outputs.

Pipeline phase output discipline:
- Fix only validation failures and file-boundary violations for the current scenario/run input slice.
- If `run_input.json` is present, use it only as requirement context; do not infer extra writable files from it beyond file_plan.json.
- Use prototype/input/file_plan.json as the only allowed file plan for implementation changes.
- Do not create new files outside file_plan.json.
- Add or change dependencies only when file_plan.json explicitly marks the relevant package/config files as writable. Otherwise repair with available kit dependencies or report the limitation.
- Do not change scope or implement new requirements.
- Preserve existing behavior.
- If changed_files.json lists unexpected files created by this run, remove them.
- If changed_files.json lists unexpected modifications to files outside file_plan.json, revert those files to their previous/baseline content.
- If changed_files.json reports `missing_required_changes` for a `must_modify` file, first check whether the requirement truly needs a semantic change in that file. Prefer a real minimal behavior-preserving semantic fix when the file really should change. If the implementation is already correct because another planned file owns the behavior, record the over-strict file-plan policy in `repair_report.json`; do not broaden application behavior just to touch the file. For prototype delivery, a harmless metadata/comment/docstring touch is an acceptable last-resort workaround only when boundary policy requires a changed file to produce a passing artifact; clearly label it as a file-plan workaround, not as functional implementation.
- If changed_files.json lists policy violations for no_change/read_only files, revert those changes.

File operation discipline:
- Use Write for intentional full-file replacement of empty or whitespace-only files; never call Edit with an empty `oldString`.
- Use Edit only when modifying an existing file and you have the exact old text to replace.
- Treat repair as one controlled attempt inside a pipeline repair loop: use `prototype/output/repair_context.json` and validation logs, make one coherent targeted change set, write `repair_report.json`, then hand control back to the pipeline. If more failures remain and repair attempts are available, the next repair will receive a refreshed `repair_context.json`.
- If the failure matches a kit implementation pattern, use that pattern to repair the implementation/test shape instead of adding another one-off workaround.

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
