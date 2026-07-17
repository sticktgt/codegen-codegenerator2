# UI static method catalog

## web.ui.static-anchors

Use for non-executable UI anchor checks.

Expected shape:
- `proposed_file` is `null` and there is no `validation_intent`.
- The implementation file must contain the exact `data-prototype-id` anchors for the relevant `screen.*`, `widget.*`, and directly rendered `action.*` scheme elements.
- This method does not create a test file and does not prove behavior.
