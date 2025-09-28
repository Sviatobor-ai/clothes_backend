"""Integration with the OpenAI Assistants API for prompt generation."""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Optional

from openai import OpenAI
from openai.types.beta.threads import Run

from app.config import settings
from app.logging_conf import get_log_context
from app.services import prompt_templates
from app.services.prompt_guard import sanitize, validate_prompt

LOGGER = logging.getLogger(__name__)
CLIENT = OpenAI(api_key=settings.openai_api_key)
MODEL = "gpt-4o-mini"
POLL_INTERVAL_SECONDS = 0.5
POLL_TIMEOUT_SECONDS = 90.0


def _sha1(text: str) -> str:
    """Return the first 12 hexadecimal characters of a SHA1 digest."""

    digest = hashlib.sha1(text.encode("utf-8"))
    return digest.hexdigest()[:12]


def _poll_run(thread_id: str, run_id: str) -> Run:
    """Poll the run until it reaches a terminal state."""

    deadline = time.monotonic() + POLL_TIMEOUT_SECONDS
    while True:
        run = CLIENT.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
        if run.status in {"completed", "failed", "cancelled", "expired"}:
            return run
        if time.monotonic() > deadline:
            raise RuntimeError("assistant_run_timeout")
        time.sleep(POLL_INTERVAL_SECONDS)


def _extract_latest_text(thread_id: str) -> str:
    """Fetch the latest assistant message text from the thread."""

    messages = CLIENT.beta.threads.messages.list(thread_id=thread_id, order="desc", limit=5)
    for message in messages.data:
        if message.role != "assistant":
            continue
        text_fragments: list[str] = []
        for content in message.content:
            if content.type == "text" and content.text:
                text_fragments.append(content.text.value)
        if text_fragments:
            return "\n".join(text_fragments)
    raise RuntimeError("assistant_no_text_response")


def _create_assistant() -> str:
    assistant = CLIENT.beta.assistants.create(
        model=MODEL,
        instructions=prompt_templates.ASSISTANT_SYSTEM,
        name="Leatherwear Prompt Assistant",
    )
    return assistant.id


def generate_prompt_text() -> str:
    """Generate a single sanitized prompt string via the Assistants API."""

    last_reason: Optional[str] = None
    logged_error = False
    try:
        for attempt in range(2):
            user_prompt = prompt_templates.build_randomized_user_prompt()
            assistant_id = _create_assistant()
            thread = CLIENT.beta.threads.create()
            CLIENT.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=user_prompt,
            )
            run = CLIENT.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=assistant_id,
            )
            run = _poll_run(thread.id, run.id)
            if run.status != "completed":
                error_message = getattr(run, "last_error", None)
                reason = error_message.get("message") if isinstance(error_message, dict) else run.status
                LOGGER.error(
                    "assistant prompt generation failed",
                    extra={"reason": reason, "attempt": attempt + 1},
                )
                logged_error = True
                raise RuntimeError(f"assistant_run_{run.status}")

            raw_text = _extract_latest_text(thread.id)
            sanitized = sanitize(raw_text)
            if not sanitized:
                LOGGER.error("assistant prompt generation failed", extra={"reason": "empty_output"})
                logged_error = True
                raise RuntimeError("assistant_empty_prompt")

            is_valid, note = validate_prompt(sanitized)
            if not is_valid:
                last_reason = note or "unsafe_prompt"
                LOGGER.warning(
                    "assistant prompt blocked",
                    extra={"reason": last_reason, "attempt": attempt + 1},
                )
                continue

            if note:
                LOGGER.warning("assistant prompt warning", extra={"warning": note})

            context = get_log_context()
            LOGGER.info(
                "assistant prompt generated",
                extra={
                    "len": len(sanitized),
                    "sha1": _sha1(sanitized),
                    "request_id": context.get("request_id"),
                },
            )
            return sanitized

        LOGGER.error(
            "assistant prompt generation failed",
            extra={"reason": last_reason or "unsafe_prompt"},
        )
        logged_error = True
        raise RuntimeError("prompt_guard_blocked")
    except Exception as exc:  # noqa: BLE001
        if not logged_error:
            LOGGER.error(
                "assistant prompt generation failed",
                extra={"reason": f"{exc.__class__.__name__}:{exc}"},
            )
        raise


"""Example usage (manual testing only):
>>> from app.services.assistant_service import generate_prompt_text
>>> prompt = generate_prompt_text()
>>> print(len(prompt), prompt[:140])
"""
