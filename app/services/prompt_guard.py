"""Basic sanitization and soft validation for generated prompts."""

from __future__ import annotations

import re
from typing import Tuple

FORBIDDEN_KEYWORDS = {
    "nude",
    "nudity",
    "lingerie",
    "bikini",
    "underwear",
    "see-through",
    "explicit",
    "erotic",
    "fetish",
    "sexual",
    "lolita",
    "schoolgirl",
    "teen",
    "underage",
    "minor",
}

_SHORT_HINT_THRESHOLD = 60
_LONG_HINT_THRESHOLD = 1200


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

    warning: str = ""
    length = len(sanitized)
    if length < _SHORT_HINT_THRESHOLD:
        warning = "prompt_short"
    elif length > _LONG_HINT_THRESHOLD:
        warning = "prompt_long"

    return True, warning
