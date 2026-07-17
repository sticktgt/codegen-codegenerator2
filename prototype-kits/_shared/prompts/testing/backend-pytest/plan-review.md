# Backend pytest validation review additions

Additional reads and rules:
- instructions/testing/backend-pytest-methods.md
- instructions/testing/backend-pytest.md
- If backend pytest is planned for mutable FastAPI state, does the file plan include the API/service seams needed for dependency overrides and isolated test storage?
- If validation checks list/get/create/update behavior, do backend service/model/API file-plan reasons cover those operations or a shared helper that covers them?
- Prefer warnings for minor missing edge coverage. Use blockers only when the backend validation plan cannot run or cannot control mutable state with the approved files.
