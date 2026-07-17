Plan the current implementation slice. Do not implement code.

Read:
- prototype/input/requirements.json
- prototype/input/scheme_model.json
- prototype/input/run_input.json, if present
- prototype/input/implementation_slice.json
- prototype/input/kit.yaml
- prototype/input/generation-rules.yaml
- prototype/input/architecture-contract.yaml
- instructions/core/architecture.md
- instructions/core/planning.md
- prototype/input/baseline_context/*.json, if present (use this workspace-relative path exactly; do not prefix it with the run directory path)
- the current workspace source files as needed

Canonical instruction paths:
- Runtime workspace copies live under `instructions/...` at the workspace root.
- Markdown instructions are available from the workspace-root `instructions/` tree.
- Use `prototype/input/...` only for JSON/YAML run inputs and machine-readable contracts.

Rules:
- Do not use `todowrite` or `todoread`. Use `plan_proposal.json` and `validation_plan_proposal.json` as the structured phase output.
- Do not edit production source files.
- Do not create implementation files.
- Do not change package files or dependencies during planning; only propose them in the file plan when justified and allowed.
- Do not propose dependency/package-file changes by default. If a new dependency is genuinely useful for implementation or validation, include the relevant package/config file in the file plan only when the architecture contract allows it, and record a short rationale. Otherwise record the limitation or use existing kit dependencies.
- Use project structure and kit rules to propose where changes should go.
- The model owns architectural planning decisions. Python validation may reject unsafe or malformed plans, but it must not rewrite artifact types, file placement, or create/modify decisions to repair architectural meaning. Produce a plan that is already consistent with the architecture rules.
- Use `policy: "must_modify"` only when the requirement cannot be implemented without a semantic change in that exact file. If a file is only a possible implementation location, a related layer, or needed for inspection/regression context, use `may_modify` or `read_only` instead. Do not mark a file `must_modify` merely to show traceability.
- A file-plan `reason` for `must_modify` must name the concrete semantic change expected in that file. Reasons like "verify", "preserve", "include if needed", or "related to requirement" are not sufficient for `must_modify`; use `read_only`/`may_modify` for those cases.
- Before writing final JSON, cross-check `validation_plan_proposal.json` against `file_plan_draft`. If validation asserts list, detail, create, update, delete, search, filter, or UI refresh behavior, the owning file-plan reasons must cover those operations or explain the shared helper/model/mapper that covers them. Improve the plan first; do not rely on review or repair to discover missing operations.
- For derived or related response/display fields returned through the same resource model, plan consistent population for every endpoint/service method used by the validation flow. Do not plan only list enrichment when validation also checks get/detail, create/update response, or post-edit refresh behavior.

- New file names and new scheme element ids must be proposed by you from the requirement intent and current project conventions, not copied from hardcoded assumptions.
- Follow the `planner_output` section of `architecture-contract.yaml` for canonical design_delta output. Do not use deprecated alternatives such as `scheme_delta`.
- Treat `prototype/input/run_input.json`, when present, as the canonical scenario input from the requirements stage. Treat `implementation_slice.json` as a compatibility view generated from it for the current pipeline.
- Treat `prototype/input/scheme_model.json` as scheme context from requirements/design. A scheme element being present does not prove that the implementation artifact exists in the workspace. The scheme may also be partial in incremental runs.
- Treat `prototype/input/baseline_context/*.json`, when present, as read-only semantic context from the previous successful run: traceability, accepted file plans, change manifests, and validation summaries. Use it together with workspace inspection; do not treat it as a file-change instruction.
- The scenario/run input describes user intent, acceptance criteria, optional selected existing scheme elements, and constraints. It does not prescribe file policies, new element ids, or implementation artifact names.
- If `run_input.json` or `implementation_slice.json` includes `selected_existing_elements`, use them as user-selected context. If it is empty or absent, resolve affected existing elements yourself from requirements, scheme_model, baseline_context, previous traceability, existing anchors/routes/API/model fields, and code.
- Strictly separate existing, discovered, and new scheme elements:
  - `design_delta.resolved_existing_elements` contains elements known from `scheme_model.json`, explicitly listed in `implementation_slice.selected_existing_elements`, discovered from `baseline_context`, previous traceability, or discovered in the current workspace code. Being resolved existing does not mean the element was listed in the current scheme_model.
  - `design_delta.proposed_new_elements` contains only element ids introduced for the current slice and not known from scheme_model, selected_existing_elements, baseline_context, or workspace discovery. Do not put discovered baseline/code elements into proposed_new_elements merely because the current scheme_model omits them.
  - No element id may appear in both lists.
  - Use `source: "selected_by_user"` only for ids explicitly listed in `implementation_slice.selected_existing_elements`.
  - Use `source: "scheme_model"` for ids present in scheme_model.
  - Use `source: "baseline_discovered"`, `"previous_traceability"`, or `"workspace_discovered"` for ids absent from scheme_model but supported by baseline artifacts or current code evidence.
  - Use `source: "resolved_by_planner"` only when the existing-element classification follows from multiple inputs and you explain the evidence in `reason`.
  - If a resolved existing element is absent from the current scheme_model, mention this as a schema gap/update candidate in `assumptions` or `design_delta.schema_gaps` when useful; do not classify it as a new implementation element.
- If the slice extends existing behavior, preserve already accepted behavior by default. Prefer adding a wrapper, UI state, or new artifact over repurposing an existing artifact with a stable responsibility.
- If a scheme action is implemented inside a screen rather than a dedicated action file, make the relationship explicit in `design_delta`: for a new action use `proposed_new_elements`; for an existing action from `scheme_model.json` keep it in `resolved_existing_elements` but include `implementation_mode: "screen_internal"` and `owning_artifact`. Also include that action id in the owning screen file-plan item `scheme_elements` so UI anchor checks can validate it.
- Do not repurpose an existing action/API/service artifact unless the requirement explicitly asks to replace the old behavior. If you must modify an existing artifact, explain why reuse/wrapping is insufficient in `design_delta.preservation_decisions`.
- If the requirement is ambiguous, make a conservative planner decision that preserves existing behavior. Do not ask the analyst implementation-design questions about internal file responsibilities.

Write exactly these JSON reports:
- prototype/output/plan_proposal.json
- prototype/output/validation_plan_proposal.json

plan_proposal.json shape:
{
  "slice_id": "...",
  "requirement_ids": [],
  "design_delta": {
    "change_type": "create_new|extend_existing_behavior|replace_existing_behavior|refactor_only",
    "resolved_existing_elements": [
      {
        "id": "existing scheme element id",
        "type": "screen|action|api|service|data|component|other",
        "source": "selected_by_user|scheme_model|baseline_discovered|previous_traceability|workspace_discovered|resolved_by_planner",
        "reason": "why this existing/discovered element is relevant; include evidence when it is absent from the current scheme_model"
      }
    ],
    "proposed_new_elements": [
      {
        "id": "new scheme element id proposed by the planner",
        "type": "screen|action|api|service|data|component|other",
        "requirement_id": "REQ-...",
        "implementation_mode": "separate_artifact|screen_internal|existing_artifact_extension",
        "artifact": "relative/path for separate_artifact or null",
        "owning_artifact": "relative/path for screen_internal or existing_artifact_extension, otherwise null",
        "reason": "why this new element is needed"
      }
    ],
    "schema_gaps": [
      {
        "id": "existing element id missing from current scheme_model, if any",
        "source": "baseline_discovered|previous_traceability|workspace_discovered",
        "suggested_schema_update": "short description or null"
      }
    ],
    "preservation_decisions": [
      {
        "existing_element_id": "existing scheme element id",
        "artifact": "relative/path or null",
        "decision": "reuse|wrap|modify_without_repurpose|replace",
        "preserved_behavior": "what existing accepted behavior remains valid",
        "reason": "why this decision preserves or intentionally replaces existing behavior"
      }
    ]
  },
  "file_plan_draft": {
    "create": [
      {
        "path": "relative/path",
        "policy": "must_create",
        "requirement_id": "REQ-...",
        "scheme_element_id": "primary scheme element id",
        "scheme_elements": ["all scheme element ids implemented or anchored by this file"],
        "artifact_type": "...",
        "reason": "why this file is needed"
      }
    ],
    "modify": [],
    "read": []
  },
  "assumptions": [],
  "questions": []
}

validation_plan_proposal.json shape:
{
  "slice_id": "...",
  "checks": [
    {
      "id": "VAL-...",
      "type": "smoke|unit|api|service|build|static|ui_static|ui_behavior|browser_e2e|e2e",
      "requirement_id": "REQ-...",
      "scheme_element_id": "...",
      "description": "what this check proves; mention secondary catalog methods when useful",
      "test_method_id": "method id from the active test-method catalog",
      "validation_intent": "rerun_existing|extend_existing_test|create_new_test|rerun_behavior_test|extend_behavior_test|create_behavior_test; omit for non-file checks such as ui_static",
      "proposed_file": "relative/test/path or null"
    }
  ],
  "assumptions": []
}

Architecture contract requirement:
- Follow `prototype/input/architecture-contract.yaml` for artifact types, allowed roots, path placement, test capabilities, dependency policy, and UI anchor conventions.
- Do not invent file placement rules outside the contract.
- When a slice adds, removes, or exposes a response field, derived display field, filter field, or query-supported field that requires a response/model/DTO/schema change, include the owning model/DTO/schema file in the file plan. Do not rely on API/service/test changes alone if the response model must serialize the new field. If the model is intentionally unchanged because the value is mapped elsewhere, explain that in the plan.
- When a validation plan checks the same returned resource after several operations, such as list + detail + update, the implementation plan must name the shared response/enrichment path or list every operation-specific method that must change. A plan that names only one operation while validation checks several is incomplete.

Workspace path discipline:
- Treat the current working directory as the workspace root.
- Read and write `prototype/input/...` and `prototype/output/...` relative to the workspace root.
- Never use `/runs/<run-name>/prototype/...`; the valid path is `/runs/<run-name>/workspace/prototype/...` when an absolute path is unavoidable.
- Do not read from run-level `input/` or `output/` unless the prompt explicitly asks for a diagnostics-only fallback.

Planner-output discipline:
- `design_delta` is the only canonical design-delta section. Do not write `scheme_delta`.
- Every scheme element referenced by `file_plan_draft` or `validation_plan_proposal` must be either present in `scheme_model.json`, listed in `design_delta.resolved_existing_elements`, or listed in `design_delta.proposed_new_elements`.
- New scheme element ids must not appear in `resolved_existing_elements`, even if they are mentioned by validation checks or anchored inside an existing screen.
- Existing/discovered element ids already present in scheme_model, baseline_context, previous traceability, or workspace code should not appear in `proposed_new_elements`; classify them as `resolved_existing_elements` and record a schema gap if the current scheme_model is incomplete.
- A screen-internal action may have no dedicated file, but it still needs a design_delta entry with `implementation_mode: "screen_internal"` and `owning_artifact` pointing to the owning file path or owning screen element id. This applies to existing scheme actions as well as new proposed actions.
- If a screen file implements screen-internal actions, include those action ids in the screen file's `scheme_elements` and include the related requirement ids on the screen file when you can.
- Do not include files in the file plan merely to satisfy naming symmetry. File creation must follow the actual architecture decision.
- For confirmation flows, prefer a working minimal plan: preserve the existing destructive action and implement Confirm/Cancel as screen-internal if separate files are not needed.

- Requirement coverage rules:
  - Every requirement id in `implementation_slice.requirements` must appear in at least one planned implementation file and at least one validation check.
  - Coverage may be direct (`requirement_id`/`requirements`) or through a referenced scheme element whose scheme-model requirements include that id.
  - For screen-internal actions, the owning screen file is the implementation file for that action requirement; make that relationship explicit through `scheme_elements` and/or `design_delta.owning_artifact`.
  - Do not cover primary requirements only implicitly through a broad check under a different requirement id.
Multi-resource incremental planning:
- When a slice adds a second resource to an existing screen, separate ownership clearly: the parent screen may embed a new widget, but the widget file owns its own internal actions and anchors.
- If a new action is implemented by a child widget, set `implementation_mode: "screen_internal"` or the nearest supported internal mode with `owning_artifact` pointing to the child widget file that contains the real clickable control. Do not attach the child action to the parent screen file merely because the parent renders the widget.
- The parent screen file should list the child widget element as integration context, not duplicate the child widget's action id in its own `scheme_elements` unless the parent screen contains the actual clickable control.
- For multi-resource joins or display fields, plan the dependency seam explicitly. If one resource service resolves a related resource display value through another service/repository, plan constructor injection or an API-layer dependency provider so tests and runtime can share the same isolated storage/service instances. Do not plan a service that silently instantiates a production/default related service when validation needs temp storage isolation.
- For multi-resource joins or display fields returned from existing CRUD endpoints, plan the response enrichment as a reusable path when possible. If the resource can be returned by list, detail, create, or update endpoints, do not describe the service change as list-only unless validation is intentionally list-only.
- For existing UI flows, prefer extending the existing spec/test only where it is necessary to prove preservation or the new relationship. A separate compact spec is acceptable for a distinct new resource flow, but do not split one user journey into many specs.
