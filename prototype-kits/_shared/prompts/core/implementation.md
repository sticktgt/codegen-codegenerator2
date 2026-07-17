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
- instructions/core/architecture.md
- instructions/core/coding.md
- instructions/core/file-boundaries.md
- instructions/core/traceability.md
- instructions/core/pipeline-output.md
- instructions/core/implementation-guidance.md
- relevant pattern files listed in instructions/core/implementation-guidance.md for artifact types present in file_plan.json

Canonical instruction paths:
- Runtime workspace copies live under `instructions/...` at the workspace root.
- Markdown instructions are available from the workspace-root `instructions/` tree.
- Use `prototype/input/...` only for JSON/YAML run inputs and machine-readable contracts.

Rules:
- Do not use `todowrite` or `todoread`. Use `implementation_report.json` and `change_manifest.json` as the structured progress and result outputs.

Pipeline phase output discipline:
- Use prototype/input/file_plan.json as the only allowed file plan.
- Before the first Write/Edit, derive the exact writable path set from file_plan.json and validation_plan.json. Keep this checklist in your working notes and only write paths from that set plus required prototype/output reports.
- Also derive the behavior operations asserted by validation_plan.json. If validation checks list/detail/create/update/search/filter/UI refresh behavior for a changed field, implement the planned files so those operations are consistently covered. Do not implement only the operation mentioned first when validation checks several operations.
- Do not infer additional files from design_delta or naming symmetry. If a new scheme element is screen-internal, implement it only inside its owning artifact when that artifact is allowed by file_plan.json.
- Do not create, edit, rename, or delete files outside file_plan.json.
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
- Do not rewrite the whole application.
- Do not implement requirements outside the current scenario/run input slice.
- If `run_input.json` is present, use it only as requirement context; do not infer extra writable files from it beyond file_plan.json.
- Preserve existing accepted behavior by default. If the file plan marks an existing artifact as read-only/no_change, reuse it rather than repurposing it.
- For confirm/cancel flows, keep existing destructive actions/API wrappers stable unless file_plan.json explicitly allows and explains changing them.
- If the slice extends existing behavior, prefer wrappers, UI state, or new artifacts over changing the stable responsibility of an existing action/API/service.
- New dependencies are allowed only when file_plan.json explicitly includes the relevant package/config files as writable and the plan explains why the dependency is needed. Do not invent unplanned dependency files.
- If a planned test or implementation would be better with a missing dependency but package/config files are not writable, use available kit dependencies when reasonable or report the limitation in implementation_report.json for replanning.
- Use the kit implementation patterns selected by instructions/core/implementation-guidance.md when they match the approved file plan. Patterns are implementation guidance only; they do not grant permission to create files outside file_plan.json.
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

Workspace path discipline:
- Treat the current working directory as the workspace root.
- Read and write `prototype/input/...` and `prototype/output/...` relative to the workspace root.
- Never use `/runs/<run-name>/prototype/...`; the valid path is `/runs/<run-name>/workspace/prototype/...` when an absolute path is unavoidable.
- Do not read from run-level `input/` or `output/` unless the prompt explicitly asks for a diagnostics-only fallback.
