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


def _generate_with_images_api(prompt: str, count: int, size: str, fmt: str) -> list[bytes]:
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
            {"model": MODEL_NAME, "prompt": prompt, "size": size, "n": count},
            {"model": MODEL_NAME, "prompt": prompt, "image_size": size, "n": count},
            {"model": MODEL_NAME, "prompt": prompt, "size": size, "num_images": count},
            {"model": MODEL_NAME, "prompt": prompt, "image_size": size, "num_images": count},
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


def _generate_with_model(prompt: str, count: int, size: str) -> list[bytes]:
    """Generate images using the stable ``GenerativeModel`` surface."""

    model = genai.GenerativeModel(MODEL_NAME)
    collected: list[bytes] = []

    for _ in range(count):
        def _call() -> Any:
            return model.generate_content(
                prompt,
                generation_config={
                    "response_mime_type": "image/png",
                    "image_size": size,
                },
            )

        response = _run_with_retry(_call)
        collected.extend(_extract_png_bytes(response))

    return collected


def _maybe_add_png(images: list[bytes], payload: bytes) -> None:
    if not payload:
        return
    if not payload.startswith(_PNG_SIGNATURE):
        LOGGER.warning("gemini response payload does not look like PNG")
    images.append(payload)


def _extract_png_bytes(response: Any) -> list[bytes]:
    """Extract PNG byte payloads from a Gemini SDK response object."""

    images: list[bytes] = []

    def _process(obj: Any) -> None:
        if obj is None:
            return
        if isinstance(obj, bytes):
            _maybe_add_png(images, obj)
            return
        if isinstance(obj, str):
            try:
                decoded = base64.b64decode(obj, validate=True)
            except binascii.Error:
                return
            _maybe_add_png(images, decoded)
            return
        if isinstance(obj, dict):
            if "inline_data" in obj:
                _process(obj["inline_data"])
            if "data" in obj:
                _process(obj["data"])
            if "image" in obj:
                _process(obj["image"])
            if "images" in obj:
                _process(obj["images"])
            for value in obj.values():
                _process(value)
            return
        if isinstance(obj, (list, tuple, set)):
            for item in obj:
                _process(item)
            return
        for attr in ("inline_data", "data", "image", "images", "content", "parts", "candidates"):
            if hasattr(obj, attr):
                _process(getattr(obj, attr))
        if hasattr(obj, "__dict__"):
            _process(vars(obj))

    _process(response)
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
    size = size_map.get(aspect_key, "1024x1536")

    images: list[bytes] = []

    try:
        for attempt in range(2):
            if len(images) >= n:
                break
            remaining = n - len(images)
            try:
                new_images = _generate_with_images_api(prompt, remaining, size, fmt.lower())
            except _ImagesApiUnavailable:
                new_images = []
            images.extend(new_images[:remaining])

            if len(images) >= n:
                break

            fallback_needed = n - len(images)
            if fallback_needed > 0:
                fallback_images = _generate_with_model(prompt, fallback_needed, size)
                images.extend(fallback_images[:fallback_needed])

        if not images:
            raise RuntimeError("gemini_image_generation_empty")

        images = images[:n]
        LOGGER.info(
            "gemini images generated",
            extra={
                "model": MODEL_NAME,
                "size": size,
                "n": n,
                "prompt_sha": _sha1_prefix(prompt),
            },
        )
        return images
    except Exception as exc:  # noqa: BLE001
        LOGGER.error(
            "gemini image generation failed",
            extra={
                "error": exc.__class__.__name__,
                "message": str(exc),
            },
        )
        raise
