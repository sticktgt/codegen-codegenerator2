# Local JSON storage review additions

Additional reads and rules:
- instructions/backend/storage-json.md
- instructions/backend/patterns/fastapi-json-crud.md

- Is `backend/app/storage/__init__.py`, if used, classified as `backend_storage` rather than `backend_integration`?
- Review service dependencies for linked resources. If a primary resource service is expected to return a related resource display field, but the plan does not provide a way to inject or share the related service/storage in API tests, warn strongly or block when backend validation depends on temp storage isolation.
- For multi-service FastAPI plans, check whether the plan explicitly preserves the primary provider as the owner of primary storage. Warn strongly if the plan says the endpoint will create a new primary service in the route handler to attach a related service; recommend composing the related service in the primary provider instead.
