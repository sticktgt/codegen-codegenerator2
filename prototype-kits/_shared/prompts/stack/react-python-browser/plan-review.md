# React / Python browser stack review additions

Additional reads and rules:
- instructions/core/architecture-addons/react-python-json-browser.md
- Does the plan follow the layer rules in `instructions/core/architecture.md` and `instructions/core/architecture-addons/react-python-json-browser.md` without relying on Python to repair artifact types or create/modify decisions?
- Are existing skeleton/integration files planned as modify/read rather than create?
- Are any backend/frontend layers missing?
- For scheme actions without a dedicated file, including existing actions from `scheme_model.json`, does `implementation_mode: "screen_internal"` name an `owning_artifact` and is the owning artifact allowed by the file plan?
- For incremental slices, does each derived value or small extension have a precise owner? If the model can compute a derived response field, the service/API should not be forced to change unless it performs real filtering/mapping/persistence/endpoint work.
- Treat repurposing an existing API/action/service artifact as a blocker unless the requirement explicitly asks to replace the old behavior.
- For a confirmation flow around an existing destructive action, prefer preserving the existing destructive action and adding confirmation UI/state or a wrapper action.
- It is acceptable for a cancel/confirm or CRUD action to be screen-internal if it only manages local UI flow or invokes an existing API/action; in that case the design_delta should say so explicitly and the screen file must carry the relevant scheme element for UI anchor validation.
- If a child-widget action is listed as owned by the parent screen while the actual clickable control will live in the child widget, issue at least a warning and recommend moving ownership to the child widget. Treat it as a blocker when the file plan would force wrapper anchors or duplicate action anchors in the parent just to satisfy UI static checks.
- A parent screen embedding a child widget does not automatically own every action inside that widget. The owning artifact should be the file that contains the actual user control.
