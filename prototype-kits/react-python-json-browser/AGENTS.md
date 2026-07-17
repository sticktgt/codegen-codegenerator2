# Prototype Kit Instructions

You are implementing a small prototype inside a prepared workspace.

## Primary rule

Implement only the approved implementation slice described in:

```text
prototype/input/implementation_slice.json
```

Use these files as the source of truth:

```text
prototype/input/scheme_model.json
prototype/input/requirements.json
prototype/input/data_sources.json
prototype/input/mock_plan.json
prototype/input/implementation_slice.json
prototype/input/file_plan.json
prototype/input/validation_plan.json
prototype/input/generation-rules.yaml
```

## File discipline

- Use `file_plan.json` as the only allowed file plan.
- Create owned files when missing.
- Modify only allowed integration files.
- Do not change files outside `file_plan.json`; report any limitation in `prototype/output/implementation_report.json`.
- Do not change files under `prototype/input/`.
- Do not change the project structure.

## Scope discipline

- Do not implement requirements outside the implementation slice.
- Do not add authentication.
- Do not add external integrations.
- Do not add database migrations.
- Use local JSON/mock storage.

## Traceability

Create or update:

```text
prototype/output/implementation_report.json
```

The report must list changed files, related scheme elements, related requirements, and any deviations from the active file plan.

## Composable phase prompts

- `prompts/manifest.yaml` declares the ordered prompt modules for `plan`, `plan-review`, `implementation`, and `repair`.
- Shared modules live under `prototype-kits/_shared/prompts/` and are grouped into core, stack, storage, and testing responsibilities.
- The pipeline composes one run snapshot per phase before OpenCode starts. Do not choose prompt modules from scenario semantics in Python code.
- Storage-specific changes should normally replace only the storage prompt module; React/Python and testing modules remain reusable when their contracts do not change.
- Monolithic `prompts/*_prompt.md` files are not supported by this kit; update `prompts/manifest.yaml` and shared modules instead.

## Composable runtime context

- `runtime/manifest.yaml` declares shared agents, instructions, examples, and skills that the pipeline materializes into the run workspace.
- Shared runtime modules live under `prototype-kits/_shared/agents/`, `_shared/instructions/`, `_shared/examples/`, and `_shared/skills/`.
- The active phase prompt lists the canonical materialized modules under `instructions/core/`, `instructions/frontend/`, `instructions/backend/`, and `instructions/testing/`.
- Read the phase-required modules first, then load only patterns relevant to the approved file and validation plans.
- `instructions/core/architecture.md` contains invariant rules; `instructions/core/architecture-addons/stack/react-python-json-browser.md` gives the stack overview; layer-specific placement rules live under `instructions/core/architecture-addons/frontend/`, `backend/`, and `storage/`.
- The optional `prototype-crud-flow` skill is only a compact checklist. It does not replace canonical instructions, the approved file plan, or required phase reports.
