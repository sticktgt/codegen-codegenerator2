# Core Architecture Rules

These rules are stack-independent and apply to every prototype kit. Stack and kit-specific placement rules are defined in an architecture add-on selected by the active kit.

The architecture rules are the primary source of truth for planning and implementation. Python pipeline code may check machine-readable safety boundaries, but it must not reinterpret architectural meaning, invent artifact names, or repair a planner's semantic decisions.

## Three different states

Keep these concepts separate:

1. **Requirement intent**
   - Comes from `prototype/input/run_input.json` and `requirements.json`.
   - Describes what the user wants and acceptance criteria.
   - Does not prescribe file names, file policies, or implementation details.

2. **Scheme context**
   - Comes from `prototype/input/scheme_model.json`.
   - Contains logical elements such as screens, widgets, actions, APIs, services, data, and mocks.
   - A scheme element being present does not prove that its implementation file already exists.

3. **Implementation state**
   - Comes from the actual workspace file tree.
   - Determines whether a planned artifact should be `create`, `modify`, or `read`.

## Planner ownership

The planner must produce a plan that is already consistent with the active architecture contract and selected architecture add-on:

- use the architecture contract for artifact types and allowed paths;
- inspect the workspace file tree before deciding `create` vs `modify`;
- create new owned artifacts only when a new artifact is needed;
- modify existing skeleton/integration files only for wiring;
- do not rely on Python validation to fix artifact types or operations.

## Validation authority

Static Python checks may verify format, path safety, allowed roots, forbidden files, declared UI invariants, and test execution results. They do not own architectural design. If a plan is semantically wrong, the model must correct the plan by following the core rules and active architecture add-on.
