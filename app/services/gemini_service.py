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


class _ImagesApiUnavailable(RuntimeError):
    """Raised when the experimental Images API surface is not usable."""


def _sha1_prefix(text: str) -> str:
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


def _generate_with_images_api(prompt: str, count: int, fmt: str) -> list[bytes]:
    """Attempt image generation using the experimental ``Images`` surface."""

    images_api = None
    if hasattr(genai, "Images"):
        images_api = getattr(genai, "Images")
    elif hasattr(genai, "images"):
        images_api = getattr(genai, "images")

    if images_api is None:
        raise _ImagesApiUnavailable("images_api_missing")

    generate_fn = getattr(images_api, "generate", None)
    if not callable(generate_fn):
        raise _ImagesApiUnavailable("generate_not_callable")

    def _call() -> Any:
        last_type_error: Exception | None = None
        base_options = [
            {"model": MODEL_NAME, "prompt": prompt, "n": count},
            {"model": MODEL_NAME, "prompt": prompt, "num_images": count},
        ]
        extra_options = [
            {"mime_type": "image/png"},
            {"format": fmt},
            {"image_format": fmt},
            {},
        ]

        for base_kwargs in base_options:
            for extra_kwargs in extra_options:
                try:
                    return generate_fn(**base_kwargs, **extra_kwargs)
                except TypeError as exc:
                    last_type_error = exc
                    continue
        if last_type_error is not None:
            raise _ImagesApiUnavailable(str(last_type_error))
        raise _ImagesApiUnavailable("images_api_signature_mismatch")

    response = _run_with_retry(_call)
    return _extract_png_bytes(response)


def _generate_with_model(prompt: str, count: int) -> list[bytes]:
    """Generate images using the stable ``GenerativeModel`` surface."""

    model = genai.GenerativeModel(MODEL_NAME)
    collected: list[bytes] = []

    for _ in range(count):
        def _call() -> Any:
            return model.generate_content(
                prompt,
                generation_config={
                    "response_mime_type": "image/png",
                },
            )

        response = _run_with_retry(_call)
        collected.extend(_extract_png_bytes(response))

    return collected


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
        parts = getattr(content, "parts", None)
        if parts is None and isinstance(content, dict):
            parts = content.get("parts", [])
        if not parts:
            continue
        for part in parts:
            inline_data = getattr(part, "inline_data", None)
            if inline_data is None and isinstance(part, dict):
                inline_data = part.get("inline_data")
            if not inline_data:
                continue
            mime_type = getattr(inline_data, "mime_type", None)
            if mime_type is None and isinstance(inline_data, dict):
                mime_type = inline_data.get("mime_type")
            if mime_type != "image/png":
                continue
            data = getattr(inline_data, "data", None)
            if data is None and isinstance(inline_data, dict):
                data = inline_data.get("data")
            if not data:
                continue
            if isinstance(data, str):
                try:
                    payload = base64.b64decode(data, validate=True)
                except binascii.Error:
                    continue
            elif isinstance(data, (bytes, bytearray)):
                payload = bytes(data)
            else:
                continue
            if not payload.startswith(_PNG_SIGNATURE):
                LOGGER.warning(
                    "gemini inline data missing PNG signature",
                    extra={"reason": "missing_signature", "model": MODEL_NAME},
                )
            images.append(payload)

    return images


def generate_images(prompt: str, n: int = 2, aspect: str = "VERTICAL", fmt: str = "png") -> list[bytes]:
    """Generate PNG images via Gemini, using either Images API or GenerativeModel.

    The Google Generative AI SDK is evolving, so this helper first attempts to use
    the experimental :mod:`Images` surface when available and falls back to the
    stable :class:`~google.generativeai.GenerativeModel` interface otherwise.
    If the SDK signatures change in the future, update the `_generate_with_images_api`
    helper to match the new method names and keyword arguments and remove the
    compatibility shim when a single path is sufficient.
    """

    if not prompt or not prompt.strip():
        raise ValueError("prompt must be a non-empty string")

    if not 1 <= n <= 4:
        raise ValueError("n must be between 1 and 4")

    if fmt.lower() not in {"png"}:
        raise ValueError("unsupported image format")

    aspect_key = (aspect or "").upper()
    size_map = {
        "VERTICAL": "1024x1536",
        "SQUARE": "1024x1024",
    }
    size_str = size_map.get(aspect_key, "1024x1536")
    if aspect_key == "SQUARE":
        framing_hint = "Square framing, full outfit visible"
    else:
        framing_hint = "Vertical portrait framing, full outfit visible"
    prompt_hint = f"{prompt}\n\n{framing_hint}; target feel ~{size_str}."

    images: list[bytes] = []
    attempts = 0
    max_attempts = 2

    try:
        while len(images) < n and attempts < max_attempts:
            remaining = n - len(images)
            new_images: list[bytes] = []
            if attempts == 0:
                try:
                    new_images = _generate_with_images_api(prompt_hint, remaining, fmt.lower())
                except _ImagesApiUnavailable:
                    new_images = _generate_with_model(prompt_hint, remaining)
            else:
                new_images = _generate_with_model(prompt_hint, remaining)

            attempts += 1

            images.extend(new_images)

        if not images:
            raise RuntimeError("no_images_generated")

        if len(images) > n:
            images = images[:n]

        LOGGER.info(
            "gemini images generated",
            extra={
                "model": MODEL_NAME,
                "size": size_str,
                "n": n,
                "prompt_sha1": _sha1_prefix(prompt),
            },
        )
        return images
    except Exception as exc:  # noqa: BLE001
        LOGGER.error(
            "gemini image generation failed",
            extra={
                "err": exc.__class__.__name__,
                "detail": str(exc),
            },
        )
        raise
