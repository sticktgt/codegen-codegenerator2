# Backend pytest repair additions

Additional reads and rules:
- If the failure is in `backend/tests/*.py`, read `instructions/testing/backend-pytest-methods.md` and `instructions/testing/backend-pytest.md` before editing unless the repair is limited to a purely mechanical one-line syntax fix already obvious from the traceback.
- For `NameError` or `ImportError` in backend pytest, scan the entire modified test file for the same missing-symbol class of issue before editing. Add module-level imports for all direct model/service/provider/helper symbols used by fixtures or test functions.
- After fixing a backend pytest import/symbol failure, re-read the full modified test file and check all fixtures and test bodies again before writing `repair_report.json`; do not stop after the first traceback line if the same symbol class may appear later in the file.
- Mutable-state test isolation: ensure API requests in tests use the isolated dependency prepared by the test fixture; add or use a small allowed provider/factory/injection seam rather than patching unrelated helpers.
- If one endpoint returns an enriched/derived field but another endpoint returning the same response model does not, repair the shared enrichment/serialization path where possible instead of fixing only the first failing operation.
- Do not repair feature API failures by editing smoke tests. Use the feature test method and dependency seam selected by the catalog.
