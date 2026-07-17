# Local JSON Storage Rules

- Use local JSON/mock data for the active kit.
- Keep injected storage resources intact. Do not collapse an injected path, handle, adapter, repository, or config to a basename, default resource, global singleton, or production mock.
- Tests that mutate storage must use test-owned temporary storage or restore tracked mock data exactly.
