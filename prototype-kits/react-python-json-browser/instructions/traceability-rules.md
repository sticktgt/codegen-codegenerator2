# Traceability Rules

- Each owned file should correspond to a scheme element.
- Each changed file must be reported in `prototype/output/implementation_report.json`.
- Include related requirement IDs and scheme element IDs in reports.
- Prefer stable anchors for important public points when it does not make code noisy, for example `data-prototype-id` in generated UI controls.
- Traceability is ultimately built from git diff, file plan, validation results, and agent reports.
- Do not rely on agent reports alone as the source of truth.
