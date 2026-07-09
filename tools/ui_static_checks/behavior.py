from __future__ import annotations

import re
from typing import Any

_BROAD_PAGE_TEXT_LOCATOR_RE = re.compile(r"\bpage\.locator\(\s*([`'\"])text=", re.MULTILINE)


def behavior_test_warnings(path: str, text: str) -> list[dict[str, Any]]:
    """Return non-blocking browser-test hygiene hints.

    Browser behavior correctness is primarily validated by running Playwright.
    Static diagnostics here intentionally stay advisory so Python code does not
    replace the LLM's responsibility to write suitable tests.
    """
    broad_matches = list(_BROAD_PAGE_TEXT_LOCATOR_RE.finditer(text))
    if not broad_matches:
        return []
    return [
        {
            "code": "broad_page_text_locator",
            "path": path,
            "count": len(broad_matches),
            "message": (
                "Browser/e2e test uses page.locator('text=...'), which can be broad in Playwright strict mode. "
                "Prefer scoped locators when the generated UI naturally has duplicate visible text."
            ),
        }
    ]
