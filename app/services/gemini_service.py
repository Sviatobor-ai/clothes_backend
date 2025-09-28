"""Gemini image generation utilities with dual SDK compatibility paths."""

from __future__ import annotations

import base64
import binascii
import hashlib
import logging
from typing import Any, Callable

import google.generativeai as genai

from app.config import settings

# Configure the SDK immediately; this does not trigger outbound requests.
genai.configure(api_key=settings.google_api_key)

MODEL_NAME = "models/gemini-2.5-flash-image-preview"

LOGGER = logging.getLogger(__name__)

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def short_sha1(text: str) -> str:
    """Return the first 12 hexadecimal characters of a SHA1 digest."""

    digest = hashlib.sha1(text.encode("utf-8"))
    return digest.hexdigest()[:12]


def _is_transient_error(exc: Exception) -> bool:
    """Return True when the exception looks transient (network or 5xx)."""

    if isinstance(exc, (ConnectionError, TimeoutError)):
        return True

    status_code = getattr(exc, "status_code", None)
    if isinstance(status_code, int) and 500 <= status_code < 600:
        return True

    code = getattr(exc, "code", None)
    if isinstance(code, int) and 500 <= code < 600:
        return True

    response = getattr(exc, "response", None)
    response_status = getattr(response, "status_code", None)
    if isinstance(response_status, int) and 500 <= response_status < 600:
        return True

    message = str(exc).lower()
    transient_tokens = (" 500", " 502", " 503", " 504", "5xx", "temporarily unavailable")
    return any(token in message for token in transient_tokens)


def _run_with_retry(func: Callable[[], Any]) -> Any:
    """Execute ``func`` and retry once if a transient error is raised."""

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            return func()
        except Exception as exc:  # noqa: BLE001 - intentional broad catch for retry logic
            if attempt == 0 and _is_transient_error(exc):
                last_error = exc
                continue
            raise
    if last_error:
        raise last_error
    raise RuntimeError("unreachable")


def _decode_base64(data: str | bytes | bytearray) -> bytes | None:
    """Decode base64 input into bytes, returning ``None`` on failure."""

    if isinstance(data, str):
        try:
            return base64.b64decode(data, validate=True)
        except binascii.Error:
            return None
    if isinstance(data, (bytes, bytearray)):
        try:
            return base64.b64decode(data, validate=True)
        except binascii.Error:
            return None
    return None


def _append_png(images: list[bytes], payload: bytes) -> None:
    """Append ``payload`` to ``images`` and warn on invalid signature."""

    if not payload.startswith(_PNG_SIGNATURE):
        LOGGER.warning("non-png-signature; len=%d", len(payload))
    images.append(payload)


def _extract_png_bytes(response: Any) -> list[bytes]:
    """Extract PNG byte payloads from a Gemini SDK response object."""

    images: list[bytes] = []

    candidates = getattr(response, "candidates", None)
    if candidates is None and isinstance(response, dict):
        candidates = response.get("candidates", [])

    for candidate in candidates or []:
        content = getattr(candidate, "content", None)
        if content is None and isinstance(candidate, dict):
            content = candidate.get("content")
        if content is None:
            continue
        parts = getattr(content, "parts", None)
        if parts is None and isinstance(content, dict):
            parts = content.get("parts", [])
        for part in parts or []:
            inline_data = getattr(part, "inline_data", None)
            if inline_data is None and isinstance(part, dict):
                inline_data = part.get("inline_data")
            if not inline_data:
                continue
            mime_type = getattr(inline_data, "mime_type", "")
            if isinstance(inline_data, dict):
                mime_type = inline_data.get("mime_type", mime_type)
            if mime_type != "image/png":
                continue
            data = getattr(inline_data, "data", None)
            if isinstance(inline_data, dict):
                data = inline_data.get("data", data)
            if data is None:
                continue
            if isinstance(data, (bytes, bytearray)):
                payload = bytes(data)
            elif isinstance(data, str):
                decoded = _decode_base64(data)
                if decoded is None:
                    continue
                payload = decoded
            else:
                continue
            _append_png(images, payload)

    return images


def _generate_with_model(model: genai.GenerativeModel, prompt: str) -> list[bytes]:
    """Generate images using the ``GenerativeModel`` surface."""

    response = _run_with_retry(lambda: model.generate_content(prompt))
    return _extract_png_bytes(response)


def generate_images(prompt: str, n: int = 2, aspect: str = "VERTICAL", fmt: str = "png") -> list[bytes]:
    """Generate PNG images via Gemini using the GenerativeModel defaults."""

    if not prompt or not prompt.strip():
        raise ValueError("prompt must be a non-empty string")

    if not 1 <= n <= 4:
        raise ValueError("n must be between 1 and 4")

    if fmt.lower() not in {"png"}:
        raise ValueError("unsupported image format")

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        pngs: list[bytes] = []
        missing = n

        for _ in range(2):
            for _ in range(missing):
                pngs.extend(_generate_with_model(model, prompt))
                if len(pngs) >= n:
                    break
            if len(pngs) >= n:
                break
            missing = n - len(pngs)

        if not pngs:
            raise RuntimeError("no_images_generated")

        if len(pngs) > n:
            pngs = pngs[:n]

        if len(pngs) < n:
            LOGGER.warning(
                "gemini returned fewer images than requested",
                extra={"requested": n, "received": len(pngs)},
            )

        LOGGER.info(
            "gemini images generated",
            extra={"model": MODEL_NAME, "count": len(pngs), "sha1": short_sha1(prompt)},
        )

        return pngs
    except Exception as exc:  # noqa: BLE001 - propagate after logging
        LOGGER.error("gemini image generation failed: %s: %s", exc.__class__.__name__, str(exc))
        raise
