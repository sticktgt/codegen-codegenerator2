# Pattern: related response enrichment

Use this pattern whenever a primary resource response includes a field derived from a related resource or external lookup.

## Ownership

If a display field needs external data, populate it in the service/API mapping. Do not make it a Pydantic `computed_field` unless it can be computed only from fields already present on that same model.

When an API endpoint returns or filters a primary resource using data from a related resource, keep the primary service/provider as the owner of primary storage and compose the related service through dependency injection.


## Filtering and ordering on enriched fields

When a request filter, search predicate, sort key, or validation assertion depends on a related/derived field that is not stored on the primary raw record, populate that field before applying the predicate. Do not filter raw stored records by a response-only field and then enrich the survivors; that will drop valid records whose derived value exists only after composition.

Use a clear sequence in the service/API layer:

1. load the primary records through the primary storage/service owner;
2. compose or enrich the related/derived response fields through the injected related service or mapper;
3. apply filters/search/sort that depend on those enriched fields;
4. return the same enriched response shape that the UI and tests validate.

Filters over stored primary fields may still run before enrichment. Filters over related/derived response fields must run after enrichment, or use an explicit backend query/join mechanism that is equivalent for the selected storage technology.

## Coverage across operations

When a related or derived field is part of the public response model, keep enrichment consistent across every endpoint or service method that returns that model in the validated flow. A typical CRUD resource may return the model from list, detail, create, and update operations. Prefer a single helper such as `_enrich_<entity>_response(...)` or `_with_related_display_fields(...)` used by all relevant methods. If you choose operation-specific logic, update every relevant operation explicitly.

Do not fix only the list response when tests or UI refresh logic also read detail or update responses. Do not make tests require detail/update enrichment while implementation only enriches list. If the approved file plan is too narrow to update the needed owner, record the mismatch in `implementation_report.json` rather than silently editing unplanned files.

If an endpoint response must expose a new field, relationship id, or related display value through a Pydantic model/DTO/schema, the owning model/DTO/schema file is part of the implementation contract and should be in the file plan. Do not sneak response model changes into an unplanned file just because API/service/tests need the field.
