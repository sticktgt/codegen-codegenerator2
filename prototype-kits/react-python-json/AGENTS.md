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
