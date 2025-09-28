"""Basic sanitization and validation for generated prompts."""

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
    "transparent",
    "sheer",
    "explicit",
    "erotic",
    "fetish",
    "latex catsuit",
    "latex bodysuit",
    "lolita",
    "schoolgirl",
    "teen",
    "underage",
    "minor",
    "gucci",
    "prada",
    "chanel",
    "versace",
    "balenciaga",
    "dior",
    "fendi",
    "ysl",
    "saint laurent",
    "louis vuitton",
    "lv",
    "hermes",
    "burberry",
    "celine",
    "armani",
    "valentino",
    "givenchy",
    "coach",
    "bottega",
    "miu miu",
    "dolce",
    "gabbana",
}

REQUIRED_KEYWORDS = {"leather", "vertical"}

MIN_LENGTH = 200
MAX_LENGTH = 900


def sanitize(text: str) -> str:
    """Return a single-line sanitized string without markdown fences."""

    cleaned = text.replace("```", "")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def validate_prompt(text: str) -> Tuple[bool, str]:
    """Validate prompt length and keyword presence."""

    sanitized = sanitize(text)
    if not sanitized:
        return False, "empty_prompt"

    normalized = sanitized.lower()
    for forbidden in FORBIDDEN_KEYWORDS:
        if forbidden in normalized:
            return False, f"forbidden_keyword:{forbidden}"

    for required in REQUIRED_KEYWORDS:
        if required not in normalized:
            return False, f"missing_required:{required}"

    if len(sanitized) < MIN_LENGTH:
        return False, "prompt_too_short"
    if len(sanitized) > MAX_LENGTH:
        return False, "prompt_too_long"

    return True, ""
