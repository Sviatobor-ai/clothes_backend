"""Basic sanitization and soft validation for generated prompts."""

from __future__ import annotations

import re
from typing import Tuple

FORBIDDEN_KEYWORDS = {
    "nude",
    "nudity",
    "explicit",
    "erotic",
    "fetish",
    "sexual",
    "porn",
    "pornographic",
    "lolita",
    "schoolgirl",
    "teen",
    "underage",
    "minor",
    "child",
}


def sanitize(text: str) -> str:
    """Return a single-line sanitized string without markdown fences."""

    cleaned = text.replace("```", "")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def validate_prompt(text: str) -> Tuple[bool, str]:
    """Sanitize and softly validate the generated prompt."""

    sanitized = sanitize(text)
    if not sanitized:
        return False, "empty_prompt"

    normalized = sanitized.lower()
    for forbidden in FORBIDDEN_KEYWORDS:
        if forbidden in normalized:
            return False, f"forbidden_keyword:{forbidden}"

    return True, ""
