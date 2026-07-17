# Backend pytest planning additions

Additional reads and rules:
- instructions/testing/backend-pytest-methods.md
- instructions/testing/backend-pytest.md
- Use backend pytest for API/service contracts, edge cases, request validation, persistence, and related-resource response/filter behavior.
- For generated FastAPI APIs that use mutable state, plan `backend.pytest.api.mutable-state` and include the provider/dependency seam in the implementation file plan when needed.
- Do not place feature API behavior in `backend/tests/test_smoke.py`; smoke is read-only/rerun coverage unless the requirement explicitly changes bootstrap behavior.
