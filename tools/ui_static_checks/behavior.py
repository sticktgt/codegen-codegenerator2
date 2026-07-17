from __future__ import annotations

import re
from typing import Any

_BROAD_PAGE_TEXT_LOCATOR_RE = re.compile(r"\bpage\.locator\(\s*([`'\"])text=", re.MULTILINE)
_TABLE_CELL_INDEX_LOCATOR_RE = re.compile(
    r"\.locator\(\s*([`'\"])td\1\s*\)\s*\.nth\(",
    re.MULTILINE,
)


def behavior_test_warnings(path: str, text: str) -> list[dict[str, Any]]:
    """Return non-blocking browser-test hygiene hints.

    Browser behavior correctness is primarily validated by running Playwright.
    Static diagnostics here intentionally stay advisory so Python code does not
    replace the LLM's responsibility to write suitable tests.
    """
    warnings: list[dict[str, Any]] = []

    broad_matches = list(_BROAD_PAGE_TEXT_LOCATOR_RE.finditer(text))
    if broad_matches:
        warnings.append(
            {
                "code": "broad_page_text_locator",
                "path": path,
                "count": len(broad_matches),
                "message": (
                    "Browser/e2e test uses page.locator('text=...'), which can be broad in Playwright strict mode. "
                    "Prefer scoped locators when the generated UI naturally has duplicate visible text."
                ),
            }
        )

    table_index_matches = list(_TABLE_CELL_INDEX_LOCATOR_RE.finditer(text))
    if table_index_matches:
        warnings.append(
            {
                "code": "table_cell_index_locator",
                "path": path,
                "count": len(table_index_matches),
                "message": (
                    "Browser/e2e test uses locator('td').nth(...). Column-index assertions are fragile after "
                    "generated table columns are added, removed, or reordered. Prefer row-scoped field/display "
                    "anchors such as field.<entity>-<field>-display, or derive the index from the visible header "
                    "inside the test when a table contract intentionally fixes the order."
                ),
            }
        )

    return warnings
